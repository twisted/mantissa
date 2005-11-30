
from zope.interface import Interface

from twisted.trial import unittest

from axiom import store, item, attributes, userbase
from axiom.scripts import axiomatic

from xmantissa import ixmantissa, offering

class TestSiteRequirement(item.Item):
    typeName = 'test_site_requirement'
    schemaVersion = 1

    installed = attributes.integer(default=0)

    def installOn(self, other):
        self.installed = True

class TestAppPowerup(item.Item):
    typeName = 'test_app_powerup'
    schemaVersion = 1

    installed = attributes.integer(default=0)

    def installOn(self, other):
        self.installed = True

class TestPublicPagePowerup(item.Item):
    typeName = 'test_publicpage_powerup'
    schemaVersion = 1

    def installOn(self, other):
        other.powerUp(self, ixmantissa.IPublicPage)

class ITestInterface(Interface):
    """
    An interface to which no object can be adapted.  Used to ensure failed
    adaption causes a powerup to be installed.
    """

class OfferingTest(unittest.TestCase):
    def setUp(self):
        self.dbpath = self.mktemp()
        axiomatic.main(['-d', self.dbpath, 'mantissa', '--admin-password', 'password'])
        self.store = store.Store(self.dbpath)
        self.userbase = self.store.findUnique(userbase.LoginSystem)
        self.adminAccount = self.userbase.accountByAddress(u'admin', u'localhost')

    def testInstallation(self):
        conf = self.adminAccount.avatars.open().findUnique(offering.OfferingConfiguration)
        off = offering.Offering(
            u'test_offering',
            u'This is an offering which tests the offering installation mechanism',
            [(ITestInterface, TestSiteRequirement)],
            [TestAppPowerup],
            []
            )
        conf.installOffering(off, None)

        # Site store requirements should be on the site store
        tsr = self.store.findUnique(TestSiteRequirement)
        self.failUnless(tsr.installed)

        # App store should have been created
        appStore = self.userbase.accountByAddress(off.name, None)
        self.assertNotEqual(appStore, None)

        # App store requirements should be on the app store
        tap = appStore.avatars.open().findUnique(TestAppPowerup)
        self.failUnless(tap.installed)
