from zope.interface import implements

from twisted.python.components import registerAdapter
from nevow import rend, tags, inevow, livepage
from axiom.item import Item, InstallableMixin
from axiom import attributes

from xmantissa.ixmantissa import (IPreference, IPreferenceCollection,
                                  INavigableFragment,
                                  IPreferenceAggregator)

class PreferenceValidationError(Exception):
    pass

class Preference(object):
    implements(IPreference)

    def __init__(self, key, value, name, collection, description):
        self.key = key
        self.value = value
        self.name = name
        self.collection = collection
        self.description = description

    def choices(self):
        raise NotImplementedError

    def displayToValue(self, display):
        raise NotImplementedError

    def valueToDisplay(self, value):
        raise NotImplementedError

class MultipleChoicePreference(Preference):
    """base class for multiple choice preferences that have simple mappings
       between internal values and display values."""

    def __init__(self, key, value, name, collection, description, valueToDisplay):
        init = super(MultipleChoicePreference, self).__init__
        init(key, value, name, collection, description)

        self._valueToDisplay = valueToDisplay
        self._displayToValue = dict((v, k) for (k, v) in valueToDisplay.iteritems())
        assert len(valueToDisplay) == len(self._displayToValue)

    def choices(self):
        return self._valueToDisplay.iterkeys()

    def displayToValue(self, display):
        try:
            return self._displayToValue[display]
        except KeyError:
            raise PreferenceValidationError, 'bad value: %r' % display

    def valueToDisplay(self, value):
        return self._valueToDisplay[value]

class _ItemsPerPage(MultipleChoicePreference):
    def __init__(self, value, collection, choices):
        desc = 'Show this many items per page (for search results)'
        super(_ItemsPerPage, self).__init__('itemsPerPage', value, 'Items Per Page',
                                            collection, desc,
                                            dict((c, str(c)) for c in choices))

class DefaultPreferenceCollection(Item, InstallableMixin):
    implements(IPreferenceCollection)

    schemaVersion = 1
    typeName = 'mantissa_default_preference_collection'
    name = 'Basic Preferences'

    itemsPerPage = attributes.integer(default=10)
    installedOn = attributes.reference()
    _cachedPrefs = attributes.inmemory()

    def installOn(self, other):
        super(DefaultPreferenceCollection, self).installOn(other)
        other.powerUp(self, IPreferenceCollection)

    def activate(self):
        ipp = _ItemsPerPage(self.itemsPerPage, self, (10, 20, 30))
        self._cachedPrefs = {"itemsPerPage" : ipp}

    # IPreferenceCollection
    def getPreferences(self):
        return self._cachedPrefs

    def setPreferenceValue(self, pref, value):
        # this ugliness is short lived
        assert hasattr(self, pref.key)
        setattr(pref, 'value', value)
        self.store.transact(lambda: setattr(self, pref.key, value))

class PreferenceAggregator(Item, InstallableMixin):
    implements(IPreferenceAggregator)

    schemaVersion = 1
    typeName = 'preference_aggregator'

    _prefMap = attributes.inmemory()
    installedOn = attributes.reference()

    def installOn(self, other):
        super(PreferenceAggregator, self).installOn(other)
        other.powerUp(self, IPreferenceAggregator)

    def activate(self):
        self._prefMap = None

    # IPreferenceAggregator
    def getPreference(self, key):
        if self._prefMap is None:
            # prefMap is a dictionary of {key:preference}, across all
            # preference collections
            prefMap = dict()
            for prefColl in self.installedOn.powerupsFor(IPreferenceCollection):
                prefMap.update(prefColl.getPreferences())
            self._prefMap = prefMap

        # will raise KeyError if no collection holds this key
        return self._prefMap[key]

    def getPreferenceValue(self, key):
        return self.getPreference(key).value

class PreferenceEditor(rend.Fragment):
    implements(INavigableFragment)

    fragmentName = 'preference-editor'
    title = 'Preferences'
    live = True

    prefs = None
    aggregator = None

    def head(self):
        return tags.script(type='text/javascript',
                           src='/Mantissa/js/preferences.js')

    def serializePref(self, pref):
        value = pref.valueToDisplay(pref.value)

        prefmap = dict(name=str(pref.name), key=str(pref.key), value=value)

        itemPattern = self.patterns['preference'](data=prefmap)

        choices = pref.choices()

        if choices is not None:
            choices = list(dict(choice=pref.valueToDisplay(c))
                                for c in choices)

            subPattern = self.patterns['multipleChoiceEdit']
            subPattern = subPattern(data=dict(value=value, choices=choices))
        else:
            subPattern = self.patterns['edit']
            subPattern = subPattern.fillSlots('value', value)

        return itemPattern.fillSlots('edit-widget', subPattern)

    def serializePrefs(self):
        for (collectionName, prefs) in self.prefs.iteritems():
            pattern = self.patterns['preferenceCollection']
            container = pattern.fillSlots('name', collectionName)

            content = map(self.serializePref, prefs)

            yield container.fillSlots('preferences', content)

    def handle_savePref(self, ctx, key, value):
        pref = self.aggregator.getPreference(key)
        try:
            value = pref.displayToValue(value)
        except PreferenceValidationError, err:
            # make this nicer at some point
            return (livepage.js.alert('Error Saving Preferences: %s' % err), livepage.eol)

        pref.collection.setPreferenceValue(pref, value)
        return (livepage.js.updatePrefValue(key, pref.valueToDisplay(value)), livepage.eol)

    def data_preferences(self, ctx, data):
        pgen = inevow.IQ(self.docFactory).patternGenerator
        self.patterns = dict(multipleChoiceEdit=pgen('multiple-choice-edit'),
                             edit=pgen('edit'), preference=pgen('preference'),
                             preferenceCollection=pgen('preference-collection'))

        installedOn = self.original.installedOn
        self.aggregator = IPreferenceAggregator(installedOn)
        prefs = dict()

        for collection in installedOn.powerupsFor(IPreferenceCollection):
            prefs[collection.name] = collection.getPreferences().values()

        self.prefs = prefs

        return self.serializePrefs()

registerAdapter(PreferenceEditor, PreferenceAggregator, INavigableFragment)
