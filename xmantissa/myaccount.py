from twisted.python.components import registerAdapter

from axiom.item import Item, InstallableMixin
from axiom import attributes

from xmantissa import ixmantissa
from xmantissa.fragmentutils import FragmentCollector
from xmantissa.prefs import PreferenceAggregator
from xmantissa.webgestalt import AuthenticationApplication

class MyAccount(Item, InstallableMixin):

    typeName = 'mantissa_myaccount'
    schemaVersion = 1

    installedOn = attributes.reference()

class MyAccountFragment(FragmentCollector):
    fragmentName = 'my-account'
    title = 'My Account'

    collect = (PreferenceAggregator, AuthenticationApplication)

registerAdapter(MyAccountFragment, MyAccount, ixmantissa.INavigableFragment)

