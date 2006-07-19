# -*- test-case-name: xmantissa.test.test_webnav -*-

from epsilon.structlike import record

from zope.interface import implements

from xmantissa.ixmantissa import ITab

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
