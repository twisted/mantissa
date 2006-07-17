
from twisted.trial import unittest
from twisted.application import service
from twisted.web import http

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
