from zope.interface import implements
from twisted.python.components import registerAdapter
from nevow import rend
from nevow.taglibrary import tabbedPane

from axiom.item import Item, InstallableMixin
from axiom import attributes
from xmantissa import ixmantissa
from xmantissa.prefs import PreferenceAggregator
from xmantissa.webgestalt import AuthenticationApplication

class MyAccount(Item, InstallableMixin):

    typeName = 'mantissa_myaccount'
    schemaVersion = 1

    installedOn = attributes.reference()


class FragmentCollector(rend.Fragment):
    implements(ixmantissa.INavigableFragment)

    fragmentName = None
    live = True
    title = None

    collect = ()

    def __init__(self, original, docFactory=None):
        rend.Fragment.__init__(self, original, docFactory)

        translator = ixmantissa.IWebTranslator(original.installedOn)

        tabs = []
        for item in self.collect:
            item = original.installedOn.findFirst(item)
            frag = ixmantissa.INavigableFragment(item)
            frag.docFactory = translator.getDocFactory(frag.fragmentName, None)
            tabs.append((frag.title, frag))
        self.tabs = tabs

    def head(self):
        for (tabTitle, fragment) in self.tabs:
            content = fragment.head()
            if content is not None:
                yield content

        yield tabbedPane.tabbedPaneGlue.inlineGlue

    def locateHandler(self, ctx, path, name):
        for (tabTitle, fragment) in self.tabs:
            handler = getattr(fragment, 'handle_'+name, None)
            if handler is not None:
                return handler
        raise AttributeError, 'no handler for %r' % name

    def data_tabbedPane(self, ctx, data):
        return tabbedPane.tabbedPane(ctx, dict(pages=self.tabs))

class MyAccountFragment(FragmentCollector):
    fragmentName = 'my-account'
    title = 'My Account'

    collect = (PreferenceAggregator, AuthenticationApplication)

registerAdapter(MyAccountFragment, MyAccount, ixmantissa.INavigableFragment)

