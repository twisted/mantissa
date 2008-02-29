
"""
Test for upgrading a WebSite to move its TCP and SSL information onto separate
objects.
"""

from twisted.application.service import IService

from axiom.test.historic.stubloader import StubbedTest
from axiom.dependency import installedOn
from axiom.userbase import LoginSystem

from xmantissa.port import TCPPort, SSLPort
from xmantissa.web import SiteConfiguration
from xmantissa.website import WebSite

from xmantissa.test.historic.stub_website4to5 import cert

class WebSiteUpgradeTests(StubbedTest):
    def test_preservedAttributes(self):
        """
        Test that some data from the simple parts of the schema is preserved.
        """
        web = self.store.findUnique(WebSite)
        self.assertEqual(web.hitCount, 123)

        site = self.store.findUnique(SiteConfiguration)
        self.assertEqual(site.httpLog, self.store.filesdir.child('httpd.log'))
        self.assertEqual(site.hostname, u'example.net')


    def test_portNumber(self):
        """
        Test that the WebSite's portNumber attribute is transformed into a
        TCPPort instance.
        """
        site = self.store.findUnique(SiteConfiguration)
        ports = list(self.store.query(TCPPort, TCPPort.factory == site))
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0].portNumber, 8088)
        self.assertEqual(installedOn(ports[0]), self.store)
        self.assertEqual(list(self.store.interfacesFor(ports[0])), [IService])


    def test_securePortNumber(self):
        """
        Test that the WebSite's securePortNumber attribute is transformed into
        an SSLPort instance.
        """
        site = self.store.findUnique(SiteConfiguration)
        ports = list(self.store.query(SSLPort, SSLPort.factory == site))
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0].portNumber, 6443)
        certPath = self.store.newFilePath('server.pem')
        self.assertEqual(ports[0].certificatePath, certPath)
        self.assertEqual(certPath.getContent(), cert)
        self.assertEqual(installedOn(ports[0]), self.store)
        self.assertEqual(list(self.store.interfacesFor(ports[0])), [IService])


    def test_poweredDown(self):
        """
        Test that the WebSite is no longer an IService powerup for the store.
        """
        site = self.store.findUnique(WebSite)
        powerups = self.store.powerupsFor(IService)
        self.failIfIn(site, list(powerups))


    def test_userStore(self):
        """
        Test that WebSites in user stores upgrade without errors.
        """
        ls = self.store.findUnique(LoginSystem)
        substore = ls.accountByAddress(u'testuser', u'localhost').avatars.open()
        self.failUnless(substore.getItemByID(3).__class__ is WebSite)


    def tearDown(self):
        d = StubbedTest.tearDown(self)
        def flushit(ign):
            from epsilon.cooperator import SchedulerStopped
            self.flushLoggedErrors(SchedulerStopped)
            return ign
        return d.addCallback(flushit)

