from zope.interface import implements

from twisted.trial.unittest import TestCase

from axiom.item import Item, InstallableMixin
from axiom.store import Store
from axiom import attributes

from xmantissa import prefs, ixmantissa, liveform

class WidgetShopPrefCollection(Item, InstallableMixin, prefs.PreferenceCollectionMixin):
    """
    Basic L{xmantissa.ixmantissa.IPreferenceCollection}, with a single
    preference, C{preferredWidget}
    """
    implements(ixmantissa.IPreferenceCollection)

    installedOn = attributes.reference()
    preferredWidget = attributes.text()

    def installOn(self, other):
        other.powerUp(self, ixmantissa.IPreferenceCollection)
        super(WidgetShopPrefCollection, self).installOn(other)

    def getPreferenceParameters(self):
        return (liveform.Parameter('preferredWidget',
                                    liveform.TEXT_INPUT,
                                    unicode,
                                    'Preferred Widget'),)

class PreferencesTestCase(TestCase):
    """
    Test case for basic preference functionality
    """

    def testAggregation(self):
        """
        Assert that L{xmantissa.prefs.PreferenceAggregator} gives us
        the right values for the preference attributes on L{WidgetShopPrefCollection}
        """
        store = Store()

        agg = prefs.PreferenceAggregator(store=store)
        agg.installOn(store)

        coll = WidgetShopPrefCollection(store=store)
        coll.installOn(store)

        coll.preferredWidget = u'Foo'

        self.assertEqual(agg.getPreferenceValue('preferredWidget'), 'Foo')

        coll.preferredWidget = u'Bar'

        self.assertEqual(agg.getPreferenceValue('preferredWidget'), 'Bar')
