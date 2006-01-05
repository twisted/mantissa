# -*- test-case-name: xmantissa -*-

from zope.interface import implements

from twisted.python.components import registerAdapter
from twisted.python.util import sibpath
from twisted.python import log
from twisted.application.service import IService, Service
from twisted.conch import manhole

from epsilon import extime

from axiom.attributes import integer, boolean, timestamp, bytes, reference, inmemory
from axiom.item import Item, InstallableMixin
from axiom import userbase
from axiom.substore import SubStore

from xmantissa import webnav, tdb, tdbview, offering, signup
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite, PrefixURLMixin
from xmantissa.webgestalt import AuthenticationApplication
from xmantissa.ixmantissa import INavigableElement, INavigableFragment, \
    ISessionlessSiteRootPlugin

from nevow import rend, athena, flat, json, livepage, static, tags as T


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

    def installOn(self, other):
        other.powerUp(self, ISessionlessSiteRootPlugin)

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
            devsite.installOn(self.store.parent)
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

    def installOn(self, other):
        self.increment()
        other.powerUp(self, INavigableElement)

    def deletedFromStore(self, *a, **kw):
        self.decrement()
        return super(AdminStatsApplication, self).deletedFromStore(*a, **kw)

    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.0,
                           [webnav.Tab('Stats', self.storeID, 0.1)],
                           authoritative=False)]


class LocalUserBrowser(Item):
    implements(INavigableElement)

    typeName = 'local_user_browser'
    schemaVersion = 1

    garbage = integer(default=12345678653)

    def installOn(self, other):
        other.powerUp(self, INavigableElement)

    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.0,
                           [webnav.Tab('Local Users', self.storeID, 0.1)],
                           authoritative=False)]



class LocalUserBrowserFragment(tdbview.TabularDataView):
    def __init__(self, userBrowser):
        tdm = tdb.TabularDataModel(
            userBrowser.store.parent,
            userbase.LoginMethod,
            [userbase.LoginMethod.localpart,
             userbase.LoginMethod.domain,
             userbase.LoginMethod.verified],
            baseComparison=(userbase.LoginMethod.domain != None),
            defaultSortColumn='domain', # XXX TODO (domain, localpart) sorting
            defaultSortAscending=True)
        views = [
            tdbview.ColumnViewBase('localpart', typeHint='text'),
            tdbview.ColumnViewBase('domain', typeHint='text'),
            tdbview.ColumnViewBase('verified', typeHint='boolean')]
        super(LocalUserBrowserFragment, self).__init__(tdm, views)

registerAdapter(LocalUserBrowserFragment, LocalUserBrowser, INavigableFragment)



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

    def installOn(self, other):
        self.increment()
        other.powerUp(self, INavigableElement)

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

    def __init__(self, *a, **kw):
        rend.Fragment.__init__(self, *a, **kw)
        self.namespace = {'s': self.original.store}
        self.interpreter = manhole.ManholeInterpreter(self,
                                                      self.namespace)

    def head(self):
        return T.script(
            language='javascript',
            src='/static/webadmin/js/repl.js')

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

class Traceback(Item):
    typeName = 'mantissa_traceback'
    schemaVersion = 1

    when = timestamp()
    traceback = bytes()
    collector = reference()

    def __init__(self, store, collector, failure):
        when = extime.Time()
        traceback = failure.getTraceback()
        super(Traceback, self).__init__(
            store=store,
            traceback=traceback,
            when=when,
            collector=collector)

class TracebackCollector(Item, Service):
    implements(IService)

    typeName = 'mantissa_traceback_collector'
    schemaVersion = 1

    tracebackCount = integer(default=0)

    parent = inmemory()
    running = inmemory()
    name = inmemory()

    def installOn(self, other):
        other.powerUp(self, IService)
        self.setServiceParent(other)

    def startService(self):
        log.addObserver(self.emit)

    def stopService(self):
        log.removeObserver(self.emit)

    def emit(self, event):
        if event.get('isError') and event.get('failure') is not None:
            f = event['failure']
            def txn():
                self.tracebackCount += 1
                Traceback(store=self.store, collector=self, failure=f)
            self.store.transact(txn)

    def getTracebacks(self):
        """
        Return an iterable of Tracebacks that have been collected.
        """
        return self.store.query(Traceback,
                                Traceback.collector == self)


class TracebackViewer(Item):
    implements(INavigableElement)

    typeName = 'mantissa_tb_viewer'
    schemaVersion = 1

    allowDeletion = boolean(default=False)

    def installOn(self, other):
        other.powerUp(self, INavigableElement)

    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.0,
                           [webnav.Tab('Errors', self.storeID, 0.3)],
                           authoritative=False)]

    def _getCollector(self):
        def ifCreate(coll):
            coll.installOn(self.store.parent)
        return self.store.parent.findOrCreate(TracebackCollector, ifCreate)

    # this needs to be moved somewhere else, topPanelContent is no more
    #def topPanelContent(self):
    #    # XXX There should really be a juice protocol for this.
    #    return '%d errors logged' % (self._getCollector().tracebackCount,)


class TracebackViewerFragment(rend.Fragment):
    implements(INavigableFragment)

    live = False
    fragmentName = 'traceback-viewer'

    def head(self):
        return ()

    def render_tracebacks(self, ctx, data):
        for tb in self.original._getCollector().getTracebacks():
            yield T.div[T.code[T.pre[tb.traceback]]]

registerAdapter(TracebackViewerFragment, TracebackViewer, INavigableFragment)


class DONTUSETHISBenefactor(Item):
    typeName = 'seriously_dont_use_it_is_just_an_example'
    schemaVersion = 1

    didYouUseIt = integer(default=0)

    def endow(self, ticket, avatar):
        self.didYouUseIt += 1 # OMFG can you *read*??
        for X in WebSite, PrivateApplication, DeveloperApplication, TracebackViewer:
            X(store=avatar).installOn(avatar)
        AuthenticationApplication(store=avatar)

# This is a lot like the above benefactor.  We should probably delete
# the above benefactor now.
class AdministrativeBenefactor(Item):
    typeName = 'mantissa_administrative_benefactor'
    schemaVersion = 1

    endowed = integer(default=0)

    def endow(self, ticket, avatar):
        self.endowed += 1
        for powerUp in [

            # Install a web site for the individual user as well.
            # This is necessary because although we have a top-level
            # website for everybody, not all users should be allowed
            # to log in through the web (like UNIX's "system users",
            # "nobody", "database", etc.)  Note, however, that there
            # is no port number, because the WebSite's job in this
            # case is to be a web *resource*, not a web *server*.
            WebSite,

            # Now we install the 'private application' plugin for
            # 'admin', on admin's private store, This provides the URL
            # "/private", but only when 'admin' is logged in.  It is a
            # hook to hang other applications on.  (XXX Rename:
            # PrivateApplication should probably be called
            # PrivateAppShell)
            PrivateApplication,

            # These are plugins *for* the PrivateApplication; they
            # publish objects via the tab-based navigation: a
            # statistics page and a Python interactive interpreter,
            # respectively.
            AdminStatsApplication,
            DeveloperApplication,

            # This is another PrivateApplication plugin.  It allows
            # the administrator to configure the services offered
            # here.
            offering.OfferingConfiguration,

            # And another one: SignupConfiguration allows the
            # administrator to add signup forms which grant various
            # kinds of account.
            signup.SignupConfiguration,

            # This one lets the administrator view unhandled
            # exceptions which occur in the server.
            TracebackViewer,

            # And this one gives the administrator a page listing all
            # users which exist in this site's credentials database.
            LocalUserBrowser]:


            avatar.findOrCreate(powerUp).installOn(avatar)
        AuthenticationApplication(store=avatar)

    def deprive(self, ticket, avatar):
        # Only delete the really administratory things.
        for powerUp in [
            AdminStatsApplication, DeveloperApplication,
            TracebackViewer, LocalUserBrowser]:
            avatar.findUnique(powerUp).deleteFromStore()
