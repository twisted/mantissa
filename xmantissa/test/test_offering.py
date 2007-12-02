
from zope.interface import Interface

from twisted.trial import unittest

from axiom import store, item, attributes, userbase

from axiom.plugins.mantissacmd import Mantissa

from axiom.dependency import installedOn

from xmantissa import ixmantissa, offering


class TestSiteRequirement(item.Item):
    typeName = 'test_site_requirement'
    schemaVersion = 1

    attr = attributes.integer()

class TestAppPowerup(item.Item):
    typeName = 'test_app_powerup'
    schemaVersion = 1

    attr = attributes.integer()


class TestPublicPagePowerup(item.Item):
    typeName = 'test_publicpage_powerup'
    schemaVersion = 1
    powerupInterfaces = ixmantissa.IPublicPage

    attr = attributes.integer()

class ITestInterface(Interface):
    """
    An interface to which no object can be adapted.  Used to ensure failed
    adaption causes a powerup to be installed.
    """

class OfferingTest(unittest.TestCase):
    def setUp(self):
        self.store = store.Store(filesdir=self.mktemp())
        Mantissa().installSite(self.store, "/", generateCert=False)
        Mantissa().installAdmin(self.store, u'admin@localhost', u'asdf')
        self.userbase = self.store.findUnique(userbase.LoginSystem)
        self.adminAccount = self.userbase.accountByAddress(u'admin', u'localhost')


    def testInstallation(self):
        conf = self.adminAccount.avatars.open().findUnique(offering.OfferingConfiguration)
        off = offering.Offering(
            name=u'test_offering',
            description=u'This is an offering which tests the offering '
                         'installation mechanism',
            siteRequirements=[(ITestInterface, TestSiteRequirement)],
            appPowerups=[TestAppPowerup],
            installablePowerups=[],
            loginInterfaces=[],
            themes=[],
            )
        conf.installOffering(off, None)

        # Site store requirements should be on the site store
        tsr = self.store.findUnique(TestSiteRequirement)
        self.failUnless(installedOn(tsr), self.store)

        # App store should have been created
        appStore = self.userbase.accountByAddress(off.name, None)
        self.assertNotEqual(appStore, None)

        # App store requirements should be on the app store
        ss = appStore.avatars.open()
        tap = ss.findUnique(TestAppPowerup)
        self.failUnless(installedOn(tap), ss)


    def testGetInstalledOfferingNames(self):
        self.assertEquals(offering.getInstalledOfferingNames(self.store), ['mantissa-base'])

        self.testInstallation()

        self.assertEquals(
            offering.getInstalledOfferingNames(self.store),
            [u"mantissa-base", u"test_offering"])
