# -*- test-case-name: xmantissa.test.test_webnav -*-

from epsilon.structlike import record

from zope.interface import implements

from nevow import url
from nevow.inevow import IQ

from xmantissa.ixmantissa import ITab
from xmantissa.fragmentutils import dictFillSlots

class TabMisconfiguration(Exception):
    def __init__(self, info, tab):
        Exception.__init__(
            self,
            "Inconsistent tab item factory information",
            info, tab)

TabInfo = record('priority storeID children linkURL authoritative',
                 authoritative=None)

class Tab(object):
    """Represent part or all of the layout of a single navigation tab.

    @ivar name: This tab's name.

    @ivar storeID: A /-separated string containing URL segments to be
    rendered as part of a link on the web.

    @ivar priority: A float between 0 and 1 indicating the relative ordering of
    this tab amongst its peers.  Higher priorities sort sooner.

    @ivar children: A tuple of tabs beneath this one.

    @ivar authoritative: A flag indicating whether this instance of the
    conceptual tab with this name takes precedent over any other instance of
    the conceptual tab with this name.  It is an error for two instances of the
    same conceptual tab to be authoritative.

    """

    _item = None
    implements(ITab)

    def __init__(self, name, storeID, priority, children=(), authoritative=True, linkURL=None):
        self.name = name
        self.storeID = storeID
        self.priority = priority
        self.children = tuple(children)
        self.authoritative = authoritative
        self.linkURL = linkURL

    def __repr__(self):
        return '<%s%s %r/%0.3f %r [%r]>' % (self.authoritative and '*' or '',
                                            self.__class__.__name__,
                                            self.name,
                                            self.priority,
                                            self.storeID,
                                            self.children)

    def __iter__(self):
        raise TypeError("%r are not iterable" % (self.__class__.__name__,))

    def __getitem__(self, key):
        """Retrieve a sub-tab from this tab by name.
        """
        tabs = [t for t in self.children if t.name == key]
        assert len(tabs) < 2, "children mis-specified for " + repr(self)
        if tabs:
            return tabs[0]
        raise KeyError(key)

    def pathFromItem(self, item, avatar):
        """
        @param item: A thing that we linked to, and such.

        @return: a list of [child, grandchild, great-grandchild, ...] that
        indicates a path from me to the navigation for that item, or [] if
        there is no path from here to there.
        """
        for subnav in self.children:
            subpath = subnav.pathFromItem(item, avatar)
            if subpath:
                subpath.insert(0, self)
                return subpath
        else:
            myItem = self.loadForAvatar(avatar)
            if myItem is item:
                return [self]
        return []

def getTabs(navElements):
    # XXX TODO: multiple levels of nesting, this is hard-coded to 2.
    # Map primary tab names to a TabInfo
    primary = {}

    # Merge tab information from all nav plugins into one big structure
    for plg in navElements:
        for tab in plg.getTabs():
            if tab.name not in primary:
                primary[tab.name] = TabInfo(
                    priority=tab.priority,
                    storeID=tab.storeID,
                    children=list(tab.children),
                    linkURL=tab.linkURL)
            else:
                info = primary[tab.name]

                if info.authoritative:
                    if tab.authoritative:
                        raise TabMisconfiguration(info, tab)
                else:
                    if tab.authoritative:
                        info.authoritative = True
                        info.priority = tab.priority
                        info.storeID = tab.storeID
                info.children.extend(tab.children)

    # Sort the tabs and their children by their priority
    def key(o):
        return -o.priority

    resultTabs = []

    for (name, info) in primary.iteritems():
        info.children.sort(key=key)

        resultTabs.append(
            Tab(name, info.storeID, info.priority, info.children))

    resultTabs.sort(key=key)

    return resultTabs

def setTabURLs(tabs, webTranslator):
    """
    Sets the C{linkURL} attribute on each L{Tab} instance
    in C{tabs} that does not already have it set

    @param tabs: sequence of L{Tab} instances
    @param webTranslator: L{xmantissa.ixmantissa.IWebTranslator}
                          implementor

    @return: None
    """

    for tab in tabs:
        if not tab.linkURL:
            tab.linkURL = webTranslator.linkTo(tab.storeID)
        setTabURLs(tab.children, webTranslator)

def getSelectedTab(tabs, forURL):
    """
    Returns the tab that should be selected when the current
    resource lives at C{forURL}.  Call me after L{setTabURLs}

    @param tabs: sequence of L{Tab} instances
    @param forURL: L{nevow.url.URL}

    @return: L{Tab} instance
    """

    flatTabs = []

    def flatten(tabs):
        for t in tabs:
            flatTabs.append(t)
            flatten(t.children)

    flatten(tabs)
    forURL = '/' + forURL.path

    for t in flatTabs:
        if forURL == t.linkURL:
            return t

    flatTabs.sort(key=lambda t: len(t.linkURL), reverse=True)

    for t in flatTabs:
        if not t.linkURL.endswith('/'):
            linkURL = t.linkURL + '/'
        else:
            linkURL = t.linkURL

        if forURL.startswith(linkURL):
            return t


class NavMixin(object):
    """
    Mixin for renderables that want to include the mantissa navigation &
    menubar in their output.  The way to do this is by including a render
    directive that calls the I{menubar} renderer.

    @type resolver: L{xmantissa.ixmantissa.ITemplateNameResolver}
    @type translator: L{xmantissa.ixmantissa.IWebTranslator}
    @type pageComponents: L{xmantissa.webapp._PageComponents}
    @type username: C{unicode}
    """
    def __init__(self, resolver, translator, pageComponents, username):
        self.resolver = resolver
        self.translator = translator
        self.pageComponents = pageComponents
        self.username = username
        self._navTemplate = translator.getDocFactory('navigation')
        setTabURLs(pageComponents.navigation, translator)


    def render_appNavigation(self, ctx, data):
        """
        Render some navigation tabs.
        """
        selectedTab = getSelectedTab(self.pageComponents.navigation,
                                     url.URL.fromContext(ctx))

        getp = IQ(self._navTemplate).onePattern

        for tab in self.pageComponents.navigation:
            if tab == selectedTab or selectedTab in tab.children:
                p = 'selected-app-tab'
                contentp = 'selected-tab-contents'
            else:
                p = 'app-tab'
                contentp = 'tab-contents'

            yield dictFillSlots(getp(p),
                    {'name': tab.name,
                     'tab-contents': getp(contentp).fillSlots('href', tab.linkURL)})


    def render_navigation(self, ctx, data):
        """
        Render some navigation for the "start menu".
        """
        getp = IQ(self._navTemplate).onePattern

        def fillSlots(tabs):
            for tab in tabs:
                if tab.children:
                    kids = getp('subtabs').fillSlots('kids', fillSlots(tab.children))
                else:
                    kids = ''

                yield dictFillSlots(getp('tab'), dict(href=tab.linkURL,
                                                      name=tab.name,
                                                      kids=kids))

        return fillSlots(self.pageComponents.navigation)


    def render_menubar(self, ctx, data):
        """
        Render the Mantissa menubar, by loading the "menubar" pattern from the
        navigation template.
        """
        return IQ(self._navTemplate).onePattern('menubar')


    def render_search(self, ctx, data):
        """
        Render some UI for performing searches, if we know about a search
        aggregator.
        """
        searchAggregator = self.pageComponents.searchAggregator

        if searchAggregator is None or not searchAggregator.providers():
            return ''
        return IQ(self._navTemplate).onePattern("search")


    def render_searchFormAction(self, ctx, data):
        """
        Render the URL that the search form should post to, if we know about a
        search aggregator.
        """
        searchAggregator = self.pageComponents.searchAggregator

        if searchAggregator is None or not searchAggregator.providers():
            action = ''
        else:
            action = self.webapp.linkTo(searchAggregator.storeID)
        return ctx.tag.fillSlots('form-action', action)


    def render_username(self, ctx, data):
        """
        Render the name of the user whose store is being viewed.
        """
        return ctx.tag[self.username]


    def data_settingsLink(self, ctx, data):
        """
        Render the URL of the settings page.
        """
        return self.translator.linkTo(self.pageComponents.settings.storeID)
