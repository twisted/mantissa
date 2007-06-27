
import sha
import socket

from zope.interface import implements

from twisted.internet.address import IPv4Address
from twisted.trial import unittest
from twisted.application import service
from twisted.web import http
from twisted.python.filepath import FilePath

from nevow.flat import flatten
from nevow.context import WebContext
from nevow.testutil import AccumulatingFakeRequest, renderPage
from nevow.testutil import renderLivePage, FakeRequest
from nevow.url import URL
from nevow.guard import LOGIN_AVATAR
from nevow.inevow import IResource, IRequest
from nevow.rend import WovenContext
from nevow.athena import LivePage

from epsilon.scripts import certcreate

from axiom import userbase
from axiom.store import Store
from axiom.dependency import installOn
from axiom.test.util import getPristineStore

from xmantissa.port import TCPPort, SSLPort
from xmantissa import website, signup, publicweb
from xmantissa.publicweb import LoginPage
from xmantissa.product import Product

from xmantissa.website import SiteRootMixin, WebSite
from xmantissa.website import MantissaLivePage

from xmantissa.cachejs import HashedJSModuleProvider

# Secure port number used for testing.
TEST_SECURE_PORT = 9123


def createStore(testCase):
    """
    Create a new Store in a temporary directory retrieved from C{testCase}.
    Give it a LoginSystem and create an SSL certificate in its files directory.

    @param testCase: The L{unittest.TestCase} by which the returned Store will
    be used.

    @rtype: L{Store}
    """
    dbdir = testCase.mktemp()
    store = Store(dbdir)
    login = userbase.LoginSystem(store=store)
    installOn(login, store)
    certPath = store.newFilePath('server.pem')
    certcreate.main(['--filename', certPath.path, '--quiet'])
    return store



class WebSiteTestCase(unittest.TestCase):
    def setUp(self):
        self.origFunction = http._logDateTimeStart
        http._logDateTimeStart = lambda: None

        self.store = getPristineStore(self, createStore)
        self.certPath = self.store.filesdir.child('server.pem')
        svc = service.IService(self.store)
        svc.privilegedStartService()
        svc.startService()


    def tearDown(self):
        http._logDateTimeStart = self.origFunction
        del self.origFunction
        svc = service.IService(self.store)
        return svc.stopService()


    def test_cleartextRoot(self):
        """
        Test that the L{WebSite.cleartextRoot} method returns the proper URL
        for HTTP communication with this site.
        """
        ws = website.WebSite(store=self.store, hostname=u'example.com')
        TCPPort(store=self.store, portNumber=80, factory=ws)
        self.assertEquals(
            flatten(ws.cleartextRoot()),
            'http://example.com/')


    def test_cleartextRootNonstandardPort(self):
        """
        Test that the L{WebSite.cleartextRoot} method returns the proper URL
        for HTTP communication with this site even if the server is listening
        on a funky port number.
        """
        ws = website.WebSite(store=self.store, hostname=u'example.com')
        TCPPort(store=self.store, portNumber=8000, factory=ws)
        self.assertEquals(
            flatten(ws.cleartextRoot()),
            'http://example.com:8000/')


    def test_cleartextRootUnavailable(self):
        """
        Test that the L{WebSite.cleartextRoot} method returns None if there is
        no HTTP server listening.
        """
        ws = website.WebSite(store=self.store)
        self.assertEquals(ws.cleartextRoot(), None)


    def test_cleartextRootWithoutHostname(self):
        """
        Test that the L{WebSite.cleartextRoot} method returns a best-guess URL
        if there is no hostname available.
        """
        ws = website.WebSite(store=self.store)
        TCPPort(store=self.store, portNumber=8000, factory=ws)
        self.assertEquals(
            flatten(ws.cleartextRoot()),
            'http://%s:8000/' % (socket.getfqdn(),))


    def test_cleartextRootHostOverride(self):
        """
        Test that if a hostname is explicitly passed to
        L{WebSite.cleartextRoot}, it overrides the configured hostname in the
        result.
        """
        ws = website.WebSite(store=self.store, hostname=u'example.com')
        TCPPort(store=self.store, portNumber=80, factory=ws)
        self.assertEquals(
            flatten(ws.cleartextRoot(u'example.net')),
            'http://example.net/')


    def test_cleartextRootPortZero(self):
        """
        If C{WebSite.portNumber} is 0, then the server will begin
        listening on a random port. Check that L{WebSite.cleartextRoot}
        will return the right port when this is the case.
        """
        randomPort = 7777

        class FakePort(object):
            def getHost(self):
                return IPv4Address('TCP', u'example.com', randomPort)

        ws = website.WebSite(store=self.store, hostname=u'example.com')
        port = TCPPort(store=self.store, portNumber=0, factory=ws)
        port.listeningPort = FakePort()
        self.assertEquals(flatten(ws.cleartextRoot()),
                          'http://example.com:%s/' % (randomPort,))


    def test_cleartextRootPortZeroDisconnected(self):
        """
        If C{WebSite.securePortNumber} is 0 and the server is not listening
        then there is no valid URL. Check that L{WebSite.cleartextRoot}
        returns None.
        """
        ws = website.WebSite(store=self.store)
        port = TCPPort(store=self.store, portNumber=0, factory=ws)
        self.assertEquals(None, ws.cleartextRoot())


    def test_encryptedRoot(self):
        """
        Test that the L{WebSite.encryptedRoot} method returns the proper URL
        for HTTPS communication with this site.
        """
        ws = website.WebSite(store=self.store,hostname=u'example.com')
        SSLPort(store=self.store, portNumber=443, factory=ws)
        self.assertEquals(flatten(ws.encryptedRoot()), 'https://example.com/')


    def test_encryptedRootNonstandardPort(self):
        """
        Test that the L{WebSite.encryptedRoot} method returns the proper URL
        for HTTPS communication with this site even if the server is listening
        on a funky port number.
        """
        ws = website.WebSite(store=self.store, hostname=u'example.com')
        SSLPort(store=self.store, portNumber=8443, factory=ws)
        self.assertEquals(
            flatten(ws.encryptedRoot()),
            'https://example.com:8443/')


    def test_encryptedRootUnavailable(self):
        """
        Test that the L{WebSite.encryptedRoot} method returns None if there is
        no HTTP server listening.
        """
        ws = website.WebSite(store=self.store)
        self.assertEquals(ws.encryptedRoot(), None)


    def test_encryptedRootWithoutHostname(self):
        """
        Test that the L{WebSite.encryptedRoot} method returns a non-universal
        URL if there is no hostname available.
        """
        ws = website.WebSite(store=self.store)
        SSLPort(store=self.store, portNumber=8443, factory=ws)

        self.assertEquals(
            flatten(ws.encryptedRoot()),
            'https://%s:8443/' % (socket.getfqdn(),))


    def test_encryptedRootHostOverride(self):
        """
        Test that if a hostname is explicitly passed to
        L{WebSite.encryptedRoot}, it overrides the configured hostname in the
        result.
        """
        ws = website.WebSite(store=self.store, hostname=u'example.com')
        SSLPort(store=self.store, portNumber=443, factory=ws)
        self.assertEquals(
            flatten(ws.encryptedRoot(u'example.net')),
            'https://example.net/')


    def test_encryptedRootPortZero(self):
        """
        If C{WebSite.securePortNumber} is 0, then the server will begin
        listening on a random port. Check that L{WebSite.encryptedRoot}
        will return the right port when this is the case.
        """
        randomPort = 7777

        class FakePort(object):
            def getHost(self):
                return IPv4Address('TCP', u'example.com', randomPort)

        ws = website.WebSite(store=self.store, hostname=u'example.com')
        port = SSLPort(store=self.store, portNumber=0, factory=ws)
        port.listeningPort = FakePort()
        self.assertEquals(
            flatten(ws.encryptedRoot()),
            'https://example.com:%s/' % (randomPort,))


    def test_encryptedRootPortZeroDisconnected(self):
        """
        If C{WebSite.securePortNumber} is 0 and the server is not listening
        then there is no valid URL. Check that L{WebSite.encryptedRoot}
        returns None.
        """
        ws = website.WebSite(store=self.store)
        port = SSLPort(store=self.store, portNumber=0, factory=ws)
        self.assertEquals(None, ws.encryptedRoot())


    def testMaybeEncryptedRoot(self):
        """
        If HTTPS service is available, L{WebSite.maybeEncryptedRoot} should
        return the same as L{WebSite.encryptedRoot}.
        """
        ws = website.WebSite(store=self.store, hostname=u'example.com')
        SSLPort(store=self.store, portNumber=443, factory=ws)
        self.assertEquals(ws.encryptedRoot(), ws.maybeEncryptedRoot())


    def testMaybeEncryptedRootUnavailable(self):
        """
        If HTTPS service is not available, L{WebSite.maybeEncryptedRoot} should
        return the same as L{WebSite.cleartextRoot}.
        """
        ws = website.WebSite(store=self.store, hostname=u'example.com')
        TCPPort(store=self.store, portNumber=80, factory=ws)
        self.assertEquals(ws.cleartextRoot(), ws.maybeEncryptedRoot())


    def testOnlySecureSignup(self):
        """
        Make sure the signup page is only displayed over HTTPS.
        """
        ws = website.WebSite(store=self.store)
        installOn(ws, self.store)
        port = TCPPort(store=self.store, portNumber=0, factory=ws)
        installOn(port, self.store)
        securePort = SSLPort(store=self.store, portNumber=0, certificatePath=self.certPath, factory=ws)
        installOn(securePort, self.store)

        self.store.parent = self.store #blech

        securePortNum = securePort.listeningPort.getHost().port

        sc = signup.SignupConfiguration(store=self.store)
        installOn(sc, self.store)
        sg = sc.createSignup(u"test", signup.UserInfoSignup,
                             {"prefixURL": u"signup"}, Product(store=self.store), u"", u"Test")
        signupPage = sg.createResource()
        fr = AccumulatingFakeRequest(uri='/signup', currentSegments=['signup'])
        result = renderPage(signupPage, reqFactory=lambda: fr)

        def rendered(ignored):
            self.assertEqual(fr.redirected_to, 'https://localhost:%s/signup' % (securePortNum,))
        result.addCallback(rendered)
        return result


    def testOnlySecureLogin(self):
        """
        Make sure the login page is only displayed over HTTPS.
        """
        ws = website.WebSite(store=self.store)
        installOn(ws, self.store)
        port = TCPPort(store=self.store, portNumber=0, factory=ws)
        installOn(port, self.store)
        securePort = SSLPort(store=self.store, portNumber=0, certificatePath=self.certPath, factory=ws)
        installOn(securePort, self.store)

        url, _ = ws.site.resource.locateChild(FakeRequest(), ["login"])
        self.assertEquals(url.scheme, "https")


    def testOnlyHTTPLogin(self):
        """
        If there's no secure port, work over HTTP anyway.
        """
        ws = website.WebSite(store=self.store)
        installOn(ws, self.store)
        port = TCPPort(store=self.store, portNumber=0, factory=ws)
        installOn(port, self.store)

        res, _ = ws.site.resource.locateChild(FakeRequest(), ["login"])
        self.failUnless(isinstance(res, LoginPage))


    def testOnlyHTTPSignup(self):
        """
        If there's no secure port, work over HTTP anyway.
        """
        ws = website.WebSite(store=self.store)
        installOn(ws, self.store)
        port = TCPPort(store=self.store, portNumber=0, factory=ws)
        installOn(port, self.store)

        portNum = port.listeningPort.getHost().port

        self.store.parent = self.store #blech

        sc = signup.SignupConfiguration(store=self.store)
        installOn(sc, self.store)
        sg = sc.createSignup(u"test", signup.UserInfoSignup,
                             {"prefixURL": u"signup"}, Product(store=self.store), u"", u"Test")
        signupPage = sg.createResource()
        fr = AccumulatingFakeRequest(uri='/signup', currentSegments=['signup'])
        result = renderLivePage(signupPage, reqFactory=lambda: fr)
        def rendered(ignored):
            #we should get some sort of a page
            self.assertEquals(fr.redirected_to, None)
            self.assertNotEquals(len(fr.accumulator), 0)
        result.addCallback(rendered)
        return result



class LoginPageTests(unittest.TestCase):
    """
    Tests for functionality related to login.
    """
    def setUp(self):
        """
        Create a L{Store}, L{WebSite} and necessary request-related objects to
        test L{LoginPage}.
        """
        self.store = Store()
        website.WebSite(store=self.store)
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

        page = StubLoginPage.fromRequest(self.store, request)
        self.assertTrue(isinstance(page, StubLoginPage))
        self.assertIdentical(page.store, self.store)
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
            page = LoginPage(self.store)
        finally:
            publicweb.IStaticShellContent = originalInterface
        self.assertEqual(len(adaptions), 1)
        self.assertIdentical(adaptions[0][0], self.store)
        self.assertIdentical(page.staticContent, result)


    def test_segments(self):
        """
        L{LoginPage.beforeRender} should fill the I{login-action} slot with an
        L{URL} which includes all the segments given to the L{LoginPage}.
        """
        segments = ('foo', 'bar')
        page = LoginPage(self.store, segments)
        page.beforeRender(self.context)
        loginAction = self.context.locateSlotData('login-action')
        expectedLocation = URL.fromContext(self.context)
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
        page = LoginPage(self.store, (), args)
        page.beforeRender(self.context)
        loginAction = self.context.locateSlotData('login-action')
        expectedLocation = URL.fromContext(self.context)
        expectedLocation = expectedLocation.child(LOGIN_AVATAR)
        expectedLocation = expectedLocation.add('foo', 'bar')
        self.assertEqual(loginAction, expectedLocation)


    def test_locateChildPreservesSegments(self):
        """
        L{LoginPage.locateChild} should create a new L{LoginPage} with segments
        extracted from the traversal context.
        """
        segments = ('foo', 'bar')
        page = LoginPage(self.store)
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
        page = LoginPage(self.store)
        child, remaining = page.locateChild(self.context, None)
        self.assertTrue(isinstance(child, LoginPage))
        self.assertEqual(child.arguments, self.request.args)



class UnguardedWrapperTests(unittest.TestCase):
    """
    Tests for L{UnguardedWrapper}.
    """
    def test_secureLoginRequest(self):
        """
        When queried over HTTPS, L{UnguardedWrapper.locateChild} should consume
        the leading C{'login'} segment of a request and return a L{LoginPage}
        and the remaining segments.
        """
        request = FakeRequest(
            uri='/login/foo',
            currentSegments=[],
            isSecure=True)
        store = object()
        wrapper = website.UnguardedWrapper(store, None)
        child, segments = wrapper.locateChild(request, ('login', 'foo'))
        self.assertTrue(isinstance(child, LoginPage))
        self.assertIdentical(child.store, store)
        self.assertEqual(child.segments, ())
        self.assertEqual(child.arguments, {})
        self.assertEqual(segments, ('foo',))


    def test_insecureLoginRequest(self):
        """
        When queried for I{login} over HTTP, L{UnguardedWrapper.locateChild}
        should respond with a redirect to a location which differs on in its
        use of HTTPS instead of HTTP.
        """
        host = 'example.org'
        port = 1234

        request = FakeRequest(
            headers={'host': '%s:%d' % (host, port)},
            uri='/login/foo',
            currentSegments=[],
            isSecure=False)

        class FakeStore(object):
            implements(IResource)
            class securePort(object):
                def getHost():
                    return IPv4Address('TCP', '127.0.0.1', port, 'INET')
                getHost = staticmethod(getHost)

        store = FakeStore()
        wrapper = website.UnguardedWrapper(store, None)
        child, segments = wrapper.locateChild(request, ('login', 'foo'))
        self.assertTrue(isinstance(child, URL))

        self.assertEqual(
            str(child),
            str(URL('https', 'example.org:%d' % (port,), ['login', 'foo'])))
        self.assertEqual(segments, ())



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


    def test_jsmodules(self):
        """
        Test that the C{__jsmodule__} child of the site's root is an object which
        will serve up JavaScript modules for Athena applications.
        """
        topResource = SiteRootMixin()
        # Don't even need to provide a store - this data is retrieved from
        # code, not the database, and it _should never_ touch the database on
        # the way to getting it.
        resource, segments = topResource.locateChild(None, ('__jsmodule__',))
        self.failUnless(isinstance(resource, HashedJSModuleProvider))
        self.assertEquals(segments, ())


    def test_live(self):
        """
        Test that the C{live} child of the site's root is a L{LivePage}
        object.
        """
        topResource = SiteRootMixin()
        (resource, segments) = topResource.locateChild(None, ('live',))
        self.failUnless(isinstance(resource, LivePage))
        self.assertEqual(segments, ())


    def test_liveNoHitCount(self):
        """
        Test that accessing the C{live} child of the site's root does not
        increment the C{hitCount} attribute.
        """
        topResource = SiteRootMixin()
        topResource.locateChild(None, ('live',))
        self.assertEqual(topResource.hitCount, 0)


    def test_hitsCountedByDefault(self):
        """
        Test that children of the site's root will contribute to the hit count
        if they don't explicitly state otherwise.
        """
        topResource = SiteRootMixin()
        topResource.child_x = lambda *a: (None, ())
        topResource.locateChild(None, ('x',))
        self.assertEqual(topResource.hitCount, 1)


    def test_hitsCountedifTrue(self):
        """
        Test that children of the site's root will contribute to the hit count
        if they express an interest in doing that.
        """
        topResource = SiteRootMixin()
        topResource.child_x = lambda *a: (None, ())
        topResource.child_x.countHits = True
        topResource.locateChild(None, ('x',))
        self.assertEqual(topResource.hitCount, 1)


    def test_hitsNotCountedIfFalse(self):
        """
        Test that children of the site's root won't contribute to the hit
        count if they ask not to.
        """
        topResource = SiteRootMixin()
        topResource.child_x = lambda *a: (None, ())
        topResource.child_x.countHits = False
        topResource.locateChild(None, ('x',))
        self.assertEqual(topResource.hitCount, 0)


    def test_transportRoot(self):
        """
        The transport root should always point at the '/live' transport root
        provided to avoid database interaction while invoking the transport.
        """
        livePage = self.makeLivePage()
        self.assertEquals(flatten(livePage.transportRoot), 'http://localhost/live')


    def makeLivePage(self):
        """
        Create a MantissaLivePage instance for testing.
        """
        store = Store()
        webSite = WebSite(store=store, hostname=self.hostname.decode('ascii'))
        installOn(webSite, store)
        SSLPort(store=store, factory=webSite, portNumber=TEST_SECURE_PORT)
        return MantissaLivePage(webSite)


    def test_debuggableMantissaLivePage(self):
        """
        L{MantissaLivePage.getJSModuleURL}'s depends on state from page
        rendering, but it should provide a helpful error message in the case
        where that state has not yet been set up.
        """
        livePage = self.makeLivePage()
        self.assertRaises(NotImplementedError, livePage.getJSModuleURL, 'Mantissa')


    def test_mantissaLivePageMixin(self):
        """
        All athena LivePages in Mantissa or Mantissa applications should inherit
        from MantissaLivePage.  Those pages should all share a getJSModuleURL
        implementation which provides a URL including 3 segments::
            https://<hostname>:<ssl port>/__jsmodule__/
                <SHA1 digest of module contents>/Package.ModuleName
        """
        livePage = self.makeLivePage()
        self._preRender(livePage)
        jsurl = livePage.getJSModuleURL('Mantissa')
        self.assertEqual(jsurl.scheme, 'https')
        self.assertEqual(jsurl.netloc,
                         self.hostname + ':' + str(TEST_SECURE_PORT))
        segments = jsurl.pathList()
        self.assertEqual(segments[0], '__jsmodule__')
        expect = sha.new(
            FilePath(__file__).parent().parent()
            .child("js").child("Mantissa").child("__init__.js")
            .open().read()).hexdigest()
        self.assertEqual(segments[1], expect)
        self.assertEqual(segments[2], "Mantissa")
