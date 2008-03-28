
from epsilon import hotfix
hotfix.require('twisted', 'trial_assertwarns')

import sha

from zope.interface import implements
from zope.interface.verify import verifyObject

try:
    from cssutils import CSSParser
except ImportError:
    CSSParser = None

from twisted.python.components import registerAdapter
from twisted.internet.address import IPv4Address
from twisted.trial import unittest, util
from twisted.python.filepath import FilePath

from nevow.flat import flatten
from nevow.context import WebContext
from nevow.testutil import FakeRequest
from nevow.url import URL
from nevow.inevow import IResource, IRequest
from nevow.rend import WovenContext, NotFound
from nevow.athena import LivePage
from nevow.guard import LOGIN_AVATAR

from axiom import userbase
from axiom.store import Store
from axiom.dependency import installOn
from axiom.plugins.mantissacmd import Mantissa

from xmantissa.ixmantissa import (
    IProtocolFactoryFactory, ISiteURLGenerator, ISiteRootPlugin)
from xmantissa.port import TCPPort, SSLPort
from xmantissa import website, publicweb
from xmantissa.websharing import UserIndexPage
from xmantissa.signup import PasswordResetResource
from xmantissa.publicweb import LoginPage
from xmantissa.offering import installOffering
from xmantissa.plugins.baseoff import baseOffering
from xmantissa.cachejs import theHashModuleProvider

from xmantissa.website import MantissaLivePage, APIKey
from xmantissa.web import SecuringWrapper, _SecureWrapper, StaticContent, UnguardedWrapper, SiteConfiguration


maybeEncryptedRootWarningMessage = (
    "Use ISiteURLGenerator.rootURL instead of WebSite.maybeEncryptedRoot")
maybeEncryptedRootSuppression = util.suppress(
    message=maybeEncryptedRootWarningMessage,
    category=DeprecationWarning)



class SiteConfigurationTests(unittest.TestCase):
    """
    L{xmantissa.web.Site} defines how to create an HTTP server.
    """
    def setUp(self):
        self.domain = u"example.com"
        self.store = Store()
        self.site = SiteConfiguration(store=self.store, hostname=self.domain)


    def test_interfaces(self):
        """
        L{SiteConfiguration} implements L{IProtocolFactoryFactory} and
        L{ISiteURLGenerator}.
        """
        self.assertTrue(verifyObject(ISiteURLGenerator, self.site))
        self.assertTrue(verifyObject(IProtocolFactoryFactory, self.site))


    def _baseTest(self, portType, scheme, portNumber, method):
        portType(store=self.store, portNumber=portNumber, factory=self.site)
        self.assertEquals(
            getattr(self.site, method)(), URL(scheme, self.domain))


    def test_cleartextRoot(self):
        """
        L{SiteConfiguration.cleartextRoot} method returns the proper URL for
        HTTP communication with this site.
        """
        self._baseTest(TCPPort, 'http', 80, 'cleartextRoot')


    def test_encryptedRoot(self):
        """
        L{SiteConfiguration.encryptedRoot} method returns the proper URL for
        HTTPS communication with this site.
        """
        self._baseTest(SSLPort, 'https', 443, 'encryptedRoot')


    def _nonstandardPortTest(self, portType, scheme, portNumber, method):
        portType(store=self.store, portNumber=portNumber, factory=self.site)
        self.assertEquals(
            getattr(self.site, method)(),
            URL(scheme, '%s:%s' % (self.domain, portNumber)))


    def test_cleartextRootNonstandardPort(self):
        """
        L{SiteConfiguration.cleartextRoot} method returns the proper URL for
        HTTP communication with this site even if the server is listening on a
        non-standard port number.
        """
        self._nonstandardPortTest(TCPPort, 'http', 8000, 'cleartextRoot')


    def test_encryptedRootNonstandardPort(self):
        """
        L{SiteConfiguration.encryptedRoot} method returns the proper URL for
        HTTPS communication with this site even if the server is listening on a
        non-standard port number.
        """
        self._nonstandardPortTest(SSLPort, 'https', 8443, 'encryptedRoot')


    def _unavailableTest(self, method):
        self.assertEquals(getattr(self.site, method)(), None)


    def test_cleartextRootUnavailable(self):
        """
        L{SiteConfiguration.cleartextRoot} method returns None if there is no
        HTTP server listening.
        """
        self._unavailableTest('cleartextRoot')


    def test_encryptedRootUnavailable(self):
        """
        L{SiteConfiguration.encryptedRoot} method returns None if there is no
        HTTPS server listening.
        """
        self._unavailableTest('encryptedRoot')


    def _hostOverrideTest(self, portType, scheme, portNumber, method):
        portType(store=self.store, portNumber=portNumber, factory=self.site)
        self.assertEquals(
            getattr(self.site, method)(u'example.net'),
            URL(scheme, 'example.net'))


    def test_cleartextRootHostOverride(self):
        """
        A hostname passed to L{SiteConfiguration.cleartextRoot} overrides the
        configured hostname in the result.
        """
        self._hostOverrideTest(TCPPort, 'http', 80, 'cleartextRoot')


    def test_encryptedRootHostOverride(self):
        """
        A hostname passed to L{SiteConfiguration.encryptedRoot} overrides the
        configured hostname in the result.
        """
        self._hostOverrideTest(SSLPort, 'https', 443, 'encryptedRoot')


    def _portZero(self, portType, scheme, method):
        randomPort = 7777

        class FakePort(object):
            def getHost(self):
                return IPv4Address('TCP', u'example.com', randomPort)

        port = portType(store=self.store, portNumber=0, factory=self.site)
        port.listeningPort = FakePort()
        self.assertEquals(
            getattr(self.site, method)(),
            URL(scheme, '%s:%s' % (self.domain, randomPort)))


    def test_cleartextRootPortZero(self):
        """
        When the C{portNumber} of a started L{TCPPort} which refers to the
        C{SiteConfiguration} is C{0}, L{SiteConfiguration.cleartextRoot}
        returns an URL with the port number which was actually bound in the
        netloc.
        """
        self._portZero(TCPPort, 'http', 'cleartextRoot')


    def test_encryptedRootPortZero(self):
        """
        When the C{portNumber} of a started L{SSLPort} which refers to the
        C{SiteConfiguration} is C{0}, L{SiteConfiguration.encryptedRoot}
        returns an URL with the port number which was actually bound in the
        netloc.
        """
        self._portZero(SSLPort, 'https', 'encryptedRoot')


    def _portZeroDisconnected(self, portType, method):
        portType(store=self.store, portNumber=0, factory=self.site)
        self.assertEquals(None, getattr(self.site, method)())


    def test_cleartextRootPortZeroDisconnected(self):
        """
        When the C{portNumber} of an unstarted L{TCPPort} which refers to the
        C{SiteConfiguration} is C{0}, L{SiteConfiguration.cleartextRoot}
        returns C{None}.
        """
        self._portZeroDisconnected(TCPPort, 'cleartextRoot')


    def test_encryptedRootPortZeroDisconnected(self):
        """
        When the C{portNumber} of an unstarted L{SSLPort} which refers to the
        C{SiteConfiguration} is C{0}, L{SiteConfiguration.encryptedRoot}
        returns C{None}.
        """
        self._portZeroDisconnected(SSLPort, 'encryptedRoot')


    def test_rootURL(self):
        """
        L{SiteConfiguration.rootURL} returns C{/} for a request made onto the
        hostname with which the L{SiteConfiguration} is configured.
        """
        request = FakeRequest(headers={
            'host': self.domain.encode('ascii')})
        self.assertEqual(self.site.rootURL(request), URL('', ''))


    def test_rootURLWithoutHost(self):
        """
        L{SiteConfiguration.rootURL} returns C{/} for a request made without a
        I{Host} header.
        """
        request = FakeRequest()
        self.assertEqual(self.site.rootURL(request), URL('', ''))


    def test_rootURLWWWSubdomain(self):
        """
        L{SiteConfiguration.rootURL} returns C{/} for a request made onto the
        I{www} subdomain of the hostname of the L{SiteConfiguration}.
        """
        request = FakeRequest(headers={
            'host': 'www.' + self.domain.encode('ascii')})
        self.assertEqual(self.site.rootURL(request), URL('', ''))


    def _differentHostnameTest(self, portType, portNumber, isSecure, scheme):
        request = FakeRequest(isSecure=isSecure, headers={
            'host': 'alice.' + self.domain.encode('ascii')})
        portType(store=self.store, factory=self.site, portNumber=portNumber)
        self.assertEqual(self.site.rootURL(request), URL(scheme, self.domain))


    def test_cleartextRootURLDifferentHostname(self):
        """
        L{SiteConfiguration.rootURL} returns an absolute URL with the HTTP
        scheme and its hostname as the netloc and with a path of C{/} for a
        request made over HTTP onto a hostname different from the hostname of the
        L{SiteConfiguration}.

        """
        self._differentHostnameTest(TCPPort, 80, False, 'http')


    def test_encryptedRootURLDifferentHostname(self):
        """
        L{SiteConfiguration.rootURL} returns an absolute URL with its hostname
        as the netloc and with a path of C{/} for a request made over HTTPS onto a
        hostname different from the hostname of the L{SiteConfiguration}.
        """
        self._differentHostnameTest(SSLPort, 443, True, 'https')


    def _differentHostnameNonstandardPort(self, portType, isSecure, scheme):
        portNumber = 12345
        request = FakeRequest(isSecure=isSecure, headers={
            'host': 'alice.' + self.domain.encode('ascii')})
        portType(store=self.store, factory=self.site, portNumber=portNumber)
        self.assertEqual(
            self.site.rootURL(request),
            URL(scheme, '%s:%s' % (self.domain.encode('ascii'), portNumber)))


    def test_cleartextRootURLDifferentHostnameNonstandardPort(self):
        """
        L{SiteConfiguration.rootURL} returns an absolute URL with an HTTP
        scheme and an explicit port number in the netloc for a request made
        over HTTP onto a hostname different from the hostname of the
        L{SiteConfiguration} if the L{SiteConfiguration} has an HTTP server on
        a non-standard port.
        """
        self._differentHostnameNonstandardPort(TCPPort, False, 'http')


    def test_encryptedRootURLDifferentHostnameNonstandardPort(self):
        """
        L{SiteConfiguration.rootURL} returns an absolute URL with an HTTPS
        scheme and an explicit port number in the netloc for a request made
        over HTTPS onto a hostname different from the hostname of the
        L{SiteConfiguration} if the L{SiteConfiguration} has an HTTPS server on
        a non-standard port.
        """
        self._differentHostnameNonstandardPort(SSLPort, True, 'https')


    def test_rootURLNonstandardRequestPort(self):
        """
        L{SiteConfiguration.rootURL} returns C{/} for a request made onto a
        non-standard port which is one on which the L{SiteConfiguration} is
        configured to listen.
        """
        request = FakeRequest(headers={
            'host': '%s:%s' % (self.domain.encode('ascii'), 54321)})
        TCPPort(store=self.store, factory=self.site, portNumber=54321)
        self.assertEqual(self.site.rootURL(request), URL('', ''))



class StylesheetRewritingRequestWrapperTests(unittest.TestCase):
    """
    Tests for L{StylesheetRewritingRequestWrapper}.
    """
    def test_replaceMantissa(self):
        """
        L{StylesheetRewritingRequestWrapper._replace} changes URLs of the form
        I{/Mantissa/foo} to I{<rootURL>/static/mantissa-base/foo}.
        """
        request = object()
        roots = {request: URL.fromString('/bar/')}
        wrapper = website.StylesheetRewritingRequestWrapper(request, [], roots.get)
        self.assertEqual(
            wrapper._replace('/Mantissa/foo.png'),
            '/bar/static/mantissa-base/foo.png')


    def test_replaceOtherOffering(self):
        """
        L{StylesheetRewritingRequestWrapper._replace} changes URLs of the form
        I{/Something/foo} to I{<rootURL>/static/Something/foo} if C{Something}
        gives the name of an installed offering with a static content path.
        """
        request = object()
        roots = {request: URL.fromString('/bar/')}
        wrapper = website.StylesheetRewritingRequestWrapper(request, ['OfferingName'], roots.get)
        self.assertEqual(
            wrapper._replace('/OfferingName/foo.png'),
            '/bar/static/OfferingName/foo.png')


    def test_nonOfferingOnlyGivenPrefix(self):
        """
        L{StylesheetRewritingRequestWrapper._replace} only changes URLs of the
        form I{/Something/foo} so they are beneath the root URL if C{Something}
        does not give the name of an installed offering.
        """
        request = object()
        roots = {request: URL.fromString('/bar/')}
        wrapper = website.StylesheetRewritingRequestWrapper(
            request, ['Foo'], roots.get)
        self.assertEqual(
            wrapper._replace('/OfferingName/foo.png'),
            '/bar/OfferingName/foo.png')


    def test_shortURL(self):
        """
        L{StylesheetRewritingRequestWrapper._replace} changes URLs with only
        one segment so they are beneath the root URL.
        """
        request = object()
        roots = {request: URL.fromString('/bar/')}
        wrapper = website.StylesheetRewritingRequestWrapper(
            request, [], roots.get)
        self.assertEqual(
            wrapper._replace('/'),
            '/bar/')


    def test_absoluteURL(self):
        """
        L{StylesheetRewritingRequestWrapper._replace} does not change absolute
        URLs.
        """
        wrapper = website.StylesheetRewritingRequestWrapper(object(), [], None)
        self.assertEqual(
            wrapper._replace('http://example.com/foo'),
            'http://example.com/foo')


    def test_relativeUnmodified(self):
        """
        L{StylesheetRewritingRequestWrapper._replace} does not change URLs with
        relative paths.
        """
        wrapper = website.StylesheetRewritingRequestWrapper(object(), [], None)
        self.assertEqual(wrapper._replace('relative/path'), 'relative/path')


    def test_finish(self):
        """
        L{StylesheetRewritingRequestWrapper.finish} causes all written bytes to
        be translated with C{_replace} written to the wrapped request.
        """
        stylesheetFormat = """
            .foo {
                background-image: url(%s)
            }
        """
        originalStylesheet = stylesheetFormat % ("/Foo/bar",)
        expectedStylesheet = stylesheetFormat % ("/bar/Foo/bar",)

        request = FakeRequest()
        roots = {request: URL.fromString('/bar/')}
        wrapper = website.StylesheetRewritingRequestWrapper(
            request, [], roots.get)
        wrapper.write(originalStylesheet)
        wrapper.finish()
        # Parse and serialize both versions to normalize whitespace so we can
        # make a comparison.
        parser = CSSParser()
        self.assertEqual(
            parser.parseString(request.accumulator).cssText,
            parser.parseString(expectedStylesheet).cssText)
    if CSSParser is None:
        test_finish.skip = "Stylesheet rewriting test requires cssutils package."



class LoginPageTests(unittest.TestCase):
    """
    Tests for functionality related to login.
    """
    domain = u"example.com"

    def setUp(self):
        """
        Create a L{Store}, L{WebSite} and necessary request-related objects to
        test L{LoginPage}.
        """
        self.siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.siteStore, self.domain, u"", False)
        self.site = self.siteStore.findUnique(SiteConfiguration)
        installOn(
            TCPPort(store=self.siteStore, factory=self.site, portNumber=80),
            self.siteStore)
        self.context = WebContext()
        self.request = FakeRequest()
        self.context.remember(self.request)


    def test_fromRequest(self):
        """
        L{LoginPage.fromRequest} should return a two-tuple of the class it is
        called on and an empty tuple.
        """
        request = FakeRequest(
            uri='/foo/bar/baz',
            currentSegments=['foo'],
            args={'quux': ['corge']})

        class StubLoginPage(LoginPage):
            def __init__(self, store, segments, arguments):
                self.store = store
                self.segments = segments
                self.arguments = arguments

        page = StubLoginPage.fromRequest(self.siteStore, request)
        self.assertTrue(isinstance(page, StubLoginPage))
        self.assertIdentical(page.store, self.siteStore)
        self.assertEqual(page.segments, ['foo', 'bar'])
        self.assertEqual(page.arguments, {'quux': ['corge']})


    def test_staticShellContent(self):
        """
        The L{IStaticShellContent} adapter for the C{store} argument to
        L{LoginPage.__init__} should become its C{staticContent} attribute.
        """
        originalInterface = publicweb.IStaticShellContent
        adaptions = []
        result = object()
        def stubInterface(object, default):
            adaptions.append((object, default))
            return result
        publicweb.IStaticShellContent = stubInterface
        try:
            page = LoginPage(self.siteStore)
        finally:
            publicweb.IStaticShellContent = originalInterface
        self.assertEqual(len(adaptions), 1)
        self.assertIdentical(adaptions[0][0], self.siteStore)
        self.assertIdentical(page.staticContent, result)


    def test_segments(self):
        """
        L{LoginPage.beforeRender} should fill the I{login-action} slot with an
        L{URL} which includes all the segments given to the L{LoginPage}.
        """
        segments = ('foo', 'bar')
        page = LoginPage(self.siteStore, segments)
        page.beforeRender(self.context)
        loginAction = self.context.locateSlotData('login-action')
        expectedLocation = URL.fromString('/')
        for segment in (LOGIN_AVATAR,) + segments:
            expectedLocation = expectedLocation.child(segment)
        self.assertEqual(loginAction, expectedLocation)


    def test_queryArguments(self):
        """
        L{LoginPage.beforeRender} should fill the I{login-action} slot with an
        L{URL} which includes all the query arguments given to the
        L{LoginPage}.
        """
        args = {'foo': ['bar']}
        page = LoginPage(self.siteStore, (), args)
        page.beforeRender(self.context)
        loginAction = self.context.locateSlotData('login-action')
        expectedLocation = URL.fromString('/')
        expectedLocation = expectedLocation.child(LOGIN_AVATAR)
        expectedLocation = expectedLocation.add('foo', 'bar')
        self.assertEqual(loginAction, expectedLocation)


    def test_locateChildPreservesSegments(self):
        """
        L{LoginPage.locateChild} should create a new L{LoginPage} with segments
        extracted from the traversal context.
        """
        segments = ('foo', 'bar')
        page = LoginPage(self.siteStore)
        child, remaining = page.locateChild(self.context, segments)
        self.assertTrue(isinstance(child, LoginPage))
        self.assertEqual(remaining, ())
        self.assertEqual(child.segments, segments)


    def test_locateChildPreservesQueryArguments(self):
        """
        L{LoginPage.locateChild} should create a new L{LoginPage} with query
        arguments extracted from the traversal context.
        """
        self.request.args = {'foo': ['bar']}
        page = LoginPage(self.siteStore)
        child, remaining = page.locateChild(self.context, None)
        self.assertTrue(isinstance(child, LoginPage))
        self.assertEqual(child.arguments, self.request.args)



class UnguardedWrapperTests(unittest.TestCase):
    """
    Tests for L{UnguardedWrapper}.
    """
    def setUp(self):
        """
        Set up a store with a valid offering to test against.
        """
        self.store = Store()
        installOffering(self.store, baseOffering, {})
        self.site = ISiteURLGenerator(self.store)


    def test_live(self):
        """
        L{UnguardedWrapper} has a I{live} child which returns a L{LivePage}
        instance.
        """
        request = FakeRequest(uri='/live/foo', currentSegments=[])
        wrapper = UnguardedWrapper(self.store, None)
        resource = wrapper.child_live(request)
        self.assertTrue(isinstance(resource, LivePage))


    def test_jsmodules(self):
        """
        L{UnguardedWrapper} has a I{__jsmodules__} child which returns a
        L{LivePage} instance.
        """
        request = FakeRequest(uri='/__jsmodule__/foo', currentSegments=[])
        wrapper = UnguardedWrapper(None, None)
        resource = wrapper.child___jsmodule__(request)

        # This is weak.  Identity of this object doesn't matter.  The caching
        # and jsmodule serving features are what matter. -exarkun
        self.assertIdentical(resource, theHashModuleProvider)


    def test_static(self):
        """
        L{UnguardedWrapper} has a I{static} child which returns a
        L{StaticContent} instance.
        """
        request = FakeRequest(uri='/static/extra', currentSegments=[])
        wrapper = UnguardedWrapper(self.store, None)
        resource = wrapper.child_static(request)
        self.assertTrue(isinstance(resource, StaticContent))
        self.assertEqual(
            resource.staticPaths,
            {baseOffering.name: baseOffering.staticContentPath})



class AnonymousSiteTests(unittest.TestCase):
    def setUp(self):
        """
        Set up a store with a valid offering to test against.
        """
        self.store = Store()
        installOffering(self.store, baseOffering, {})
        self.site = ISiteURLGenerator(self.store)
        self.resource = IResource(self.store)


    def test_login(self):
        """
        L{AnonymousSite} has a I{login} child which returns a L{LoginPage}
        instance.
        """
        host = 'example.org'
        port = 1234
        netloc = '%s:%d' % (host, port)

        request = FakeRequest(
            headers={'host': netloc},
            uri='/login/foo',
            currentSegments=[],
            isSecure=False)

        self.site.hostname = host.decode('ascii')
        SSLPort(store=self.store, portNumber=port, factory=self.site)

        resource, segments = self.resource.locateChild(request, ("login",))
        self.assertTrue(isinstance(resource, LoginPage))
        self.assertIdentical(resource.store, self.store)
        self.assertEqual(resource.segments, ())
        self.assertEqual(resource.arguments, {})
        self.assertEqual(segments, ())


    def test_resetPassword(self):
        """
        L{AnonymousSite} has a I{resetPassword} child which returns a
        L{PasswordResetResource} instance.
        """
        resource, segments = self.resource.locateChild(
            FakeRequest(headers={"host": "example.com"}),
            ("resetPassword",))
        self.assertTrue(isinstance(resource, PasswordResetResource))
        self.assertIdentical(resource.store, self.store)
        self.assertEqual(segments, ())


    def test_users(self):
        """
        L{AnonymousSite} has a I{users} child which returns a L{UserIndexPage}
        instance.
        """
        resource, segments = self.resource.locateChild(
            FakeRequest(headers={"host": "example.com"}), ("users",))
        self.assertTrue(isinstance(resource, UserIndexPage))
        self.assertIdentical(
            resource.loginSystem, self.store.findUnique(userbase.LoginSystem))
        self.assertEqual(segments, ())


    def test_notFound(self):
        """
        L{AnonymousSite.locateChild} returns L{NotFound} for requests it cannot
        find another response for.
        """
        result = self.resource.locateChild(
            FakeRequest(headers={"host": "example.com"}),
            ("foo", "bar"))
        self.assertIdentical(result, NotFound)


    def test_siteRootPlugin(self):
        """
        L{AnonymousSite.locateChild} queries for L{ISiteRootPlugin} providers
        and returns the result of their I{resourceFactory} method if it is not
        C{None}.
        """
        result = object()
        calledWith = []
        class SiteRootPlugin(object):
            def resourceFactory(self, segments):
                calledWith.append(segments)
                return result

        self.store.inMemoryPowerUp(SiteRootPlugin(), ISiteRootPlugin)
        self.assertIdentical(
            self.resource.locateChild(
                FakeRequest(headers={"host": "example.com"}),
                ("foo", "bar")),
            result)
        self.assertEqual(calledWith, [("foo", "bar")])



class StubResource(object):
    """
    An L{IResource} implementation which behaves in a way which is useful for
    testing L{SecuringWrapper}.

    @ivar childResource: The object which will be returned as a child resource
        from C{locateChild}.
    @ivar childSegments: The object which will be returned as the
        unconsumed segments from C{locateChild}.
    @ivar renderContent: The object to return from C{renderHTTP}.
    @ivar renderedWithContext: The argument passed to C{renderHTTP}.
    """
    implements(IResource)

    def __init__(self, childResource, childSegments, renderContent):
        self.childResource = childResource
        self.childSegments = childSegments
        self.renderContent = renderContent


    def renderHTTP(self, context):
        self.renderedWithContext = context
        return self.renderContent


    def locateChild(self, context, segments):
        self.locatedWith = (context, segments)
        return self.childResource, self.childSegments



class NotResource(object):
    """
    A class which does not implement L{IResource}.
    """



class NotResourceAdapter(object):
    """
    An adapter from L{NotResource} to L{IResource} (not really - but close
    enough for the tests).
    """
    def __init__(self, notResource):
        self.notResource = notResource


registerAdapter(NotResourceAdapter, NotResource, IResource)



class SecuringWrapperTests(unittest.TestCase):
    """
    L{SecuringWrapper} makes sure that any resource which is eventually
    retrieved from a wrapped resource and then rendered is rendered over HTTPS
    if possible and desired.
    """
    def setUp(self):
        """
        Create a resource and a wrapper to test.
        """
        self.store = Store()
        self.urlGenerator = SiteConfiguration(store=self.store,
                                              hostname=u"example.com")
        self.child = StubResource(None, None, None)
        self.childSegments = ("baz", "quux")
        self.content = "some bytes perhaps"
        self.resource = StubResource(
            self.child, self.childSegments, self.content)
        self.wrapper = SecuringWrapper(self.urlGenerator, self.resource)


    def test_locateChildHTTPS(self):
        """
        L{SecuringWrapper.locateChild} returns the wrapped resource and the
        unmodified segments if it is called with a secure request.
        """
        segments = ("foo", "bar")
        request = FakeRequest(isSecure=True)
        newResource, newSegments = self.wrapper.locateChild(request, segments)
        self.assertIdentical(newResource, self.resource)
        self.assertEqual(newSegments, segments)


    def test_locateChildHTTP(self):
        """
        L{SecuringWrapper.locateChild} returns a L{_SecureWrapper} wrapped
        around its own wrapped resource along with the unmodified segments if
        it is called with an insecure request.
        """
        segments = ("foo", "bar")
        request = FakeRequest(isSecure=False)
        newResource, newSegments = self.wrapper.locateChild(request, segments)
        self.assertTrue(isinstance(newResource, _SecureWrapper))
        self.assertIdentical(newResource.urlGenerator, self.urlGenerator)
        self.assertIdentical(newResource.wrappedResource, self.resource)
        self.assertEqual(newSegments, segments)


    def test_renderHTTPNeedsSecure(self):
        """
        L{SecuringWrapper.renderHTTP} returns a L{URL} pointing at the same
        location as the request URI but with an https scheme if the wrapped
        resource has a C{needsSecure} attribute with a true value and the
        request is over http.
        """
        SSLPort(store=self.store, factory=self.urlGenerator, portNumber=443)
        request = FakeRequest(
            isSecure=False, uri='/bar/baz', currentSegments=['bar', 'baz'])
        self.resource.needsSecure = True
        result = self.wrapper.renderHTTP(request)
        self.assertEqual(
            result, URL('https', self.urlGenerator.hostname, ['bar', 'baz']))


    def test_renderHTTP(self):
        """
        L{SecuringWrapper.renderHTTP} returns the result of the wrapped
        resource's C{renderHTTP} method if the wrapped resource does not have a
        C{needsSecure} attribute with a true value.
        """
        request = FakeRequest(
            isSecure=False, uri='/bar/baz', currentSegments=['bar', 'baz'])
        result = self.wrapper.renderHTTP(request)
        self.assertIdentical(self.resource.renderedWithContext, request)
        self.assertEqual(result, self.content)


    def test_renderHTTPS(self):
        """
        L{SecuringWrapper.renderHTTP} returns the result of the wrapped
        resource's C{renderHTTP} method if it is called with a secure request.
        """
        request = FakeRequest(isSecure=True)
        result = self.wrapper.renderHTTP(request)
        self.assertIdentical(self.resource.renderedWithContext, request)
        self.assertEqual(result, self.content)


    def test_renderHTTPCannotSecure(self):
        """
        L{SecuringWrapper.renderHTTP} returns the result of the wrapped
        resource's C{renderHTTP} method if it is invoked over http but there is
        no https location available.
        """
        request = FakeRequest(isSecure=False)
        result = self.wrapper.renderHTTP(request)
        self.assertIdentical(self.resource.renderedWithContext, request)
        self.assertEqual(result, self.content)


    def test_childLocateChild(self):
        """
        L{_SecureWrapper.locateChild} returns a L{Deferred} which is called
        back with the result of the wrapped resource's C{locateChild} method
        wrapped in another L{_SecureWrapper}.
        """
        segments = ('foo', 'bar')
        request = FakeRequest()
        wrapper = _SecureWrapper(self.urlGenerator, self.resource)
        result = wrapper.locateChild(request, segments)
        def locatedChild((resource, segments)):
            self.assertTrue(isinstance(resource, _SecureWrapper))
            self.assertIdentical(resource.wrappedResource, self.child)
            self.assertEqual(segments, self.childSegments)
        result.addCallback(locatedChild)
        return result


    def test_notFound(self):
        """
        A L{_SecureWrapper.locateChild} lets L{NotFound} results from the
        wrapped resource pass through.
        """
        segments = ('foo', 'bar')
        request = FakeRequest()
        self.resource.childResource = None
        self.resource.childSegments = ()
        wrapper = _SecureWrapper(self.urlGenerator, self.resource)
        result = wrapper.locateChild(request, segments)
        def locatedChild(result):
            self.assertIdentical(result, NotFound)
        result.addCallback(locatedChild)
        return result


    def test_adaption(self):
        """
        A L{_SecureWrapper} constructed with an object which does not provide
        L{IResource} adapts it to L{IResource} and operates on the result.
        """
        notResource = NotResource()
        wrapper = _SecureWrapper(self.urlGenerator, notResource)
        self.assertTrue(isinstance(wrapper.wrappedResource, NotResourceAdapter))
        self.assertIdentical(wrapper.wrappedResource.notResource, notResource)



class AthenaResourcesTestCase(unittest.TestCase):
    """
    Test aspects of L{GenericNavigationAthenaPage}.
    """

    hostname = 'test-mantissa-live-page-mixin.example.com'
    def _preRender(self, resource):
        """
        Test helper which executes beforeRender on the given resource.

        This is used on live resources so that they don't start message queue
        timers.
        """
        ctx = WovenContext()
        req = FakeRequest(headers={'host': self.hostname})
        ctx.remember(req, IRequest)
        resource.beforeRender(ctx)


    def makeLivePage(self):
        """
        Create a MantissaLivePage instance for testing.
        """
        siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(siteStore, self.hostname.decode('ascii'), u"", False)
        return MantissaLivePage(ISiteURLGenerator(siteStore))


    def test_transportRoot(self):
        """
        The transport root should always point at the '/live' transport root
        provided to avoid database interaction while invoking the transport.
        """
        livePage = self.makeLivePage()
        self.assertEquals(flatten(livePage.transportRoot), 'http://localhost/live')


    def test_debuggableMantissaLivePage(self):
        """
        L{MantissaLivePage.getJSModuleURL}'s depends on state from page
        rendering, but it should provide a helpful error message in the case
        where that state has not yet been set up.
        """
        livePage = self.makeLivePage()
        self.assertRaises(NotImplementedError, livePage.getJSModuleURL, 'Mantissa')


    def test_beforeRenderSetsModuleRoot(self):
        """
        L{MantissaLivePage.beforeRender} should set I{_moduleRoot} to the
        C{__jsmodule__} child of the URL returned by the I{rootURL}
        method of the L{WebSite} it wraps.
        """
        receivedRequests = []
        root = URL(netloc='example.com', pathsegs=['a', 'b'])
        class FakeWebSite(object):
            def rootURL(self, request):
                receivedRequests.append(request)
                return root
        request = FakeRequest()
        page = MantissaLivePage(FakeWebSite())
        page.beforeRender(request)
        self.assertEqual(receivedRequests, [request])
        self.assertEqual(page._moduleRoot, root.child('__jsmodule__'))


    def test_getJSModuleURL(self):
        """
        L{MantissaLivePage.getJSModuleURL} should return a child of its
        C{_moduleRoot} attribute of the form::

            _moduleRoot/<SHA1 digest of module contents>/Package.ModuleName
        """
        module = 'Mantissa'
        url = URL(scheme='https', netloc='example.com', pathsegs=['foo'])
        page = MantissaLivePage(None)
        page._moduleRoot = url
        jsDir = FilePath(__file__).parent().parent().child("js")
        modulePath = jsDir.child(module).child("__init__.js")
        moduleContents = modulePath.open().read()
        expect = sha.new(moduleContents).hexdigest()
        self.assertEqual(page.getJSModuleURL(module),
                         url.child(expect).child(module))




class APIKeyTestCase(unittest.TestCase):
    """
    Tests for L{APIKey}.
    """
    def setUp(self):
        """
        Make a store.
        """
        self.store = Store()


    def test_getKeyForAPINone(self):
        """
        If there is no existing key for the named API, L{APIKey.getKeyForAPI}
        should return C{None}.
        """
        self.assertIdentical(
            APIKey.getKeyForAPI(self.store, u'this is an API name.'),
            None)


    def test_getKeyForAPIExisting(self):
        """
        If there is an existing key for the named API, L{APIKey.getKeyForAPI}
        should return it.
        """
        theAPIName = u'this is an API name.'
        existingAPIKey = APIKey(
            store=self.store,
            apiName=theAPIName,
            apiKey=u'this is an API key.')
        self.assertIdentical(
            existingAPIKey,
            APIKey.getKeyForAPI(self.store, theAPIName))


    def test_setKeyForAPINew(self):
        """
        If there is no existing key for the named API, L{APIKey.setKeyForAPI}
        should create a new L{APIKey} item.
        """
        theAPIKey = u'this is an API key.'
        theAPIName = u'this is an API name.'
        apiKey = APIKey.setKeyForAPI(
            self.store, theAPIName, theAPIKey)
        self.assertIdentical(apiKey, self.store.findUnique(APIKey))
        self.assertEqual(theAPIKey, apiKey.apiKey)
        self.assertEqual(theAPIName, apiKey.apiName)


    def test_setKeyForAPIExisting(self):
        """
        If there is an existing for the named API, L{APIKey.setKeyForAPI}
        should update its I{apiKey} attribute.
        """
        theAPIKey = u'this is an API key.'
        theAPIName = u'this is an API name.'
        existingAPIKey = APIKey(
            store=self.store, apiName=theAPIName, apiKey=theAPIKey)
        newAPIKey = u'this is a new API key'
        returnedAPIKey = APIKey.setKeyForAPI(
            self.store, theAPIName, newAPIKey)
        self.assertIdentical(existingAPIKey, returnedAPIKey)
        self.assertEqual(existingAPIKey.apiName, theAPIName)
        self.assertEqual(existingAPIKey.apiKey, newAPIKey)



class VirtualHostWrapperTests(unittest.TestCase):
    """
    Tests for L{VirtualHostWrapper}.
    """
    def test_nonSubdomain(self):
        """
        L{VirtualHostWrapper.subdomain} returns C{None} when passed a hostname
        which is not a subdomain of a domain of the site.
        """
        site = Store()
        wrapper = website.VirtualHostWrapper(site, None, None)
        self.assertIdentical(wrapper.subdomain("example.com"), None)


    def test_subdomain(self):
        """
        L{VirtualHostWrapper.subdomain} returns a two-tuple of a username and a
        domain name when passed a hostname which is a subdomain of a known
        domain.
        """
        site = Store()
        wrapper = website.VirtualHostWrapper(site, None, None)
        userbase.LoginMethod(
            store=site,
            account=site,
            protocol=u'*',
            internal=True,
            verified=True,
            localpart=u'alice',
            domain=u'example.com')
        self.assertEqual(
            wrapper.subdomain("bob.example.com"),
            ("bob", "example.com"))


    def test_wwwSubdomain(self):
        """
        L{VirtualHostWrapper.subdomain} returns C{None} when passed a hostname
        which is the I{www} subdomain of a domain of the site.
        """
        site = Store()
        wrapper = website.VirtualHostWrapper(site, None, None)
        userbase.LoginMethod(
            store=site,
            account=site,
            protocol=u'*',
            internal=True,
            verified=True,
            localpart=u'alice',
            domain=u'example.com')
        self.assertIdentical(wrapper.subdomain("www.example.com"), None)


    def test_subdomainWithPort(self):
        """
        L{VirtualHostWrapper.subdomain} handles hostnames with a port component
        as if they did not have a port component.
        """
        site = Store()
        wrapper = website.VirtualHostWrapper(site, None, None)
        userbase.LoginMethod(
            store=site,
            account=site,
            protocol=u'*',
            internal=True,
            verified=True,
            localpart=u'alice',
            domain=u'example.com')
        self.assertEqual(
            wrapper.subdomain("bob.example.com:8080"),
            ("bob", "example.com"))
