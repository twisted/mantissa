from twisted.python.components import registerAdapter

from axiom.item import Item, InstallableMixin
from axiom import attributes

from xmantissa import ixmantissa, prefs
from xmantissa.fragmentutils import FragmentCollector
from xmantissa.webgestalt import AuthenticationApplication

class Settings(Item, InstallableMixin):
    typeName = 'mantissa_settings'
    schemaVersion = 1

    installedOn = attributes.reference()

class SettingsFragment(FragmentCollector):
    fragmentName = 'settings'
    title = 'Settings'

    def __init__(self, original):
        super(SettingsFragment, self).__init__(
                    ixmantissa.IWebTranslator(original.store),
                    collect=self._makeCollect(original.store),
                    name='settings-fragment-outer')

    def _makeCollect(self, store):
        translator = ixmantissa.IWebTranslator(store)

        collect = [ixmantissa.INavigableFragment(
                        store.findUnique(AuthenticationApplication))]

        for appSettings in store.powerupsFor(
                                    ixmantissa.IPreferenceCollection):
            appCollect = list()
            appCollect.append(prefs.PreferenceEditor(appSettings))

            sections = appSettings.getSections()
            if sections is not None:
                appCollect.extend(map(ixmantissa.INavigableFragment, sections))

            appCollector = FragmentCollector(translator, collect=appCollect,
                                             name=appSettings.applicationName)

            appCollector.fragmentName = self.fragmentName
            appCollector.title = appSettings.applicationName
            collect.append(appCollector)

        return collect

registerAdapter(SettingsFragment, Settings, ixmantissa.INavigableFragment)
