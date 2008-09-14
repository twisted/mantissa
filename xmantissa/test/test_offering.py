"""
Tests for xmantissa.offering.
"""

import warnings

from zope.interface import Interface, implements, classProvides
from zope.interface.interfaces import IInterface
from zope.interface.verify import verifyClass, verifyObject

from twisted.trial import unittest

from axiom.store import Store
from axiom.substore import SubStore
from axiom import item, attributes, userbase

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



class ITestInterface(Interface):
    """
    An interface to which no object can be adapted.  Used to ensure failed
    adaption causes a powerup to be installed.
    """



class FakeNewStyleOffering(item.Item):
    """
    An offering used by the tests for the offering system which is defined in
    the preferred way, as an L{Item} subclass instead of as an L{Offering}
    instance.
    """
    powerupInterfaces = (ixmantissa.IOffering,)
    classProvides(*powerupInterfaces)

    name = u"Fake New Style Offering"
    description = None

    siteRequirements = [(None, TestSiteRequirement)]
    appPowerups = [TestAppPowerup]

    installablePowerups = None
    loginInterfaces = None
    themes = None
    staticContentPath = None
    version = None

    application = attributes.reference(
        reftype=SubStore,
        doc="A reference to the Application SubStore for this offering.")



class NewStyleOfferingTestsMixin:
    """
    A TestCase mixin defining tests which all new-style L{IOffering} providers
    are required to pass in order to function properly when installed on a
    Mantissa instance.
    """
    def getOffering(self):
        raise NotImplemented(
            "%r did not implement getOffering" % (self.__class__,))


    def test_interface(self):
        """
        Offerings must provide L{IOffering}.
        """
        self.assertTrue(verifyObject(ixmantissa.IOffering, self.getOffering()))


    def test_powerup(self):
        """
        An instance of the offering is a powerup for L{IOffering}.
        """
        store = Store()
        offering = self.getOffering()(store=store)
        store.powerUp(offering)
        self.assertEqual(
            list(store.powerupsFor(ixmantissa.IOffering)), [offering])


    def test_siteRequirements(self):
        """
        The C{siteRequirements} attribute of an offering is a list of
        two-tuples (or any other type which is iterable containing iterables of
        length two) where the first element of the tuple is C{None} or an
        interface and the second element is an L{Item} subclass.
        """
        for (iface, powerup) in self.getOffering().siteRequirements:
            self.assertTrue(iface is None or IInterface.providedBy(iface))
            self.assertTrue(issubclass(powerup, item.Item))


    def test_appPowerups(self):
        """
        The C{appPowerups} attribute of an offering is a list (or any other
        type which is iterable) of L{Item} subclasses.
        """
        for powerup in self.getOffering().appPowerups:
            self.assertTrue(issubclass(powerup, item.Item))


    def test_name(self):
        """
        The C{name} attribute of an offering is a C{unicode} instance.
        """
        self.assertIsInstance(self.getOffering().name, unicode)


    def test_application(self):
        """
        An L{Item} subclass L{IOffering} powerup must accept a C{application}
        keyword argument to its initializer and have a C{application} Axiom
        C{reference} attribute which is set to the L{SubStore} passed for that
        parameter.
        """
        store = Store()
        substore = SubStore.createNew(store, ['foo', 'bar'])
        offering = self.getOffering()(store=store, application=substore)
        self.assertIdentical(offering.application, substore)



class FakeNewStyleOfferingTests(NewStyleOfferingTestsMixin, unittest.TestCase):
    """
    L{IOffering}-conformance tests for L{FakeNewStyleOffering}.
    """
    def getOffering(self):
        return FakeNewStyleOffering



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
        self.store = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.store, u"localhost", u"", False)
        Mantissa().installAdmin(self.store, u'admin', u'localhost', u'asdf')
        self.userbase = self.store.findUnique(userbase.LoginSystem)
        self.adminAccount = self.userbase.accountByAddress(
            u'admin', u'localhost')
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

        self.conf = self.adminAccount.avatars.open().findUnique(
            offering.OfferingConfiguration)

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


    def _installOfferingTest(self, installedOffering, theOffering):

        # The application attribute should be set to the SubStore created for
        # the application.
        self.assertIsInstance(installedOffering.application, SubStore)

        # Site store requirements should be on the site store
        tsr = self.store.findUnique(TestSiteRequirement)
        self.failUnless(installedOn(tsr), self.store)

        # App store should have been created
        appStore = self.userbase.accountByAddress(theOffering.name, None)
        self.assertNotEqual(appStore, None)

        # App store requirements should be on the app store
        ss = appStore.avatars.open()
        tap = ss.findUnique(TestAppPowerup)
        self.failUnless(installedOn(tap), ss)

        self.assertRaises(offering.OfferingAlreadyInstalled,
                          self.conf.installOffering, theOffering, None)


    def test_installOffering(self):
        """
        If L{OfferingConfiguration.installOffering} is passed an L{Offering}
        instance, an L{InstalledOffering} corresponding to that L{Offering} is
        created and the C{siteRequirements} and C{appPowerups} defined by the
        L{Offering} are installed on the site and app stores, respectively.  If
        L{OfferingConfiguration.installOffering} is passed an L{Offering} with
        a name for which there is already an L{InstalledOffering},
        L{Offeringalreadyinstalled} is raised.
        """
        io = self.conf.installOffering(self.offering, None)

        # InstalledOffering should be returned, and installed on the site store
        foundIO = self.store.findUnique(offering.InstalledOffering,
                  offering.InstalledOffering.offeringName == self.offering.name)
        self.assertIdentical(io, foundIO)

        self._installOfferingTest(io, self.offering)


    def test_installNewStyleOffering(self):
        """
        If L{OfferingConfiguration.installOffering} is passed an L{IOffering}
        provider which is an L{Item} subclass, an instance of that type is
        created in the site store and the site store is powered up for
        L{IOffering} with it.  The C{siteRequirements} it indicates are
        installed on the site store and the C{appRequirements} it indicates are
        installed on the app store.
        """
        result = self.conf.installOffering(FakeNewStyleOffering, None)

        self.assertIsInstance(result, FakeNewStyleOffering)
        self.assertIn(
            result, list(self.store.powerupsFor(ixmantissa.IOffering)))

        self._installOfferingTest(result, FakeNewStyleOffering)


    def test_deprecatedOldStyleInstallOffering(self):
        """
        L{OfferingAdapter.installOffering} emits a L{DeprecationWarning} if it
        is passed a non-L{Item} L{IOffering} provider.
        """
        self.assertWarns(
            DeprecationWarning,
            "Old-style offering %r should be updated to be an Item." % (
                self.offering.name,),
            warnings.__file__,
            lambda: self.conf.installOffering(self.offering, None))


    def test_getInstalledOfferingNames(self):
        """
        L{getInstalledOfferingNames} should list the names of offerings
        installed on the given site store.
        """
        self.assertEquals(offering.getInstalledOfferingNames(self.store),
                          ['mantissa-base'])

        self.test_installOffering()

        installed = offering.getInstalledOfferingNames(self.store)
        installed.sort()
        expected = [u"mantissa-base", u"test_offering"]
        expected.sort()
        self.assertEquals(installed, expected)


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


    def test_notAppStore(self):
        """
        L{isAppStore} returns C{False} for a Store which was not created as an
        I{app store} for an L{Offering} or a new-style offering.
        """
        self.assertFalse(offering.isAppStore(self.store))
        self.assertFalse(offering.isAppStore(self.adminAccount.avatars.open()))


    def _isAppStoreTest(self, theOffering):
        self.conf.installOffering(theOffering, None)
        app = self.userbase.accountByAddress(theOffering.name, None)
        self.assertTrue(offering.isAppStore(app.avatars.open()))


    def test_isAppStore(self):
        """
        L{isAppStore} returns C{True} for a Store which was created as an I{app
        stores} for an L{Offering}.
        """
        self._isAppStoreTest(self.offering)


    def test_isAppStoreNewStyle(self):
        """
        L{isAppStore} returns C{True} for a Store which was created as an I{app
        stores} for a new-style offering.
        """
        self._isAppStoreTest(FakeNewStyleOffering)



class FakeOfferingTechnician(object):
    """
    In-memory only implementation of the offering inspection/installation API.

    @ivar installedOfferings: A mapping from offering names to corresponding
        L{IOffering} providers which have been passed to C{installOffering}.

    @ivar store: A L{Store} on which new-style offerings will be installed, or
        C{None} to install them no-where.
    """
    implements(ixmantissa.IOfferingTechnician)

    def __init__(self, store=None):
        self.store = store
        self.installedOfferings = {}


    def installOffering(self, offering):
        """
        Add the given L{IOffering} provider to the list of installed offerings.
        """
        if isinstance(offering, item.MetaItem):
            offering = offering(store=self.store)
        self.installedOfferings[offering.name] = offering


    def getInstalledOfferings(self):
        """
        Return a copy of the internal installed offerings mapping.
        """
        return self.installedOfferings.copy()


    def getInstalledOfferingNames(self):
        """
        Return the names from the internal installed offerings mapping.
        """
        return self.installedOfferings.keys()



class OfferingTechnicianTestMixin:
    """
    L{unittest.TestCase} mixin which defines unit tests for classes which
    implement L{IOfferingTechnician}.

    @ivar offerings: A C{list} of L{Offering} instances which will be installed
        by the tests this mixin defines.
    """
    offeringPlugins = [
        offering.Offering(u'an offering', None, [], [], [], [], []),
        offering.Offering(u'another offering', None, [], [], [], [], [])]

    offeringPowerups = [FakeNewStyleOffering]

    def createTechnician(self, store):
        """
        @return: An L{IOfferingTechnician} provider which will be tested.
        """
        raise NotImplementedError(
            "%r did not implement createTechnician" % (self.__class__,))


    def test_interface(self):
        """
        L{createTechnician} returns an instance of a type which declares that
        it implements L{IOfferingTechnician} and has all of the methods and
        attributes defined by the interface.
        """
        technician = self.createTechnician(Store())
        technicianType = type(technician)
        self.assertTrue(
            ixmantissa.IOfferingTechnician.implementedBy(technicianType))
        self.assertTrue(
            verifyClass(ixmantissa.IOfferingTechnician, technicianType))
        self.assertTrue(
            verifyObject(ixmantissa.IOfferingTechnician, technician))


    def test_getInstalledOfferingNames(self):
        """
        The L{ixmantissa.IOfferingTechnician.getInstalledOfferingNames}
        implementation returns a C{list} of C{unicode} strings, each element
        giving the name of an offering which has been installed.
        """
        offer = self.createTechnician(Store())
        self.assertEqual(offer.getInstalledOfferingNames(), [])

        expected = []
        for dummyOffering in self.offeringPlugins + self.offeringPowerups:
            offer.installOffering(dummyOffering)
            expected.append(dummyOffering.name)
            expected.sort()
            installed = offer.getInstalledOfferingNames()
            installed.sort()
            self.assertEqual(installed, expected)


    def test_getInstalledOfferings(self):
        """
        The L{ixmantissa.IOfferingTechnician.getInstalledOfferings}
        implementation returns a C{dict} mapping C{unicode} offering names to
        the corresponding L{IOffering} providers.
        """
        store = Store()
        offer = self.createTechnician(store)
        self.assertEqual(offer.getInstalledOfferings(), {})

        expected = {}
        for dummyOffering in self.offeringPlugins:
            offer.installOffering(dummyOffering)
            expected[dummyOffering.name] = dummyOffering
            self.assertEqual(offer.getInstalledOfferings(), expected)
        for offeringPowerup in self.offeringPowerups:
            offer.installOffering(offeringPowerup)
            expected[offeringPowerup.name] = store.findUnique(offeringPowerup)
            self.assertEqual(offer.getInstalledOfferings(), expected)



class OfferingAdapterTests(unittest.TestCase, OfferingTechnicianTestMixin):
    """
    Tests for L{offering.OfferingAdapter}.
    """
    def setUp(self):
        """
        Hook offering plugin discovery so that only the fake offerings the test
        wants exist.
        """
        self.origGetOfferings = offering.getOfferings
        offering.getOfferings = self.getOfferings


    def tearDown(self):
        """
        Restore the original L{getOfferings} function.
        """
        offering.getOfferings = self.origGetOfferings


    def getOfferings(self):
        """
        Return some dummy offerings, as defined by C{self.offeringPlugins} and
        C{self.offeringPowerups}.
        """
        return self.offeringPlugins + self.offeringPowerups


    def createTechnician(self, store):
        """
        Create an L{offering.OfferingAdapter}.
        """
        return offering.OfferingAdapter(store)


    def test_installedOfferingUpgrade(self):
        """
        L{offering.OfferingAdapter.getInstalledOfferings} deletes any
        L{InstalledOffering} items it finds which correspond to L{IOffering}
        plugins which have been updated to the new style of offering definition
        and creates in their place an instance of the L{Item} L{IOffering}
        provider.
        """
        store = Store()
        offer = self.createTechnician(store)

        # Create offering installation state which corresponds to a
        # hypothetical Offering which was upgraded to FakeNewStyleOffering.
        installed = offer.installOffering(
            offering.Offering(
                FakeNewStyleOffering.name, None, [], [], [], [], []))

        # Save this attribute for later
        application = installed.application

        # Now force an upgrade to happen.  An offering with the right name will
        # be found due to the overridden getOfferings method which returns a
        # list including FakeNewStyleOffering.
        result = offer.getInstalledOfferings()

        # There should be an instance of FakeNewStyleOffering now.
        newOffering = store.findUnique(FakeNewStyleOffering)

        # It should have been in the result
        self.assertEqual(result, {FakeNewStyleOffering.name: newOffering})

        # The rest of the state should be as if it were installed normally,
        # referring to the existing InstalledOffering item's state.
        self.assertIdentical(newOffering.store, store)
        self.assertIdentical(newOffering.application, application)
        self.assertIn(
            newOffering, list(store.powerupsFor(ixmantissa.IOffering)))

        # The InstalledOffering should be gone.
        self.assertRaises(KeyError, store.getItemByID, installed.storeID)



class FakeOfferingTechnicianTests(unittest.TestCase, OfferingTechnicianTestMixin):
    """
    Tests (ie, verification) for L{FakeOfferingTechnician}.
    """
    def createTechnician(self, store):
        """
        Create a L{FakeOfferingTechnician}.
        """
        return FakeOfferingTechnician(store)



class BaseOfferingTests(unittest.TestCase):
    """
    Tests for the base Mantissa offering,
    L{xmantissa.plugins.baseoff.baseOffering}.
    """
    def test_interface(self):
        """
        C{baseOffering} provides L{IOffering}.
        """
        self.assertTrue(verifyObject(ixmantissa.IOffering, baseOffering))


    def test_staticContentPath(self):
        """
        C{baseOffering.staticContentPath} gives the location of a directory
        which has I{mantissa.css} in it.
        """
        self.assertTrue(
            baseOffering.staticContentPath.child('mantissa.css').exists())


    def test_siteConfiguration(self):
        """
        Installing L{baseOffering} on a store results in the store being
        powered up for L{ISiteURLGenerator}.
        """
        store = Store()
        ixmantissa.IOfferingTechnician(store).installOffering(baseOffering)

        # Really I just want the adaption to succeed with a good object.  The
        # providedBy assertion is the best I can think of. -exarkun
        self.assertTrue(
            ixmantissa.ISiteURLGenerator.providedBy(
                ixmantissa.ISiteURLGenerator(store)),
            "ISiteURLGenerator powerup does not provide ISiteURLGenerator.")
