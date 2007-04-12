
import socket

from twisted.internet.address import IPv4Address
from twisted.trial import unittest
from twisted.application import service
from twisted.web import http
from twisted.python.filepath import FilePath
from twisted.python.reflect import qual

from nevow.flat import flatten
from nevow.testutil import AccumulatingFakeRequest, renderPage
from nevow.testutil import renderLivePage, FakeRequest
from epsilon.scripts import certcreate

from axiom import userbase
from axiom.store import Store
from axiom.dependency import installOn
from axiom.test.util import getPristineStore

from xmantissa.port import TCPPort, SSLPort
from xmantissa import website, signup, publicweb, people
from xmantissa.product import Product



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
                             {"prefixURL": u"signup"},
                             Product(store=self.store, types=[qual(people.Organizer)]),
                             u"", u"Test")
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
        self.failUnless(isinstance(res, publicweb.LoginPage))


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
                             {"prefixURL": u"signup"},
                             Product(store=self.store, types=[qual(people.Organizer)]),
                             u"", u"Test")
        signupPage = sg.createResource()
        fr = AccumulatingFakeRequest(uri='/signup', currentSegments=['signup'])
        result = renderLivePage(signupPage, reqFactory=lambda: fr)
        def rendered(ignored):
            #we should get some sort of a page
            self.assertEquals(fr.redirected_to, None)
            self.assertNotEquals(len(fr.accumulator), 0)
        result.addCallback(rendered)
        return result
