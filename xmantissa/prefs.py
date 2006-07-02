# -*- test-case-name: xmantissa.test.historic -*-

import pytz

from zope.interface import implements

from twisted.python.components import registerAdapter

from nevow import athena
from nevow.athena import expose

from axiom.item import Item, InstallableMixin
from axiom import attributes, upgrade, userbase

from xmantissa.fragmentutils import PatternDictionary

from xmantissa.ixmantissa import (IPreferenceCollection,
                                  INavigableFragment,
                                  IPreferenceAggregator)

class DefaultPreferenceCollection(Item, InstallableMixin):
    implements(IPreferenceCollection)

    typeName = 'mantissa_default_preference_collection'
    schemaVersion = 2

    applicationName = 'Mantissa'

    installedOn = attributes.reference()
    itemsPerPage = attributes.integer(default=10)
    timezone = attributes.text(default=u'US/Eastern')

    _cachedPrefs = attributes.inmemory()

    def installOn(self, other):
        super(DefaultPreferenceCollection, self).installOn(other)
        other.powerUp(self, IPreferenceCollection)

    def activate(self):
        ipp = _ItemsPerPage(self.itemsPerPage, self, (10, 20, 30))
        tz = _TimezonePreference(self.timezone, self)


        localparts = list(self.store.query(
            userbase.LoginMethod,
            userbase.LoginMethod.internal == True,
            limit=1).getColumn("localpart"))
        if localparts:
            localpart = localparts[0]
        else:
            localpart = None

        lp = _LocalpartPreference(localpart, self)

        self._cachedPrefs = {'itemsPerPage': ipp,
                             'timezone': tz,
                             'localpart': lp}

    def getPreferences(self):
        return self._cachedPrefs


    def _localpartSet(self, value):
        # Create a LoginMethod to actually hold this information.  This
        # "preference" can only be set once, so only one LoginMethod will be
        # created in this way.
        siteStore = self.store.parent
        hostname = userbase.getDomainNames(siteStore)[0]

        loginAccount = self.store.findUnique(userbase.LoginAccount)
        loginAccount.addLoginMethod(
            localpart=value,
            internal=True,
            protocol=userbase.ANY_PROTOCOL,
            verified=True,
            domain=hostname)


    def setPreferenceValue(self, pref, value):
        pref.value = value
        if pref.key == "localpart":
            self._localpartSet(value)
        else:
            setattr(self, pref.key, value)


    def getSections(self):
        return None



def defaultPreferenceCollection1To2(old):
    from xmantissa.settings import Settings
    Settings(store=old.store).installOn(old.store)
    return old.upgradeVersion('mantissa_default_preference_collection', 1, 2,
                              installedOn=old.installedOn,
                              itemsPerPage=old.itemsPerPage,
                              timezone=u'US/Eastern')

upgrade.registerUpgrader(defaultPreferenceCollection1To2,
                         'mantissa_default_preference_collection',
                         1, 2)

class PreferenceValidationError(Exception):
    pass

class Preference(object):
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

    def settable(self):
        return True

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

class _TimezonePreference(Preference):
    def __init__(self, value, collection):
        super(_TimezonePreference, self).__init__('timezone', value, 'Timezone',
                                                  collection, 'Your current timezone')

    def choices(self):
        return pytz.common_timezones

    def displayToValue(self, display):
        return unicode(display)

    def valueToDisplay(self, value):
        return str(value)



class _LocalpartPreference(Preference):
    """
    Allow the one-time configuration of a local address for an account.

    This will be an address beneath a domain which is hosted by this server.
    It is intended as the outward-facing contact address for protocols such as
    Q2Q, SIP, and SMTP.

    XXX TODO - At some point, this should also support selection of a domain,
    since a Mantissa server may host multiple domains.
    """
    def __init__(self, value, collection):
        Preference.__init__(self, 'localpart', value, 'Localpart', collection,
                            'Localpart')


    def choices(self):
        return None


    def displayToValue(self, display):
        value = unicode(display)
        store = self.collection.store.parent

        # XXX This enforces uniqueness across all domains.  We really want to
        # enforce uniqueness within each domain.
        existing = store.query(
            userbase.LoginMethod,
            attributes.AND(userbase.LoginMethod.localpart == value,
                           userbase.LoginMethod.internal == True),
            limit=1).count()

        if existing:
            raise PreferenceValidationError('Localpart is not unique')
        return value


    def valueToDisplay(self, value):
        if value is None:
            return 'Not Set'
        return value


    def settable(self):
        # localpart can only be set once - so we'll only allow the user to set
        # it when the current value is None.
        return self.value is None



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

# FIXME this thing *really* needs to use liveform

class PreferenceEditor(athena.LiveFragment):
    implements(INavigableFragment)

    fragmentName = 'preference-editor'
    title = 'Preferences'
    live = 'athena'
    jsClass = u'Mantissa.Preferences'

    prefs = None
    aggregator = None

    def serializePrefs(self):
        for pref in self.prefs:
            value = pref.valueToDisplay(pref.value)

            prefmap = dict(name=str(pref.name), key=str(pref.key), value=value)

            if pref.settable():
                pname = 'preference'
            else:
                pname = 'unsettable-preference'

            itemPattern = self.patterns[pname](data=prefmap)

            choices = pref.choices()

            if choices is not None:
                choices = list(dict(choice=pref.valueToDisplay(c))
                                    for c in choices)

                subPattern = self.patterns['multiple-choice-edit']
                subPattern = subPattern(data=dict(value=value, choices=choices))
            else:
                subPattern = self.patterns['edit']
                subPattern = subPattern.fillSlots('value', value)

            yield itemPattern.fillSlots('edit-widget', subPattern)

    def savePref(self, key, value):
        pref = self.aggregator.getPreference(key)
        value = pref.displayToValue(value)
        pref.collection.setPreferenceValue(pref, value)
    expose(savePref)

    def data_preferences(self, ctx, data):
        self.patterns = PatternDictionary(self.docFactory)
        self.aggregator = IPreferenceAggregator(self.original.store)
        self.prefs = self.original.getPreferences().values()

        return self.patterns['preference-collection'].fillSlots(
                    'preferences', self.serializePrefs())

    def head(self):
        return None

registerAdapter(PreferenceEditor, PreferenceAggregator, INavigableFragment)
