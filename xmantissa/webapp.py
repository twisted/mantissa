"""
This module is the basis for Mantissa-based web applications.  It provides
several basic pluggable application-level features, most notably Powerup-based
integration of the extensible hierarchical navigation system defined in
xmantissa.webnav
"""

from zope.interface import implements

from axiom.item import Item
from axiom.attributes import text, integer

from nevow.rend import Page, Fragment, NotFound
from nevow.livepage import LivePage
from nevow.inevow import IResource
from nevow import tags as t

from xmantissa.website import PrefixURLMixin
from xmantissa.webtheme import getAllThemes
from xmantissa.webnav import getTabs

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
    def __init__(self, docFactory, navigation):
        Fragment.__init__(self, docFactory=docFactory)
        self.navigation = navigation

    def render_tab(self, ctx, data):
        name = data.name
        subtabs = data.children
        self.subtabs = subtabs
        ctx.fillSlots('href', data.suffixURL)
        ctx.fillSlots('name', name)
        if subtabs:
            st = t.br(), 'subtabs:', NavFragment(self.docFactory, subtabs)
        else:
            st = t.br(), 'no sub'
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
                           self.navigation)

    def render_title(self, ctx, data):
        return ctx.tag[self.__class__.__name__]

    def render_head(self, ctx, data):
        return ctx.tag


class GenericNavigationPage(Page, NavMixin):
    def __init__(self, webapp, navigation, fragment):
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, navigation)
        self.fragment = fragment

    def render_content(self, ctx, data):
        return ctx.tag[self.fragment]

class GenericNavigationLivePage(LivePage, NavMixin):
    # XXX TODO: support live nav, live fragments somehow
    def __init__(self, webapp, navigation, fragment):
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, navigation)
        self.fragment = fragment

    def locateHandler(self, ctx, path, name):
        return getattr(self.fragment, 'handle_' + name)

    def render_head(self, ctx, data):
        return ctx.tag[
            t.invisible(render=t.directive("liveid")),
            t.invisible(render=t.directive("liveglue")),
            ]
    def render_content(self, ctx, data):
        return ctx.tag[self.fragment]


class PrivateRootPage(Page, NavMixin):

    addSlash = True

    def __init__(self, webapp, navigation):
        docFactory = webapp.getDocFactory('shell')
        self.webapp = webapp
        Page.__init__(self, docFactory=docFactory)
        NavMixin.__init__(self, webapp, navigation)

    def render_content(self, ctx, data):
        return 'Root page: possibly this should be a redirect instead.  Temporarily not.'

    def childFactory(self, ctx, name):
        try:
            storeID = int(name)
        except ValueError:
            return NotFound
        else:
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

    """
    implements(ISiteRootPlugin)

    typeName = 'private_web_application'
    schemaVersion = 1

    preferredTheme = text()
    hitCount = integer()

    prefixURL = 'private'

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
