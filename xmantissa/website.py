
"""

This module defines the basic engine for web sites and applications using
Mantissa.  It defines the basic in-database web server, and an authentication
binding using nevow.guard.

To interact with the code defined here, create a web site using the
command-line 'axiomatic' program using the 'web' subcommand.

"""

import warnings

try:
    from OpenSSL import SSL
except ImportError:
    SSL = None

from zope.interface import implements

from twisted.python.util import sibpath
from twisted.application.service import IService, Service
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import ICredentialsChecker, AllowAnonymousAccess
from twisted.protocols import policies
from twisted.internet import reactor, defer

from nevow.rend import NotFound, Page, Fragment
from nevow.inevow import IResource
from nevow.appserver import NevowSite, NevowRequest
from nevow.static import File
from nevow.url import URL

from vertex import sslverify

from axiom import upgrade
from axiom.item import Item, InstallableMixin, _PowerupConnector
from axiom.attributes import AND, integer, inmemory, text, reference, bytes, boolean

from xmantissa.ixmantissa import ISiteRootPlugin, ISessionlessSiteRootPlugin, IStaticShellContent
from xmantissa import websession
from xmantissa.publicresource import PublicPage, getLoader

from axiom.slotmachine import hyper as super

class WebConfigurationError(RuntimeError):
    """You specified some invalid configuration.
    """

def domainAndPortFromContext(ctx):
    netloc = URL.fromContext(ctx).netloc.split(':', 1)
    if len(netloc) == 1:
        domain, port = netloc[0], 80
    else:
        domain, port = netloc[0], int(netloc[1])
    return domain, port

class SiteRootMixin(object):
    implements(IResource)

    powerupInterface = ISiteRootPlugin

    def renderHTTP(self, ctx):
        raise NotImplementedError(
            "This _must_ be installed at the root of a server.")

    def locateChild(self, ctx, segments):
        self.hitCount += 1
        s = self.installedOn
        P = self.powerupInterface
        for plg in s.powerupsFor(P):
            childAndSegments = plg.resourceFactory(segments)
            if childAndSegments is not None:
                child, segments = childAndSegments # sanity
                                                   # check/documentation; feel
                                                   # free to remove
                return child, segments
        return NotFound

class LoginPage(PublicPage):
    def __init__(self, original):
        PublicPage.__init__(self, original, getLoader("login"),
                            IStaticShellContent(original.installedOn, None),
                            None)

    def beforeRender(self, ctx):
        secure = ''
        domain, port = domainAndPortFromContext(ctx)

        if port == 80:
            port = ''
        else:
            port = ':%d' % (port,)

        # There should be a nicer way to discover this information
        ws = self.original.installedOn.findFirst(
            WebSite,
            installedOn=self.original.installedOn)

        if ws.securePort is not None:
            secure = 's'
            port = ws.securePort.getHost().port
            if port == 443:
                port = ''
            else:
                port = ':%d' % (port,)

        baseURL = "http%(secure)s://%(domain)s%(port)s%(root)s" % {
            'secure': secure,
            'domain': domain,
            'port': port,
            'root': ''}
        ctx.fillSlots("login-action", baseURL + "/__login__")


class UnguardedWrapper(SiteRootMixin):
    implements(IResource)

    powerupInterface = ISessionlessSiteRootPlugin
    hitCount = 0

    def __init__(self, store, guardedRoot):
        self.installedOn = store
        self.guardedRoot = guardedRoot

    def locateChild(self, ctx, segments):
        if segments[0] == 'login':
            return LoginPage(self), ()
        x = SiteRootMixin.locateChild(self, ctx, segments)
        if x is not NotFound:
            return x
        return self.guardedRoot.locateChild(ctx, segments)


JUST_SLASH = ('',)

class PrefixURLMixin(InstallableMixin):
    """
    Mixin for use by I[Sessionlesss]SiteRootPlugin implementors; provides a
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

    def installOn(self, other, priorityModifier=0):
        """Install me on something (probably a Store) that will be queried for
        ISiteRootPlugin providers.
        """
        super(PrefixURLMixin, self).installOn(other)
        # Only 256 segments are allowed in URL paths.  We want to make sure
        # that static powerups always lose priority ordering to dynamic
        # powerups, since dynamic powerups will have information
        pURL = self.prefixURL
        priority = (pURL.count('/') - 256) + priorityModifier
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
                    other.powerUp(self, iface, priority)
        else:
            if self.sessioned:
                other.powerUp(self, ISiteRootPlugin, priority)
            if self.sessionless:
                other.powerUp(self, ISessionlessSiteRootPlugin, priority)


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


def upgradeStaticSite1To2(oldSite):
    newSite = oldRedirect.upgradeVersion(
        'web_static_redirect', 1, 2,
        staticContentPath=oldSite.staticContentPath,
        prefixURL=oldSite.prefixURL,
        sessionless=True)
    for pc in newSite.store.query(_PowerupConnector,
                                  AND(_PowerupConnector.powerup == newSite,
                                      _PowerupConnector.interface == u'xmantissa.ixmantissa.ISessionlessSiteRootPlugin')):
        pc.item.powerDown(newSite, ISessionlessSiteRootPlugin)
    return newSite
upgrade.registerUpgrader(upgradeStaticSite1To2, 'static_web_site', 1, 2)


class StaticRedirect(Item, PrefixURLMixin):
    implements(IResource,
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

class WebSite(Item, Service, SiteRootMixin, InstallableMixin):
    typeName = 'mantissa_web_powerup'
    schemaVersion = 1

    hitCount = integer(default=0)
    installedOn = reference()

    portNumber = integer(default=0)
    securePortNumber = integer(default=0)
    certificateFile = bytes(default=None)

    parent = inmemory()
    running = inmemory()
    name = inmemory()

    port = inmemory()
    securePort = inmemory()
    site = inmemory()

    debug = False

    def activate(self):
        self.site = None
        self.port = None
        self.securePort = None

    def installOn(self, other):
        super(WebSite, self).installOn(other)
        other.powerUp(self, IService)
        other.powerUp(self, IResource)
        self.setServiceParent(other)

        StaticSite(store=other,
                   prefixURL=u'static/mantissa',
                   staticContentPath=sibpath(__file__, u'static')).installOn(other)

    def privilegedStartService(self):
        if SSL is None and self.securePortNumber is not None:
            raise WebConfigurationError(
                "No SSL support: you need to install OpenSSL to serve HTTPS")

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

        self.site = AxiomSite(self.store, UnguardedWrapper(self.store, guardedRoot))

        if self.debug:
            self.site = policies.TrafficLoggingFactory(self.site, 'http')

        if self.portNumber is not None:
            self.port = reactor.listenTCP(self.portNumber, self.site)

        if self.securePortNumber is not None and self.certificateFile is not None:
            cert = sslverify.PrivateCertificate.loadPEM(file(self.certificateFile).read())
            certOpts = sslverify.OpenSSLCertificateOptions(
                cert.privateKey.original,
                cert.original,
                requireCertificate=False,
                method=SSL.SSLv23_METHOD)
            self.securePort = reactor.listenSSL(self.securePortNumber, self.site, certOpts)


    def stopService(self):
        dl = []
        if self.port is not None:
            dl.append(defer.maybeDeferred(self.port.stopListening))
            self.port = None
        if self.securePort is not None:
            dl.append(defer.maybeDeferred(self.securePort.stopListening))
            self.securePort = None
        return defer.DeferredList(dl)

