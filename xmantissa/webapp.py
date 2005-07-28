
"""

This module is the basis for Mantissa-based web applications.  It provides
several basic pluggable application-level features, most notably Powerup-based
integration of the extensible hierarchical navigation system defined in
xmantissa.webnav

"""


from xmantissa.webtheme import getAllThemes
from xmantissa.webnav import getTabs

def _reorderForPreference(themeList, preferredThemeName):
    """
    Re-order the input themeList according to the preferred theme.

    Returns None.
    """
    for t in themeList:
        if preferredThemeName == t.name:
            themeList.remove(t)
            themeList.insert(0,t)
            return


class NavFragment(Fragment):
    def __init__(self, docFactory, navigation):
        Fragment.__init__(self, docFactory)
        self.navigation = navigation

    def data_navigation(self, ctx):
        return self.navigation

    def render_tab(self, ctx, data):
        ctx.fillSlots('name', self.stuff.name)
        ctx.fillSlots('link', self.linkTarget)
        return ctx.tag

    def render_subtabs(self, ctx, data):
        return NavFragment(docFactory=self.docFactory, navigation=data.subtabs)


class NavMixin(object):

    fragmentName = 'main'

    def __init__(self, siteconf, navigation):
        self.siteconf = siteconf
        self.navigation = navigation

    def getDocFactory(self):
        return self.siteconf.getDocFactory(self.fragmentName)

    def render_content(self, ctx, data):
        raise NotImplementedError("implement render_context in subclasses")

    def render_navigation(self, ctx, data):
        return NavFragment(self.getDocFactory('navigation'), self.navigation)


class PrivatePage(Page, NavMixin):
    def __init__(self, siteConf, navigation):
        docFactory = siteConf.getDocFactory('shell')
        Page.__init__(self)
        NavMixin.__init__(self, siteConf, navigation)


class PrivateApplication(Item):
    # Installed on Avatar stores.
    implements(ISiteRootPlugin)

    typeName = 'private_web_application'
    schemaVersion = 1

    preferredTheme = text()
    hitCount = integer()

    def install(self):
        self.store.powerUp(self, ISiteRootPlugin)

    def resourceFactory(self, segments):
        self.hitCount += 1
        if segments and segments[0] == 'private':
            nav = getTabs(self.store.powerupsFor(INavigableElement))
            return PrivatePage(self, nav), segments[1:]

    def getDocFactory(self, fragmentName):
        l = list(getAllThemes())
        _reorderForPreference(l, self.preferredTheme)
        for t in l:
            fact = t.getDocFactory(fragmentName)
            if fact is not None:
                return fact
        raise KeyError("No such theme element: %r in themes: %r" %
                       (fragmentName, l))
