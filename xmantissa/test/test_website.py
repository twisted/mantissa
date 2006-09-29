
import socket

from twisted.trial import unittest
from twisted.application import service
from twisted.web import http

from nevow.flat import flatten

from epsilon.scripts import certcreate

from axiom import store, userbase

from xmantissa import website

class WebSiteTestCase(unittest.TestCase):
    def setUpClass(self):
        self.origFunction = http._logDateTimeStart
        http._logDateTimeStart = lambda: None

    def tearDownClass(self):
        http._logDateTimeStart = self.origFunction
        del self.origFunction

    def setUp(self):
        self.store = store.Store()
        self.login = userbase.LoginSystem(store=self.store)
        self.login.installOn(self.store)

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
        ws = website.WebSite(store=self.store)
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
        ws = website.WebSite(store=self.store)
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


    def testLateInstallation(self):
        ws = website.WebSite(store=self.store)
        ws.installOn(self.store)

        self.failUnless(ws.running)

    def testHTTP(self):
        ws = website.WebSite(store=self.store)
        ws.installOn(self.store)

        self.failIfEqual(ws.port, None)
        self.assertEqual(ws.securePort, None)

    def testHTTPS(self):
        certfile = self.mktemp()
        certcreate.main(['--filename', certfile])

        ws = website.WebSite(store=self.store,
                             portNumber=None,
                             securePortNumber=0,
                             certificateFile=certfile)
        ws.installOn(self.store)

        self.assertEqual(ws.port, None)
        self.failIfEqual(ws.securePort, None)
