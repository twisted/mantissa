
import sys

from zope.interface import implements

from twisted.python.components import registerAdapter
from twisted.python.util import sibpath

from twisted.conch import manhole

from axiom.attributes import integer
from axiom.item import Item
from axiom import userbase

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
    developers = integer(default=0)
    administrators = integer(default=0)

    def install(self):
        self.store.powerUp(self, ISessionlessSiteRootPlugin)

    def createResource(self):
        return static.File(sibpath(__file__, 'static'))

class ParentCounterMixin:
    def _getDevSite(self):
        # Developer site is required.  Make one if there isn't one.
        # Make sure site-wide dependency is available
        for devsite in self.store.parent.query(DeveloperSite):
            break
        else:
            devsite = DeveloperSite(store=self.store.parent)
            devsite.install()
        return devsite

    # XXX WAaah.  self.store.parent is None sometimes, depending on
    # how we got opened :/
    def increment(self):
#         devsite = self._getDevSite()
#         setattr(devsite, self.counterAttribute, getattr(devsite, self.counterAttribute) + 1)
        pass

    def decrement(self):
#         devsite = self._getDevSite()
#         setattr(devsite, self.counterAttribute, getattr(devsite, self.counterAttribute) - 1)
        pass

class AdminStatsApplication(Item, ParentCounterMixin):
    """
    """
    implements(INavigableElement)

    schemaVersion = 1
    typeName = 'administrator_application'

    counterAttribute = 'administrators'

    updateInterval = integer(default=5)

    def install(self):
        self.increment()
        self.store.powerUp(self, INavigableElement)

    def deletedFromStore(self, *a, **kw):
        self.decrement()
        return super(AdminStatsApplication, self).deletedFromStore(*a, **kw)

    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.0,
                           [webnav.Tab('Stats', self.storeID, 0.1)],
                           authoritative=False)]


class AdminStatsFragment(rend.Fragment):
    implements(INavigableFragment)

    live = False
    fragmentName = 'admin-stats'

    def head(self):
        return None

    def _query(self, *a, **kw):
        return self.original.store.parent.query(*a, **kw)

    def render_loginCount(self, ctx, data):
        for ls in self._query(userbase.LoginSystem):
            return ls.loginCount

    def render_failedLoginCount(self, ctx, data):
        for ls in self._query(userbase.LoginSystem):
            return ls.failedLogins

    def render_userCount(self, ctx, data):
        count = 0
        for la in self._query(userbase.LoginAccount):
            count += 1
        return count

    def render_disabledUserCount(self, ctx, data):
        count = 0
        for la in self._query(userbase.LoginAccount, userbase.LoginAccount.disabled != 0):
            count += 1
        return count

    def render_developerCount(self, ctx, data):
        for ds in self._query(DeveloperSite):
            return ds.developers

    def render_administratorCount(self, ctx, data):
        for ds in self._query(DeveloperSite):
            return ds.administrators

registerAdapter(AdminStatsFragment, AdminStatsApplication, INavigableFragment)


class DeveloperApplication(Item, ParentCounterMixin):
    """
    """
    implements(INavigableElement)

    counterAttribute = 'developers'

    schemaVersion = 1
    typeName = 'developer_application'

    statementCount = integer(default=0)

    def install(self):
        self.increment()
        self.store.powerUp(self, INavigableElement)

    def deletedFromStore(self, *a, **kw):
        self.decrement()
        return super(DeveloperApplication, self).deletedFromStore(*a, **kw)

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
        self.namespace = {'s': self.original.store}
        self.interpreter = manhole.ManholeInterpreter(self,
                                                      self.namespace)

    def head(self):
        return T.script(
            language='javascript',
            src='/static/webadmin/repl.js')

    def goingLive(self, ctx, client):
        self.client = client
        self.client.send(livepage.set('count', self.original.statementCount))

    def addOutput(self, output, async=False):
        # Manhole callback
        try:
            output = unicode(output)
        except UnicodeDecodeError, e:
            output = u'UnicodeDecodeError: ' + str(e)

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

    def endow(self, ticket, avatar):
        self.didYouUseIt += 1 # OMFG can you *read*??
        for X in WebSite, PrivateApplication, DeveloperApplication:
            X(store=avatar).install()
