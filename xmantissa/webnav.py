
from zope.interface import implements

from axiom.slotmachine import _structlike

from xmantissa.ixmantissa import ITab, INavigableElement

class TabMisconfiguration(Exception):
    def __init__(self, info, tab):
        Exception.__init__(
            "Inconsistent tab item factory information",
            info, tab)

class TabInfo(_structlike):
    __names__ = [
        'priority',
        'number',
        'suffixURL',
        'children']

class Tab(object):
    """Represent part or all of the layout of a single navigation tab.

    @ivar name: This tab's name.

    @ivar suffixURL: A /-separated string containing URL segments to be
    rendered as part of a link on the web.

    @ivar priority: A float between 0 and 1 indicating the relative ordering of
    this tab amongst its peers.  Higher priorities sort sooner.

    @ivar children: A tuple of tabs beneath this one.
    """

    _item = None
    implements(ITab)

    def __init__(self, name, suffixURL, priority, children=()):
        self.name = name
        self.suffixURL = suffixURL
        self.priority = priority
        self.children = tuple(children)

    def __repr__(self):
        return '<%s %r/%0.3f %r [%r]>' % (self.__class__.__name__,
                                          self.name,
                                          self.priority,
                                          self.suffixURL,
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
                    number=1,
                    suffixURL=tab.suffixURL,
                    children=list(tab.children))
            else:
                info = primary[tab.name]

                if info.suffixURL is None:
                    if tab.suffixURL is not None:
                        info.suffixURL = tab.suffixURL
                elif tab.suffixURL is not None:
                    if info.suffixURL is not tab.suffixURL:
                        raise TabMisconfiguration(info, tab)

                if tab.priority is not None:
                    info.priority += tab.priority
                    info.number += 1
                info.children.extend(tab.children)

    # Sort the tabs and their children by their priority
    def key(o):
        return -o.priority

    resultTabs = []

    for (name, info) in primary.iteritems():
        info.priority /= info.number
        info.children.sort(key=key)

        resultTabs.append(
            Tab(name, info.suffixURL, info.priority, info.children))

    resultTabs.sort(key=key)

    return Tab(".", lambda nothing: None, 1.0, resultTabs)
