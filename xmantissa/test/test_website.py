
import socket

from twisted.trial import unittest
from twisted.application import service
from twisted.web import http

from nevow.flat import flatten
from nevow.testutil import AccumulatingFakeRequest, renderPage
from nevow.testutil import renderLivePage, FakeRequest
from epsilon.scripts import certcreate

from axiom import store, userbase
from axiom.dependency import installOn

from xmantissa import website, signup
from xmantissa.product import Product

class WebSiteTestCase(unittest.TestCase):
    def setUpClass(self):
        self.origFunction = http._logDateTimeStart
        http._logDateTimeStart = lambda: None
        self.certfile = self.mktemp()
        certcreate.main(['--filename', self.certfile, '--quiet'])

    def tearDownClass(self):
        http._logDateTimeStart = self.origFunction
        del self.origFunction

    def setUp(self):
        self.store = store.Store()
        self.login = userbase.LoginSystem(store=self.store)
        installOn(self.login, self.store)

        svc = service.IService(self.store)
        svc.privilegedStartService()
        svc.startService()

    def tearDown(self):
        svc = service.IService(self.store)
        return svc.stopService()


    def test_cleartextRoot(self):
        """
        Test that the L{WebSite.cleartextRoot} method returns the proper URL
        for HTTP communication with this site.
        """
        ws = website.WebSite(store=self.store,
                             hostname=u'example.com',
                             portNumber=80)
        self.assertEquals(
            flatten(ws.cleartextRoot()),
            'http://example.com/')


    def test_cleartextRootNonstandardPort(self):
        """
        Test that the L{WebSite.cleartextRoot} method returns the proper URL
        for HTTP communication with this site even if the server is listening
        on a funky port number.
        """
        ws = website.WebSite(store=self.store,
                             hostname=u'example.com',
                             portNumber=8000)
        self.assertEquals(
            flatten(ws.cleartextRoot()),
            'http://example.com:8000/')


    def test_cleartextRootUnavailable(self):
        """
        Test that the L{WebSite.cleartextRoot} method returns None if there is
        no HTTP server listening.
        """
        ws = website.WebSite(store=self.store, portNumber=None)
        self.assertEquals(ws.cleartextRoot(), None)


    def test_cleartextRootWithoutHostname(self):
        """
        Test that the L{WebSite.cleartextRoot} method returns a best-guess URL
        if there is no hostname available.
        """
        ws = website.WebSite(store=self.store,
                             portNumber=8000)
        self.assertEquals(
            flatten(ws.cleartextRoot()),
            'http://%s:8000/' % (socket.getfqdn(),))


    def test_cleartextRootHostOverride(self):
        """
        Test that if a hostname is explicitly passed to
        L{WebSite.cleartextRoot}, it overrides the configured hostname in the
        result.
        """
        ws = website.WebSite(store=self.store,
                             portNumber=80,
                             hostname=u'example.com')
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
                from twisted.internet import address
                return address.IPv4Address('TCP', u'example.com', randomPort)

        ws = website.WebSite(store=self.store,
                             portNumber=0, hostname=u'example.com')
        ws.port = FakePort()
        self.assertEquals(flatten(ws.cleartextRoot()),
                          'http://example.com:%s/' % (randomPort,))


    def test_cleartextRootPortZeroDisconnected(self):
        """
        If C{WebSite.securePortNumber} is 0 and the server is not listening
        then there is no valid URL. Check that L{WebSite.cleartextRoot}
        returns None.
        """
        ws = website.WebSite(store=self.store, portNumber=0)
        self.assertEquals(None, ws.cleartextRoot())


    def test_encryptedRoot(self):
        """
        Test that the L{WebSite.encryptedRoot} method returns the proper URL
        for HTTPS communication with this site.
        """
        ws = website.WebSite(store=self.store,
                             hostname=u'example.com',
                             securePortNumber=443)
        self.assertEquals(
            flatten(ws.encryptedRoot()),
            'https://example.com/')


    def test_encryptedRootNonstandardPort(self):
        """
        Test that the L{WebSite.encryptedRoot} method returns the proper URL
        for HTTPS communication with this site even if the server is listening
        on a funky port number.
        """
        ws = website.WebSite(store=self.store,
                             hostname=u'example.com',
                             securePortNumber=8443)
        self.assertEquals(
            flatten(ws.encryptedRoot()),
            'https://example.com:8443/')


    def test_encryptedRootUnavailable(self):
        """
        Test that the L{WebSite.encryptedRoot} method returns None if there is
        no HTTP server listening.
        """
        ws = website.WebSite(store=self.store, securePortNumber=None)
        self.assertEquals(ws.encryptedRoot(), None)


    def test_encryptedRootWithoutHostname(self):
        """
        Test that the L{WebSite.encryptedRoot} method returns a non-universal
        URL if there is no hostname available.
        """
        ws = website.WebSite(store=self.store,
                             securePortNumber=8443)
        self.assertEquals(
            flatten(ws.encryptedRoot()),
            'https://%s:8443/' % (socket.getfqdn(),))


    def test_encryptedRootHostOverride(self):
        """
        Test that if a hostname is explicitly passed to
        L{WebSite.encryptedRoot}, it overrides the configured hostname in the
        result.
        """
        ws = website.WebSite(store=self.store,
                             securePortNumber=443,
                             hostname=u'example.com')
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
                from twisted.internet import address
                return address.IPv4Address('TCP', u'example.com', randomPort)

        ws = website.WebSite(store=self.store,
                             securePortNumber=0, hostname=u'example.com')
        ws.securePort = FakePort()
        self.assertEquals(
            flatten(ws.encryptedRoot()),
            'https://example.com:%s/' % (randomPort,))


    def test_encryptedRootPortZeroDisconnected(self):
        """
        If C{WebSite.securePortNumber} is 0 and the server is not listening
        then there is no valid URL. Check that L{WebSite.encryptedRoot}
        returns None.
        """
        ws = website.WebSite(store=self.store, securePortNumber=0)
        self.assertEquals(None, ws.encryptedRoot())


    def testMaybeEncryptedRoot(self):
        """
        If HTTPS service is available, L{WebSite.maybeEncryptedRoot} should
        return the same as L{WebSite.encryptedRoot}.
        """
        ws = website.WebSite(store=self.store,
                             hostname=u'example.com',
                             securePortNumber=443)

        self.assertEquals(ws.encryptedRoot(), ws.maybeEncryptedRoot())


    def testMaybeEncryptedRootUnavailable(self):
        """
        If HTTPS service is not available, L{WebSite.maybeEncryptedRoot} should
        return the same as L{WebSite.cleartextRoot}.
        """
        ws = website.WebSite(store=self.store,
                             hostname=u'example.com',
                             portNumber=80)

        self.assertEquals(ws.cleartextRoot(), ws.maybeEncryptedRoot())


    def testLateInstallation(self):
        ws = website.WebSite(store=self.store)
        installOn(ws, self.store)

        self.failUnless(ws.running)

    def testHTTP(self):
        ws = website.WebSite(store=self.store)
        installOn(ws, self.store)

        self.failIfEqual(ws.port, None)
        self.assertEqual(ws.securePort, None)

    def testHTTPS(self):
        ws = website.WebSite(store=self.store,
                             portNumber=None,
                             securePortNumber=0,
                             certificateFile=self.certfile)
        installOn(ws, self.store)

        self.assertEqual(ws.port, None)
        self.failIfEqual(ws.securePort, None)

    def testOnlySecureSignup(self):
        """
        Make sure the signup page is only displayed over HTTPS.
        """
        ws = website.WebSite(store=self.store,
                             portNumber=0,
                             securePortNumber=0,
                             certificateFile=self.certfile)
        installOn(ws, self.store)

        self.store.parent = self.store #blech

        securePortNum = ws.securePort.getHost().port

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
        ws = website.WebSite(store=self.store,
                             portNumber=0,
                             securePortNumber=0,
                             certificateFile=self.certfile)
        installOn(ws, self.store)

        url, _ = ws.site.resource.locateChild(FakeRequest(), ["login"])
        self.assertEquals(url.scheme, "https")


    def testOnlyHTTPLogin(self):
        """
        If there's no secure port, work over HTTP anyway.
        """
        ws = website.WebSite(store=self.store,
                             portNumber=0)
        installOn(ws, self.store)

        res, _ = ws.site.resource.locateChild(FakeRequest(), ["login"])
        self.failUnless(isinstance(res, website.LoginPage))

    def testOnlyHTTPSignup(self):
        """
        If there's no secure port, work over HTTP anyway.
        """
        ws = website.WebSite(store=self.store,
                             portNumber=0)
        installOn(ws, self.store)
        portNum = ws.port.getHost().port

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
