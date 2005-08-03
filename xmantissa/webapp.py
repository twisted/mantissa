"""
This module is the basis for Mantissa-based web applications.  It provides
several basic pluggable application-level features, most notably Powerup-based
integration of the extensible hierarchical navigation system defined in
xmantissa.webnav
"""

from zope.interface import implements

from axiom.item import Item
from axiom.attributes import text, integer, reference

from nevow.rend import Page, Fragment, NotFound
from nevow.livepage import LivePage
from nevow.inevow import IResource
from nevow import tags as t
from nevow.url import URL

from xmantissa.website import PrefixURLMixin
from xmantissa.webtheme import getAllThemes
from xmantissa.webnav import getTabs
from xmantissa._webidgen import genkey, storeIDToWebID, webIDToStoreID

from xmantissa.ixmantissa import INavigableFragment, INavigableElement,\
    ISiteRootPlugin

def _reorderForPreference(themeList, preferredThemeName):
    """
    Re-order the input themeList according to the preferred theme.

    Returns None.
    """
    for t in themeList:
        if preferredThemeName == t.themeName:
            themeList.remove(t)
            themeList.insert(0,t)
            return


class NavFragment(Fragment):
    def __init__(self, docFactory, navigation, webapp):
        Fragment.__init__(self, docFactory=docFactory)
        self.navigation = navigation
        self.webapp = webapp

    def render_tab(self, ctx, data):
        name = data.name
        subtabs = data.children
        self.subtabs = subtabs
        ctx.fillSlots('href', self.webapp.linkTo(data.storeID))
        ctx.fillSlots('name', name)
        if subtabs:
            st = NavFragment(self.docFactory, subtabs, self.webapp)
        else:
            st = ''
        ctx.fillSlots('subtabs', st)
        return ctx.tag

    def data_tabs(self, ctx, data):
        return self.navigation


class NavMixin(object):

    fragmentName = 'main'

    def __init__(self, webapp, navigation):
        self.webapp = webapp
        self.navigation = navigation

    def getDocFactory(self, fragmentName, default=None):
        return self.webapp.getDocFactory(fragmentName, default)

    def render_content(self, ctx, data):
        raise NotImplementedError("implement render_context in subclasses")

    def render_navigation(self, ctx, data):
        return NavFragment(self.getDocFactory('navigation'),
                           self.navigation,
                           self.webapp)

    def render_title(self, ctx, data):
        return ctx.tag[self.__class__.__name__]

    def render_head(self, ctx, data):
        return ctx.tag


class GenericNavigationPage(Page, NavMixin):
    def __init__(self, webapp, navigation, fragment):
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, navigation)
        self.fragment = fragment
        fragment.page = self

    def render_content(self, ctx, data):
        return ctx.tag[self.fragment]

class GenericNavigationLivePage(LivePage, NavMixin):
    # XXX TODO: support live nav, live fragments somehow
    def __init__(self, webapp, navigation, fragment):
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, navigation)
        self.fragment = fragment
        fragment.page = self

    def goingLive(self, ctx, client):
        getattr(self.fragment, 'goingLive', lambda x, y: None)(ctx, client)

    def locateHandler(self, ctx, path, name):
        return getattr(self.fragment, 'handle_' + name)

    def render_head(self, ctx, data):
        return ctx.tag[
            t.invisible(render=t.directive("liveglue")),
            ]

    def render_content(self, ctx, data):
        return ctx.tag[self.fragment]

class PrivateRootPage(Page, NavMixin):
    addSlash = True

    def __init__(self, webapp, navigation):
        self.webapp = webapp
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, navigation)

    def child_(self, ctx):
        if not self.navigation:
            return self
        # /private/XXXX ->
        click = self.webapp.linkTo(self.navigation[0].storeID)
        return URL.fromContext(ctx).click(click)

    def render_title(self, ctx, data):
        return 'OMG, WTF'

    def render_content(self, ctx, data):
        return """
        You have no default root page set, and no navigation plugins installed.  I
        don't know what to do.
        """

    def childFactory(self, ctx, name):
        storeID = self.webapp.linkFrom(name)
        if storeID is None:
            return None

        o = self.webapp.store.getItemByID(storeID, None)
        if o is None:
            return NotFound
        res = IResource(o, None)
        if res is not None:
            return res
        fragment = INavigableFragment(o, None)
        if fragment is None:
            return NotFound
        if fragment.fragmentName is not None:
            fragDocFactory = self.webapp.getDocFactory(fragment.fragmentName, None)
            if fragDocFactory is not None:
                fragment.docFactory = fragDocFactory
        if fragment.live:
            return GenericNavigationLivePage(
                self.webapp, self.navigation, fragment)
        else:
            return GenericNavigationPage(self.webapp,
                                         self.navigation, fragment)



class PrivateApplication(Item, PrefixURLMixin):
    """
    This is the root of a private, navigable web application.  It is designed
    to be installed on avatar stores after installing WebSite.

    To plug into it, install powerups of the type INavigableElement on the
    user's store.  Their tabs will be retrieved and items that are part of
    those powerups will be linked to; provide IResource adapters for said
    items.

    @ivar preferredTheme: A C{unicode} string naming the preferred theme for
    this application.  Templates and suchlike will be looked up for this theme
    first.

    @ivar hitCount: Number of page loads of this application.

    @ivar privateKey: A random integer used to deterministically but
    unpredictably perturb link generation to avoid being the target of XSS
    attacks.

    @ivar privateIndexPage: A reference to the Item whose IResource or
    INavigableFragment adapter will be displayed on login and upon viewing the
    'root' page, /private/.
    """

    implements(ISiteRootPlugin)

    typeName = 'private_web_application'
    schemaVersion = 1

    preferredTheme = text()
    hitCount = integer()
    privateKey = integer()

    privateIndexPage = reference()

    prefixURL = 'private'

    def __init__(self, **kw):
        super(PrivateApplication, self).__init__(**kw)
        gk = genkey()
        print 'privateKey in', gk
        self.privateKey = gk
        print 'privateKey out', self.privateKey

    def linkTo(self, obj):
        # currently obj must be a storeID, but other types might come eventually
        # print 'linkTo privateKey', self.privateKey
        return '/private/'+storeIDToWebID(self.privateKey, obj)

    def linkFrom(self, webid):
        # print 'linkFrom privateKey', self.privateKey
        return webIDToStoreID(self.privateKey, webid)

    def install(self):
        self.store.powerUp(self, ISiteRootPlugin)

    def createResource(self):
        return PrivateRootPage(
            self, getTabs(self.store.powerupsFor(INavigableElement)))

    def resourceFactory(self, segments):
        return super(PrivateApplication, self).resourceFactory(segments)

    def getDocFactory(self, fragmentName, default=None):
        l = list(getAllThemes())
        _reorderForPreference(l, self.preferredTheme)
        for t in l:
            fact = t.getDocFactory(fragmentName, None)
            if fact is not None:
                return fact
        return default
