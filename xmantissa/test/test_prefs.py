from zope.interface import implements
from axiom.item import Item
from axiom.store import Store
from axiom import attributes
from xmantissa import prefs, ixmantissa
from twisted.trial.unittest import TestCase

class PreferredWidget(object):
    implements(ixmantissa.IPreference)

    key = 'preferredWidget'
    name = 'Preferred Widget'
    description = 'Widgets!'

    def __init__(self, value=None, collection=None, choices=None):
        self.value = value
        self.collection = collection

    def choices(self):
        return choices

    def displayToValue(self, display):
        return display

    def valueToDisplay(self, value):
        return value

def makePrefCollection(prefMap):
    class WidgetShopPrefCollection(Item):
        implements(ixmantissa.IPreferenceCollection)

        schemaVersion = 1
        typeName = 'widget_shop_pref_collection'

        installedOn = attributes.reference()
        preferredWidget = attributes.text()

        _cachedPrefs = attributes.inmemory()

        def activate(self):
            self._cachedPrefs = prefMap

        def installOn(self, other):
            assert self.installedOn is None, "cannot install WidgetShopPrefCollection on more than one thing"
            other.powerUp(self, ixmantissa.IPreferenceCollection)
            self.installedOn = other

        # IPreferenceCollection
        def getPreferences(self):
            return self._cachedPrefs

        def setPreferenceValue(self, pref, value):
            assert hasattr(self, pref.key)
            setattr(pref, 'value', value)
            self.store.transact(lambda: setattr(self, pref.key, value))

    return WidgetShopPrefCollection

class PreferencesTestCase(TestCase):
    def testAggregation(self):
        pref = PreferredWidget(value=u'Blob', choices=(u'Blob', u'Slob', u'Frob'))

        store = Store()
        def txn():
            prefs.PreferenceAggregator(store=store).installOn(store)
            return makePrefCollection({pref.key:pref})(store=store).installOn(store)
        pref.collection = store.transact(txn)

        aggregator = ixmantissa.IPreferenceAggregator(store)
        getPrefVal = lambda v: aggregator.getPreference(v).value

        self.assertEqual(getPrefVal(pref.key), pref.value)
        ixmantissa.IPreferenceCollection(store).setPreferenceValue(pref, u'Slob')
        self.assertEqual(getPrefVal(pref.key), u'Slob')
