
"""
Tests for xmantissa.offering.
"""

from zope.interface import Interface

from twisted.trial import unittest

from axiom import store, item, attributes, userbase

from axiom.plugins.mantissacmd import Mantissa

from axiom.dependency import installedOn

from xmantissa import ixmantissa, offering

from xmantissa.plugins.baseoff import baseOffering
from xmantissa.plugins.offerings import peopleOffering


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


class OfferingPluginTest(unittest.TestCase):
    """
    A simple test for getOffering.
    """

    def test_getOfferings(self):
        """
        getOffering should use the Twisted plugin system to load the plugins
        provided with Mantissa.  Since this is dynamic, we can't assert
        anything about the complete list, but we can at least verify that all
        the plugins that should be there, are.
        """
        foundOfferings = list(offering.getOfferings())
        allExpectedOfferings = [baseOffering, peopleOffering]
        for expected in allExpectedOfferings:
            self.assertIn(expected, foundOfferings)


class OfferingTest(unittest.TestCase):
    def setUp(self):
        self.store = store.Store(filesdir=self.mktemp())
        Mantissa().installSite(self.store, "/", generateCert=False)
        Mantissa().installAdmin(self.store, u'admin@localhost', u'asdf')
        self.userbase = self.store.findUnique(userbase.LoginSystem)
        self.adminAccount = self.userbase.accountByAddress(u'admin', u'localhost')
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
        self.offering = off
        # Add this somewhere that the plugin system is going to see it.
        self._originalGetOfferings = offering.getOfferings
        offering.getOfferings = self.fakeGetOfferings


    def fakeGetOfferings(self):
        """
        Return standard list of offerings, plus one extra.
        """
        return list(self._originalGetOfferings()) + [self.offering]


    def tearDown(self):
        """
        Remove the temporary offering.
        """
        offering.getOfferings = self._originalGetOfferings


    def test_installOffering(self):
        """
        L{OfferingConfiguration.installOffering} should install the given
        offering on the Mantissa server.
        """
        conf = self.adminAccount.avatars.open().findUnique(
            offering.OfferingConfiguration)
        conf.installOffering(self.offering, None)

        # Site store requirements should be on the site store
        tsr = self.store.findUnique(TestSiteRequirement)
        self.failUnless(installedOn(tsr), self.store)

        # App store should have been created
        appStore = self.userbase.accountByAddress(self.offering.name, None)
        self.assertNotEqual(appStore, None)

        # App store requirements should be on the app store
        ss = appStore.avatars.open()
        tap = ss.findUnique(TestAppPowerup)
        self.failUnless(installedOn(tap), ss)

        self.assertRaises(offering.OfferingAlreadyInstalled,
                          conf.installOffering, self.offering, None)


    def test_getInstalledOfferingNames(self):
        """
        L{getInstalledOfferingNames} should list the names of offerings
        installed on the given site store.
        """
        self.assertEquals(offering.getInstalledOfferingNames(self.store),
                          ['mantissa-base'])

        self.test_installOffering()

        self.assertEquals(
            offering.getInstalledOfferingNames(self.store),
            [u"mantissa-base", u"test_offering"])


    def test_getInstalledOfferings(self):
        """
        getInstalledOfferings should return a mapping of offering name to
        L{Offering} object for each installed offering on a given site store.
        """
        self.assertEquals(offering.getInstalledOfferings(self.store),
                          {baseOffering.name: baseOffering})
        self.test_installOffering()
        self.assertEquals(offering.getInstalledOfferings(self.store),
                          {baseOffering.name: baseOffering,
                           self.offering.name: self.offering})
