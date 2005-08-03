
from zope.interface import implements

from twisted.python.components import registerAdapter

from axiom.attributes import integer
from axiom.item import Item

from xmantissa import webnav
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite
from xmantissa.ixmantissa import INavigableElement, INavigableFragment


from nevow import rend, livepage, loaders, tags as T


class DeveloperApplication(Item):
    """
    """
    implements(INavigableElement)

    schemaVersion = 1
    typeName = 'developer_application'

    statementCount = integer(default=0)

    def install(self):
        self.store.powerUp(self, INavigableElement)

    # INavigableElement
    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.0,
                           [webnav.Tab('REPL', self.storeID, 0.0)],
                           authoritative=False)]


class REPL(rend.Fragment):
    """
    """

    live = True
    fragmentName = 'admin-python-repl'

    docFactory = loaders.stan(T.div[
            T.div(id='count'),
            T.div(id='output'),
            T.form(onsubmit="server.handle('input', source.value); source.value = ''; return false;")[
                T.input(type='text', id='source')]])

    def handle_input(self, ctx, source):
        # IClientHandle(ctx)
        self.original.statementCount += 1
        return [
            livepage.append('output', T.div[source]), livepage.eol,
            livepage.set('count', self.original.statementCount), livepage.eol,
            ]

registerAdapter(REPL, DeveloperApplication, INavigableFragment)

class DONTUSETHISBenefactor(Item):
    typeName = 'seriously_dont_use_it_is_just_an_example'
    schemaVersion = 1

    didYouUseIt = integer(default=0)

    def endow(self, avatar):
        self.didYouUseIt += 1 # OMFG can you *read*??
        for X in WebSite, PrivateApplication, DeveloperApplication:
            X(store=avatar).install()
