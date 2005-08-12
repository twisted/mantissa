
import sys

from zope.interface import implements

from twisted.python.components import registerAdapter
from twisted.python.util import sibpath

from twisted.conch import manhole

from axiom.attributes import integer
from axiom.item import Item

from xmantissa import webnav
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite, PrefixURLMixin
from xmantissa.ixmantissa import INavigableElement, INavigableFragment, \
    ISessionlessSiteRootPlugin

from nevow import rend, flat, json, livepage, loaders, static, tags as T


class DeveloperSite(Item, PrefixURLMixin):
    """Provides static content sessionlessly for the developer application.
    """
    implements(ISessionlessSiteRootPlugin)

    typeName = 'developer_site'
    schemaVersion = 1

    prefixURL = 'static/webadmin'

    # Counts of each kind of user
    developers = integer()
    administrators = integer()

    def install(self):
        self.store.powerUp(self, ISessionlessSiteRootPlugin)

    def createResource(self):
        return static.File(sibpath(__file__, 'static'))

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
    implements(INavigableFragment)

    live = True
    fragmentName = 'admin-python-repl'

    docFactory = loaders.stan(T.div[
            T.div['Statement count: ', T.span(id='count')],
            T.div(id='output'),
            T.form(onsubmit="return submitInput(source)")[
                T.input(type='text', id='source')]])

    def __init__(self, *a, **kw):
        rend.Fragment.__init__(self, *a, **kw)
        self.namespace = {}
        self.interpreter = manhole.ManholeInterpreter(self)

    def head(self):
        return T.script(
            language='javascript',
            src='/static/webadmin/repl.js')

    def goingLive(self, ctx, client):
        self.client = client
        self.client.send(livepage.set('count', self.original.statementCount))

    def addOutput(self, output, async=False):
        # Manhole callback
        lines = livepage.js(json.serialize(output.splitlines()))
        cmd = livepage.js.appendManholeOutput(lines)
        cmd = flat.flatten(cmd)
        self.client.send(cmd)

    def handle_input(self, ctx, source):
        # IClientHandle(ctx)
        more = self.interpreter.push(source)
        if more:
            o = self.addOutput('... ')
        else:
            o = self.addOutput('>>> ')
            self.original.statementCount += 1
        return [o, livepage.eol, livepage.set('count', self.original.statementCount)]

registerAdapter(REPL, DeveloperApplication, INavigableFragment)

class DONTUSETHISBenefactor(Item):
    typeName = 'seriously_dont_use_it_is_just_an_example'
    schemaVersion = 1

    didYouUseIt = integer(default=0)

    def endow(self, avatar):
        self.didYouUseIt += 1 # OMFG can you *read*??
        for X in WebSite, PrivateApplication, DeveloperApplication:
            X(store=avatar).install()
