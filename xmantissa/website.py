# -*- test-case-name: xmantissa.test.test_website -*-

"""

This module defines the basic engine for web sites and applications using
Mantissa.  It defines the basic in-database web server, and an authentication
binding using nevow.guard.

To interact with the code defined here, create a web site using the
command-line 'axiomatic' program using the 'web' subcommand.

"""

import socket
import warnings

from zope.interface import implements

try:
    from cssutils import CSSParser
except ImportError:
    CSSParser = None

from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import ICredentialsChecker, AllowAnonymousAccess
from twisted.protocols import policies
from twisted.internet import defer
from twisted.application.service import IService
from twisted.python.filepath import FilePath

from epsilon.structlike import record

from nevow.inevow import IRequest, IResource
from nevow.rend import NotFound, Page, Fragment
from nevow import inevow
from nevow.appserver import NevowSite, NevowRequest
from nevow.static import File
from nevow.url import URL
from nevow import url
from nevow import athena

from axiom import upgrade
from axiom.item import Item, _PowerupConnector, declareLegacyItem
from axiom.attributes import AND, integer, inmemory, text, reference, bytes, boolean
from axiom.userbase import LoginSystem
from axiom.dependency import installOn

from xmantissa.ixmantissa import (
    ISiteRootPlugin, ISessionlessSiteRootPlugin, IProtocolFactoryFactory,
    IWebTranslator, IPreferenceAggregator, IOfferingTechnician)
from xmantissa import websession
from xmantissa.port import TCPPort, SSLPort

from xmantissa.cachejs import theHashModuleProvider


class WebConfigurationError(RuntimeError):
    """
    You specified some invalid configuration.
    """

class MantissaLivePage(athena.LivePage):
    """
    An L{athena.LivePage} which supports the global JavaScript modules
    collection that Mantissa provides as a root resource.

    All L{athena.LivePage} usages within and derived from Mantissa should
    subclass this.

    @ivar webSite: a L{WebSite} instance which provides site configuration
        information for generating links.

    @ivar hashCache: a cache which maps JS module names to
        L{xmantissa.cachejs.CachedJSModule} objects.
    @type hashCache: L{xmantissa.cachejs.HashedJSModuleProvider}

    @type _moduleRoot: L{URL}
    @ivar _moduleRoot: The base location for script tags which load Athena
        modules required by this page and widgets on this page.  This is set
        based on the I{Host} header in the request, so it is C{None} until
        the instance is actually rendered.
    """

    hashCache = theHashModuleProvider

    _moduleRoot = None

    def __init__(self, webSite, *a, **k):
        """
        Create a L{MantissaLivePage}.

        @param webSite: a L{WebSite} with a usable secure port implementation.
        """
        self.webSite = webSite
        athena.LivePage.__init__(self, transportRoot=url.root.child('live'),
                                 *a, **k)


    def beforeRender(self, ctx):
        """
        Before rendering, retrieve the hostname from the request being
        responded to and generate an URL which will serve as the root for
        all JavaScript modules to be loaded.
        """
        request = IRequest(ctx)
        root = self.webSite.rootURL(request)
        self._moduleRoot = root.child('__jsmodule__')


    def getJSModuleURL(self, moduleName):
        """
        Retrieve an L{URL} object which references the given module name.

        This makes a 'best effort' guess as to an fully qualified HTTPS URL
        based on the hostname provided during rendering and the configuration
        of the site.  This is to avoid unnecessary duplicate retrieval of the
        same scripts from two different URLs by the browser.

        If such configuration does not exist, however, it will simply return an
        absolute path URL with no hostname or port.

        @raise NotImplementedError: if rendering has not begun yet and
        therefore beforeRender has not provided us with a usable hostname.
        """
        if self._moduleRoot is None:
            raise NotImplementedError(
                "JS module URLs cannot be requested before rendering.")
        moduleHash = self.hashCache.getModule(moduleName).hashValue
        return self._moduleRoot.child(moduleHash).child(moduleName)



class StaticContent(record('staticPaths processors')):
    """
    Parent resource for all static content provided by all installed offerings.

    This resource has a child by the name of each offering which declares a
    static content path which serves that path.

    @ivar staticPaths: A C{dict} mapping offering names to L{FilePath}
        instances for each offering which should be able to publish static
        content.

    @ivar processors: A C{dict} mapping extensions (with leading ".") to
        two-argument callables.  These processors will be attached to the
        L{nevow.static.File} returned by C{locateChild}.
    """
    implements(inevow.IResource)

    def locateChild(self, context, segments):
        """
        Find the offering with the name matching the first segment and return a
        L{File} for its I{staticContentPath}.
        """
        name = segments[0]
        try:
            staticContent = self.staticPaths[name]
        except KeyError:
            return NotFound
        else:
            resource = File(staticContent.path)
            resource.processors = self.processors
            return resource, segments[1:]
        return NotFound



class SiteRootMixin(object):
    """
    Mixin class providing useful methods for the very top of the Mantissa site
    hierarchy, both private and public.

    Any page which provides a resource for "/" on a Mantissa server should
    inherit from this, since many other Mantissa features depend upon resources
    provided as children of this one.

    Subclasses are expected to provide various instance attributes.

    @ivar hitCount: The number of times this SiteRootMixin provider has had one
    of its pages retrieved.

    @ivar hashCache: a refererence to a L{HashedJSModuleProvider} which will
    provide javascript cacheability for this site.

    @ivar powerupInterface: The interface to search for powerups by.

    @ivar store: the store to query for powerups in.
    """
    implements(inevow.IResource)

    powerupInterface = ISiteRootPlugin

    hitCount = 0

    hashCache = theHashModuleProvider

    def renderHTTP(self, ctx):
        """
        This page is not renderable, because it is the very root of the server.

        @raise NotImplementedError: Always.
        """
        raise NotImplementedError(
            "This _must_ be installed at the root of a server.")


    def child___jsmodule__(self, ignored):
        """
        __jsmodule__ child which provides support for Athena applications to
        use a centralized URL to deploy JavaScript code.
        """
        return self.hashCache


    def child_live(self, ctx):
        """
        The 'live' namespace is reserved for Athena LivePages.  By default in
        Athena applications these resources are child resources of whatever URL
        the live page ends up at, but this root URL is provided so that the
        reliable message queuing logic can sidestep all resource traversal, and
        therefore, all database queries.  This is an important optimization,
        since Athena's implementation assumes that HTTP hits to the message
        queue resource are cheap.

        @return: an L{athena.LivePage} instance.
        """
        return athena.LivePage(None, None)
    child_live.countHits = False


    def child_Mantissa(self, ctx):
        """
        Serve files from C{xmantissa/static/} at the URL C{/Mantissa}.
        """
        # Cheating!  It *looks* like there's an app store, but there isn't
        # really, because this is the One Store To Bind Them All.

        # We shouldn't really cheat here.  It would be better to have one real
        # Mantissa offering that has its static content served up the same way
        # every other offering's content is served.  There's already a
        # /static/mantissa-static/.  This child definition is only still here
        # because some things still reference this URL.  For example,
        # JavaScript files and any CSS file which uses Mantissa content but is
        # from an Offering which does not provide a staticContentPath.
        # See #2469.  -exarkun
        return File(FilePath(__file__).sibling("static").path)


    def locateChild(self, ctx, segments):
        """
        Locate a page on a Mantissa site.

        First, look up child_ methods as normal.

        Then, look for all powerups for the interface described by the
        L{powerupInterface} attribute and call their L{resourceFactory}
        methods.

        If neither of these techniques yields a result, return L{NotFound}.

        This will increment hitCount, except for child_ methods explicitly
        annotated with a 'countHits = False' attribute.
        """
        shortcut = getattr(self, 'child_'+segments[0], None)
        if shortcut:
            # what is it, like the 80th implementation of this?
            res = shortcut(ctx)
            if getattr(shortcut, 'countHits', True):
                self.hitCount += 1
            if res is not None:
                return res, segments[1:]
        s = self.store
        P = self.powerupInterface
        for plg in s.powerupsFor(P):
            childAndSegments = plg.resourceFactory(segments)
            if childAndSegments is not None:
                child, segments = childAndSegments # sanity
                                                   # check/documentation; feel
                                                   # free to remove
                return child, segments
        return NotFound



class UnguardedWrapper(SiteRootMixin):
    """
    Resource which wraps the top of the Mantissa resource hierarchy and adds a
    login resource and performs redirects to HTTPS URLs as necessary.

    @ivar store: The site L{Store} for the resource hierarchy being wrapped.
    @ivar guardedRoot: The root resource of the hierarchy being wrapped.
    """
    implements(inevow.IResource)

    powerupInterface = ISessionlessSiteRootPlugin
    hitCount = 0

    def __init__(self, store, guardedRoot):
        self.store = store
        self.guardedRoot = guardedRoot


    def child_static(self, context):
        """
        Serve a container page for static content for Mantissa and other
        offerings.
        """
        offeringTech = IOfferingTechnician(self.store)
        installedOfferings = offeringTech.getInstalledOfferings()
        offeringsWithContent = dict([
                (offering.name, offering.staticContentPath)
                for offering
                in installedOfferings.itervalues()
                if offering.staticContentPath])

        # If you wanted to do CSS rewriting for all CSS files served beneath
        # /static/, you could do it by passing a processor for ".css" here.
        # eg:
        #
        # website = inevow.IResource(self.store)
        # factory = StylesheetFactory(
        #     offeringsWithContent.keys(), website.rootURL)
        # StaticContent(offeringsWithContent, {
        #               ".css": factory.makeStylesheetResource})
        return StaticContent(offeringsWithContent, {})


    def locateChild(self, ctx, segments):
        request = inevow.IRequest(ctx)
        if segments[0] == 'login':
            webSite = inevow.IResource(self.store, None)
            if webSite is not None:
                securePort = webSite.securePort
            else:
                securePort = None
            if not request.isSecure() and securePort is not None:
                url = URL.fromContext(ctx)
                newurl = url.secure(port=securePort.getHost().port)
                for seg in segments:
                    newurl = newurl.child(seg)
                return newurl, ()
            else:
                # This should be eliminated by having a regular child_login in
                # publicweb instead, I think, but for now we can eliminate a
                # confusing circular import --glyph
                from xmantissa.publicweb import LoginPage
                return LoginPage(self.store), segments[1:]
        x = SiteRootMixin.locateChild(self, ctx, segments)
        if x is not NotFound:
            return x
        def maybeSecure((child, segments)):
            if getattr(child, 'needsSecure', None):
                request = inevow.IRequest(ctx)
                if not request.isSecure():
                    website = inevow.IResource(self.store)
                    root = website.encryptedRoot(request.getHeader('host'))
                    root = root.click('/'.join(segments))
                    return root, ()
            return child, segments
        return defer.maybeDeferred(self.guardedRoot.locateChild, ctx, segments
                                   ).addCallback(maybeSecure)


JUST_SLASH = ('',)

class PrefixURLMixin(object):
    """
    Mixin for use by I[Sessionless]SiteRootPlugin implementors; provides a
    resourceFactory method which looks for an C{prefixURL} string on self,
    and calls and returns self.createResource().

    C{prefixURL} is a '/'-separated unicode string; it must be set before
    calling installOn.  To respond to the url C{http://example.com/foo/bar},
    use the prefixURL attribute u'foo/bar'.

    @ivar sessioned: Boolean indicating whether this object should
    powerup for L{ISiteRootPlugin}.  Note: this is only tested when
    L{installOn} is called.  If you change it later, it will have no
    impact.

    @ivar sessionless: Boolean indicating whether this object should
    powerup for ISessionlessSiteRootPlugin.  This is tested at the
    same time as L{sessioned}.
    """

    sessioned = False
    sessionless = False

    def __str__(self):
        return '/%s => item(%s)' % (self.prefixURL, self.__class__.__name__)

    def createResource(self):
        """
        Create and return an IResource.  This will only be invoked if
        the request matches the prefixURL specified on this object.
        May also return None to indicate that this object does not
        actually want to handle this request.
        """
        raise NotImplementedError(
            "PrefixURLMixin.createResource() should be "
            "implemented by subclasses (%r didn't)" % (
                self.__class__.__name__,))

    def resourceFactory(self, segments):
        """Return a C{(resource, subsegments)} tuple or None, depending on whether I
        wish to return an IResource provider for the given set of segments or
        not.
        """
        if not self.prefixURL:
            needle = ()
        else:
            needle = tuple(self.prefixURL.split('/'))
        S = len(needle)
        if segments[:S] == needle:
            if segments == JUST_SLASH:
                # I *HATE* THE WEB
                subsegments = segments
            else:
                subsegments = segments[S:]
            res = self.createResource()
            # Even though the URL matched up, sometimes we might still
            # decide to not handle this request (eg, some prerequisite
            # for our function is not met by the store).  Allow None
            # to be returned by createResource to indicate this case.
            if res is not None:
                return res, subsegments

    def __getPowerupInterfaces__(self, powerups):
        """
        Install me on something (probably a Store) that will be queried for
        ISiteRootPlugin providers.
        """

        #First, all the other powerups
        for x in powerups:
            yield x

        # Only 256 segments are allowed in URL paths.  We want to make sure
        # that static powerups always lose priority ordering to dynamic
        # powerups, since dynamic powerups will have information
        pURL = self.prefixURL
        priority = (pURL.count('/') - 256)
        if pURL == '':
            # Did I mention I hate the web?  Plugins at / are special in 2
            # ways.  Their segment length is kinda-sorta like 0 most of the
            # time, except when it isn't.  We subtract from the priority here
            # to make sure that [''] is lower-priority than ['foo'] even though
            # they are technically the same number of segments; the reason for
            # this is that / is special in that it pretends to be the parent of
            # everything and will score a hit for *any* URL in the hierarchy.
            # Above, we special-case JUST_SLASH to make sure that the other
            # half of this special-casing holds true.
            priority -= 1

        if not self.sessioned and not self.sessionless:
            warnings.warn(
                "Set either sessioned or sessionless on %r!  Falling back to "
                "deprecated providedBy() behavior" % (self.__class__.__name__,),
                DeprecationWarning,
                stacklevel=2)
            for iface in ISessionlessSiteRootPlugin, ISiteRootPlugin:
                if iface.providedBy(self):
                    yield (iface, priority)
        else:
            if self.sessioned:
                yield (ISiteRootPlugin, priority)
            if self.sessionless:
                yield (ISessionlessSiteRootPlugin, priority)


class StaticSite(PrefixURLMixin, Item):
    implements(ISessionlessSiteRootPlugin,     # implements both so that it
               ISiteRootPlugin)                # works in both super and sub
                                               # stores.
    typeName = 'static_web_site'
    schemaVersion = 2

    prefixURL = text()
    staticContentPath = text()

    sessioned = boolean(default=False)
    sessionless = boolean(default=True)

    def __str__(self):
        return '/%s => file(%s)' % (self.prefixURL, self.staticContentPath)

    def createResource(self):
        return File(self.staticContentPath)

    def installSite(self):
        """
        Not using the dependency system for this class because it's only
        installed via the command line, and multiple instances can be
        installed.
        """
        for iface, priority in self.__getPowerupInterfaces__([]):
            self.store.powerUp(self, iface, priority)

def upgradeStaticSite1To2(oldSite):
    newSite = oldSite.upgradeVersion(
        'static_web_site', 1, 2,
        staticContentPath=oldSite.staticContentPath,
        prefixURL=oldSite.prefixURL,
        sessionless=True)
    for pc in newSite.store.query(_PowerupConnector,
                                  AND(_PowerupConnector.powerup == newSite,
                                      _PowerupConnector.interface == u'xmantissa.ixmantissa.ISiteRootPlugin')):
        pc.item.powerDown(newSite, ISiteRootPlugin)
    return newSite
upgrade.registerUpgrader(upgradeStaticSite1To2, 'static_web_site', 1, 2)


class StaticRedirect(Item, PrefixURLMixin):
    implements(inevow.IResource,
               ISessionlessSiteRootPlugin,
               ISiteRootPlugin)

    schemaVersion = 2
    typeName = 'web_static_redirect'

    targetURL = text(allowNone=False)

    prefixURL = text(allowNone=False)

    sessioned = boolean(default=True)
    sessionless = boolean(default=True)

    def __str__(self):
        return '/%s => url(%s)' % (self.prefixURL, self.targetURL)

    def locateChild(self, ctx, segments):
        return self, ()

    def renderHTTP(self, ctx):
        return URL.fromContext(ctx).click(self.targetURL)

    def createResource(self):
        return self

def upgradeStaticRedirect1To2(oldRedirect):
    newRedirect = oldRedirect.upgradeVersion(
        'web_static_redirect', 1, 2,
        targetURL=oldRedirect.targetURL,
        prefixURL=oldRedirect.prefixURL)
    if newRedirect.prefixURL == u'':
        newRedirect.sessionless = False
        for pc in newRedirect.store.query(_PowerupConnector,
                                          AND(_PowerupConnector.powerup == newRedirect,
                                              _PowerupConnector.interface == u'xmantissa.ixmantissa.ISessionlessSiteRootPlugin')):
            pc.item.powerDown(newRedirect, ISessionlessSiteRootPlugin)
    return newRedirect
upgrade.registerUpgrader(upgradeStaticRedirect1To2, 'web_static_redirect', 1, 2)

class AxiomRequest(NevowRequest):
    def __init__(self, store, *a, **kw):
        NevowRequest.__init__(self, *a, **kw)
        self.store = store

    def process(self, *a, **kw):
        return self.store.transact(NevowRequest.process, self, *a, **kw)


class AxiomSite(NevowSite):
    def __init__(self, store, *a, **kw):
        NevowSite.__init__(self, *a, **kw)
        self.store = store
        self.requestFactory = lambda *a, **kw: AxiomRequest(self.store, *a, **kw)


class AxiomPage(Page):
    def renderHTTP(self, ctx):
        return self.store.transact(Page.renderHTTP, self, ctx)



class AxiomFragment(Fragment):
    def rend(self, ctx, data):
        return self.store.transact(Fragment.rend, self, ctx, data)



class StylesheetFactory(record('installedOfferingNames rootURL')):
    """
    Factory which creates resources for stylesheets which will rewrite URLs in
    them to be rooted at a particular location.

    @ivar installedOfferingNames: A C{list} of C{unicode} giving the names of
        the offerings which are installed and have a static content path.
        These are the offerings for which C{StaticContent} will find children,
        so these are the only offerings URLs pointed at which should be
        rewritten.

    @ivar rootURL: A one-argument callable which takes a request and returns an
        L{URL} which is to be used as the root of all URLs served by resources
        this factory creates.
    """
    def makeStylesheetResource(self, path, registry):
        """
        Return a resource for the css at the given path with its urls rewritten
        based on self.rootURL.
        """
        return StylesheetRewritingResourceWrapper(
            File(path), self.installedOfferingNames, self.rootURL)



class StylesheetRewritingResourceWrapper(
    record('resource installedOfferingNames rootURL')):
    """
    Resource which renders another resource using a request which rewrites CSS
    URLs.

    @ivar resource: Another L{IResource} which will be used to generate the
        response.

    @ivar installedOfferingNames: See L{StylesheetFactory.installedOfferingNames}

    @ivar rootURL: See L{StylesheetFactory.rootURL}
    """
    implements(IResource)

    def renderHTTP(self, context):
        """
        Render C{self.resource} through a L{StylesheetRewritingRequestWrapper}.
        """
        request = IRequest(context)
        request = StylesheetRewritingRequestWrapper(
            request, self.installedOfferingNames, self.rootURL)
        context.remember(request, IRequest)
        return self.resource.renderHTTP(context)



class StylesheetRewritingRequestWrapper(object):
    """
    Request which intercepts the response body, parses it as CSS, rewrites its
    URLs, and sends the serialized result.

    @ivar request: Another L{IRequest} object, methods of which will be used to
        implement this request.

    @ivar _buffer: A list of C{str} which have been passed to the write method.

    @ivar installedOfferingNames: See L{StylesheetFactory.installedOfferingNames}

    @ivar rootURL: See L{StylesheetFactory.rootURL}.
    """
    def __init__(self, request, installedOfferingNames, rootURL):
        self.request = request
        self._buffer = []
        self.installedOfferingNames = installedOfferingNames
        self.rootURL = rootURL


    def __getattr__(self, name):
        """
        Pass attribute lookups on to the wrapped request object.
        """
        return getattr(self.request, name)


    def write(self, bytes):
        """
        Buffer the given bytes for later processing.
        """
        self._buffer.append(bytes)


    def _replace(self, url):
        """
        Change URLs with absolute paths so they are rooted at the correct
        location.
        """
        segments = url.split('/')
        if segments[0] == '':
            root = self.rootURL(self.request)
            if segments[1] == 'Mantissa':
                root = root.child('static').child('mantissa-base')
                segments = segments[2:]
            elif segments[1] in self.installedOfferingNames:
                root = root.child('static').child(segments[1])
                segments = segments[2:]
            for seg in segments:
                root = root.child(seg)
            return str(root)
        return url


    def finish(self):
        """
        Parse the buffered response body, rewrite its URLs, write the result to
        the wrapped request, and finish the wrapped request.
        """
        stylesheet = ''.join(self._buffer)
        parser = CSSParser()
        css = parser.parseString(stylesheet)
        css.replaceUrls(self._replace)
        self.request.write(css.cssText)
        return self.request.finish()



class WebSite(Item, SiteRootMixin):
    """
    Govern an HTTP server which binds a port on startup and tears it down at
    shutdown using the Twisted Service system.  Unfortunately, also provide web
    pages.  These two tasks should be the responsibility of two separate Items,
    but writing the upgrader to fix this won't be fun so I don't want to do it.
    Someone else should though.
    """
    implements(IProtocolFactoryFactory, IResource)

    powerupInterfaces = (IProtocolFactoryFactory, IResource)

    typeName = 'mantissa_web_powerup'
    schemaVersion = 5

    hitCount = integer(default=0)
    installedOn = reference()

    hostname = text(doc="""
    The primary hostname by which this website will be accessible.  If set to
    C{None}, a guess will be made using L{socket.getfqdn}.
    """, default=None)

    httpLog = bytes(default=None)

    site = inmemory()

    debug = False

    def securePort():
        """
        Define a backwards compatibility property for the IListeningPort for
        the HTTPS server which used to be an attribute on WebSite.
        """
        def get(self):
            warnings.warn(
                "WebSite.securePort is deprecated!",
                stacklevel=3, category=DeprecationWarning)
            port = self._getPort(SSLPort)
            if port is not None:
                return port.listeningPort
            return None
        return get,
    securePort = property(*securePort())


    def activate(self):
        self.site = None


    def _root(self, scheme, hostname, portObj, standardPort):
        # TODO - real unicode support (but punycode is so bad)
        if portObj is None:
            return None

        portNumber = portObj.portNumber
        port = portObj.listeningPort

        if hostname is None:
            if self.hostname is None:
                hostname = socket.getfqdn()
            else:
                hostname = self.hostname.encode('ascii')
        else:
            hostname = hostname.split(':')[0].encode('ascii')

        if portNumber == 0:
            if port is None:
                return None
            else:
                portNumber = port.getHost().port

        # At some future point, we may want to make pathsegs persistently
        # configurable - perhaps scheme and hostname as well - in order to
        # easily support reverse proxying configurations, particularly where
        # Mantissa is being "mounted" somewhere other than /.  See also rootURL
        # which has some overlap with this method (the difference being
        # universal vs absolute URLs - rootURL may want to call cleartextRoot
        # or encryptedRoot in the future).  See #417 and #2309.
        pathsegs = ['']
        if portNumber != standardPort:
            hostname = '%s:%d' % (hostname, portNumber)
        return URL(scheme, hostname, pathsegs)


    def _getPort(self, portType):
        return self.store.findFirst(
            portType, portType.factory == self, default=None)


    def cleartextRoot(self, hostname=None):
        """
        Return a string representing the HTTP URL which is at the root of this
        site.

        @param hostname: An optional unicode string which, if specified, will
        be used as the hostname in the resulting URL, regardless of the
        C{hostname} attribute of this item.
        """
        return self._root('http', hostname, self._getPort(TCPPort), 80)


    def encryptedRoot(self, hostname=None):
        """
        Return a string representing the HTTPS URL which is at the root of this
        site.

        @param hostname: An optional unicode string which, if specified, will
        be used as the hostname in the resulting URL, regardless of the
        C{hostname} attribute of this item.
        """
        return self._root('https', hostname, self._getPort(SSLPort), 443)


    def maybeEncryptedRoot(self, hostname=None):
        """
        Returning a string representing the HTTPS URL which is at the root of
        this site, falling back to HTTP if HTTPS service is not available.

        @param hostname: An optional unicode string which, if specified, will
        be used as the hostname in the resulting URL, regardless of the
        C{hostname} attribute of this item.
        """
        warnings.warn(
            "Use WebSite.rootURL instead of "
            "WebSite.maybeEncryptedRoot",
            category=DeprecationWarning,
            stacklevel=3)
        root = self.encryptedRoot(hostname)
        if root is None:
            root = self.cleartextRoot(hostname)
        return root


    def rootURL(self, request):
        """
        Simple utility function to provide a root URL for this website which is
        appropriate to use in links generated in response to the given request.

        @type request: L{twisted.web.http.Request}
        @param request: The request which is being responded to.

        @rtype: L{URL}
        @return: The location at which the root of the resource hierarchy for
            this website is available.
        """
        if self.hostname:
            siteHostname = self.hostname
        else:
            siteHostname = socket.getfqdn()
        host = request.getHeader('host') or siteHostname
        if ':' in host:
            host = host.split(':', 1)[0]
        if (host == siteHostname or
            host.startswith('www.') and host[len('www.'):] == siteHostname):
            return URL(scheme='', netloc='', pathsegs=[''])
        else:
            if request.isSecure():
                return self.encryptedRoot(self.hostname)
            else:
                return self.cleartextRoot(self.hostname)


    def child_users(self, ctx):
        """
        Return a child resource to provide access to items shared by users.

        @return: a resource whose children will be private pages of individual
        users.

        @rtype L{xmantissa.websharing.UserIndexPage}
        """
        # inner import due to websharing->publicweb->website circularity
        from xmantissa.websharing import UserIndexPage
        ls = self.store.findUnique(LoginSystem, default=None)
        if ls is None:
            return None
        return UserIndexPage(ls)


    def child_resetPassword(self, ctx):
        """
        Return a page which will allow the user to re-set their password.

        If the user is logged in, locate their IPreferenceAggregator and return
        that so that they can set their password on the settings page.
        Otherwise, return a L{PasswordResetResource} so that anonymous users
        may request their password be emailed to them.

        Note: the mechanism used to determine whether a user is 'logged in'
        here is simply looking for an IPreferenceAggregator; in other words, it
        assumes that one will never be installed on a site store.  If you do
        that, users will not be able to reset their passwords.  Eventually,
        there ought to be separate objects for handling user-store and
        site-store IResource behavior, and this could be on one but not the
        other.  For now, though, the additional check for being logged in would
        be redundant, since there is no really clean way to check for the
        user's logged-in-ness either.
        """
        pa = IPreferenceAggregator(self.store, None)
        wt = IWebTranslator(self.store, None)
        if pa is not None and wt is not None:
            path = wt.linkTo(pa.storeID)
            return url.here.click(path)
        else:
            from xmantissa.signup import PasswordResetResource
            return PasswordResetResource(self.store)


    # IProtocolFactoryFactory
    def getFactory(self):
        """
        Create an L{AxiomSite} which supports authenticated and anonymous
        access.
        """
        if self.site is None:
            realm = IRealm(self.store, None)
            if realm is None:
                raise WebConfigurationError(
                    'No realm: '
                    'you need to install a userbase before using this service.')
            chkr = ICredentialsChecker(self.store, None)
            if chkr is None:
                raise WebConfigurationError(
                    'No checkers: '
                    'you need to install a userbase before using this service.')
            guardedRoot = websession.PersistentSessionWrapper(
                self.store,
                Portal(realm, [chkr, AllowAnonymousAccess()]))
            self.site = AxiomSite(
                self.store,
                UnguardedWrapper(self.store, guardedRoot),
                logPath=self.httpLog)
            if self.debug:
                self.site = policies.TrafficLoggingFactory(self.site, 'http')
        return self.site


    def setServiceParent(self, parent):
        """
        Compatibility hack necessary to prevent the Axiom service startup
        mechanism from barfing.  Even though this Item is no longer an IService
        powerup, it will still be found as one one more time and this method
        will be called on it.
        """



class APIKey(Item):
    """
    Persistent record of a key used for accessing an external API.

    @cvar URCHIN: Constant name for the "Google Analytics" API
    (http://code.google.com/apis/maps/)
    @type URCHIN: C{unicode}
    """
    URCHIN = u'Google Analytics'

    apiName = text(
        doc="""
        L{APIKey} constant naming the API this key is for.
        """, allowNone=False)


    apiKey = text(
        doc="""
        The key.
        """, allowNone=False)


    def getKeyForAPI(cls, siteStore, apiName):
        """
        Get the API key for the named API, if one exists.

        @param siteStore: The site store.
        @type siteStore: L{axiom.store.Store}

        @param apiName: The name of the API.
        @type apiName: C{unicode} (L{APIKey} constant)

        @rtype: L{APIKey} or C{NoneType}
        """
        return siteStore.findUnique(
            cls, cls.apiName == apiName, default=None)
    getKeyForAPI = classmethod(getKeyForAPI)


    def setKeyForAPI(cls, siteStore, apiName, apiKey):
        """
        Set the API key for the named API, overwriting any existing key.

        @param siteStore: The site store to install the key in.
        @type siteStore: L{axiom.store.Store}

        @param apiName: The name of the API.
        @type apiName: C{unicode} (L{APIKey} constant)

        @param apiKey: The key for accessing the API.
        @type apiKey: C{unicode}

        @rtype: L{APIKey}
        """
        existingKey = cls.getKeyForAPI(siteStore, apiName)
        if existingKey is None:
            return cls(store=siteStore, apiName=apiName, apiKey=apiKey)
        existingKey.apiKey = apiKey
        return existingKey
    setKeyForAPI = classmethod(setKeyForAPI)



def upgradeWebSite1To2(oldSite):
    newSite = oldSite.upgradeVersion(
        'mantissa_web_powerup', 1, 2,
        hitCount=oldSite.hitCount,
        installedOn=oldSite.installedOn,
        portNumber=oldSite.portNumber,
        securePortNumber=oldSite.securePortNumber,
        certificateFile=oldSite.certificateFile,
        httpLog=None)
    return newSite
upgrade.registerUpgrader(upgradeWebSite1To2, 'mantissa_web_powerup', 1, 2)


def upgradeWebSite2to3(oldSite):
    # This is dumb and we should have a way to run procedural upgraders.
    newSite = oldSite.upgradeVersion(
        'mantissa_web_powerup', 2, 3,
        hitCount=oldSite.hitCount,
        installedOn=oldSite.installedOn,
        portNumber=oldSite.portNumber,
        securePortNumber=oldSite.securePortNumber,
        certificateFile=oldSite.certificateFile,
        httpLog=oldSite.httpLog)
    staticMistake = newSite.store.findUnique(StaticSite,
                                             StaticSite.prefixURL == u'static/mantissa',
                                             default=None)
    if staticMistake is not None:
        # Ugh, need cascading deletes
        staticMistake.store.powerDown(staticMistake, ISessionlessSiteRootPlugin)
        staticMistake.deleteFromStore()
    return newSite
upgrade.registerUpgrader(upgradeWebSite2to3, 'mantissa_web_powerup', 2, 3)


def upgradeWebsite3to4(oldSite):
    """
    Add a C{None} hostname attribute.
    """
    newSite = oldSite.upgradeVersion(
        'mantissa_web_powerup', 3, 4,
        installedOn=oldSite.installedOn,
        portNumber=oldSite.portNumber,
        securePortNumber=oldSite.securePortNumber,
        certificateFile=oldSite.certificateFile,
        httpLog=oldSite.httpLog,
        hitCount=oldSite.hitCount,
        hostname=None)
    return newSite
upgrade.registerUpgrader(upgradeWebsite3to4, 'mantissa_web_powerup', 3, 4)

declareLegacyItem(
    WebSite.typeName, 4, dict(hitCount=integer(default=0),
                              installedOn=reference(),
                              hostname=text(default=None),
                              portNumber=integer(default=0),
                              securePortNumber=integer(default=0),
                              certificateFile=bytes(default=0),
                              httpLog=bytes(default=None)))

def upgradeWebsite4to5(oldSite):
    """
    Create TCPPort and SSLPort items as appropriate.
    """
    newSite = oldSite.upgradeVersion(
        'mantissa_web_powerup', 4, 5,
        installedOn=oldSite.installedOn,
        httpLog=oldSite.httpLog,
        hitCount=oldSite.hitCount,
        hostname=oldSite.hostname)

    if oldSite.portNumber is not None:
        port = TCPPort(store=newSite.store, portNumber=oldSite.portNumber, factory=newSite)
        installOn(port, newSite.store)

    securePortNumber = oldSite.securePortNumber
    certificateFile = oldSite.certificateFile
    if securePortNumber is not None and certificateFile:
        oldCertPath = newSite.store.dbdir.preauthChild(certificateFile)
        if oldCertPath.exists():
            newCertPath = newSite.store.newFilePath('server.pem')
            oldCertPath.copyTo(newCertPath)
            port = SSLPort(store=newSite.store, portNumber=oldSite.securePortNumber, factory=newSite, certificatePath=newCertPath)
            installOn(port, newSite.store)
    try:
        newSite.store.powerDown(newSite, IService)
    except ValueError:
        #maybe it wasn't powered up?
        pass

    return newSite
upgrade.registerUpgrader(upgradeWebsite4to5, 'mantissa_web_powerup', 4, 5)
