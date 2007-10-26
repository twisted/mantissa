# Copyright 2007 Divmod, Inc.
# See LICENSE file for details

"""
Tests for L{xmantissa.webnav}.
"""

from twisted.trial import unittest

from epsilon.structlike import record

from axiom.item import Item
from axiom.attributes import inmemory, integer
from axiom.store import Store
from axiom.dependency import installOn

from nevow.url import URL
from nevow import loaders, tags, context

from xmantissa import webnav
from xmantissa.webapp import PrivateApplication



class FakeNavigator(record('tabs')):
    def getTabs(self):
        return self.tabs


class NavConfigTests(unittest.TestCase):
    """
    Tests for free functions in L{xmantissa.webnav}.
    """
    def test_tabMerge(self):
        """
        L{webnav.getTabs} should combine tabs from the L{INavigableElement}
        providers passed to it into a single structure.  It should preserve the
        attributes of all of the tabs and order them and their children by
        priority.
        """
        nav = webnav.getTabs([
                FakeNavigator([webnav.Tab('Hello', 1, 0.5,
                                          [webnav.Tab('Super', 2, 1.0, (), False, '/Super/2'),
                                           webnav.Tab('Mega', 3, 0.5, (), False, '/Mega/3')],
                                          False, '/Hello/1')]),
                FakeNavigator([webnav.Tab('Hello', 4, 1.,
                                          [webnav.Tab('Ultra', 5, 0.75, (), False, '/Ultra/5'),
                                           webnav.Tab('Hyper', 6, 0.25, (), False, '/Hyper/6')],
                                          True, '/Hello/4'),
                               webnav.Tab('Goodbye', 7, 0.9, (), True, '/Goodbye/7')])])

        hello, goodbye = nav
        self.assertEqual(hello.name, 'Hello')
        self.assertEqual(hello.storeID, 4)
        self.assertEqual(hello.priority, 1.0)
        self.assertEqual(hello.authoritative,True)
        self.assertEqual(hello.linkURL, '/Hello/4')

        super, ultra, mega, hyper = hello.children
        self.assertEqual(super.name, 'Super')
        self.assertEqual(super.storeID, 2)
        self.assertEqual(super.priority, 1.0)
        self.assertEqual(super.authoritative, False)
        self.assertEqual(super.linkURL, '/Super/2')

        self.assertEqual(ultra.name, 'Ultra')
        self.assertEqual(ultra.storeID, 5)
        self.assertEqual(ultra.priority, 0.75)
        self.assertEqual(ultra.authoritative, False)
        self.assertEqual(ultra.linkURL, '/Ultra/5')

        self.assertEqual(mega.name, 'Mega')
        self.assertEqual(mega.storeID, 3)
        self.assertEqual(mega.priority, 0.5)
        self.assertEqual(mega.authoritative, False)
        self.assertEqual(mega.linkURL, '/Mega/3')

        self.assertEqual(hyper.name, 'Hyper')
        self.assertEqual(hyper.storeID, 6)
        self.assertEqual(hyper.priority, 0.25)
        self.assertEqual(hyper.authoritative, False)
        self.assertEqual(hyper.linkURL, '/Hyper/6')

        self.assertEqual(goodbye.name, 'Goodbye')
        self.assertEqual(goodbye.storeID, 7)
        self.assertEqual(goodbye.priority, 0.9)
        self.assertEqual(goodbye.authoritative, True)
        self.assertEqual(goodbye.linkURL, '/Goodbye/7')


    def test_setTabURLs(self):
        """
        Check that L{webnav.setTabURLs} correctly sets the C{linkURL}
        attribute of L{webnav.Tab} instances to the result of
        passing tab.storeID to L{xmantissa.ixmantissa.IWebTranslator.linkTo}
        if C{linkURL} is not set, and that it leaves it alone if it is
        """

        s = Store()

        privapp = PrivateApplication(store=s)
        installOn(privapp,s)

        tabs = [webnav.Tab('PrivateApplication', privapp.storeID, 0),
                webnav.Tab('Something Else', None, 0, linkURL='/foo/bar')]

        webnav.setTabURLs(tabs, privapp)

        self.assertEqual(tabs[0].linkURL, privapp.linkTo(privapp.storeID))
        self.assertEqual(tabs[1].linkURL, '/foo/bar')


    def test_getSelectedTabExactMatch(self):
        """
        Check that L{webnav.getSelectedTab} returns the tab whose C{linkURL}
        attribute exactly matches the path of the L{nevow.url.URL} it is passed
        """

        tabs = list(webnav.Tab(str(i), None, 0, linkURL='/' + str(i))
                        for i in xrange(5))

        for (i, tab) in enumerate(tabs):
            selected = webnav.getSelectedTab(tabs, URL.fromString(tab.linkURL))
            self.assertIdentical(selected, tab)

        selected = webnav.getSelectedTab(tabs, URL.fromString('/XYZ'))
        self.failIf(selected)


    def test_getSelectedTabPrefixMatch(self):
        """
        Check that L[webnav.getSelectedTab} returns the tab whose C{linkURL}
        attribute contains the longest prefix of path segments that appears
        at the beginning of the L{nevow.url.URL} it is passed (if there is not
        an exact match)
        """

        tabs = [webnav.Tab('thing1', None, 0, linkURL='/a/b/c/d'),
                webnav.Tab('thing2', None, 0, linkURL='/a/b/c')]

        def assertSelected(tab):
            selected = webnav.getSelectedTab(tabs, URL.fromString('/a/b/c/d/e'))
            self.assertIdentical(selected, tab)

        assertSelected(tabs[0])
        tabs.reverse()
        assertSelected(tabs[1])

        tabs.append(webnav.Tab('thing3', None, 0, linkURL='a/b/c/e/e'))
        assertSelected(tabs[1])

        t = webnav.Tab('thing4', None, 0, linkURL='/a/b/c/d/e')
        tabs.append(t)
        assertSelected(t)



class _MockSearchAggregator(Item):
    """
    Implement as much of L{xmantissa.ixmantissa.ISearchAggregator} as is
    required by L{webnav.NavMixin}.
    """
    attribute = integer()
    _providers = inmemory()

    def providers(self):
        """
        Return L{_providers}.
        """
        return self._providers



class NaxMixinTestCase(unittest.TestCase):
    """
    Tests for L{webnav.NavMixin}.
    """
    def setUp(self):
        store = Store()
        store.parent = store

        privapp = PrivateApplication(store=store)
        installOn(privapp, store)

        self.navMixin = webnav.NavMixin(
            privapp, privapp, privapp.getPageComponents(), u'user@host')

        self.privateApplication = privapp


    def test_searchRenderer(self):
        """
        L{webnav.NavMixin.render_search} should return an instance of the
        I{search} pattern from the navigation template, when there is a search
        aggregator with at least one provider.
        """
        searchAggregator = _MockSearchAggregator(_providers=['a provider'])
        self.navMixin.pageComponents.searchAggregator = searchAggregator
        self.navMixin._navTemplate = loaders.stan(tags.div[
            tags.div(attribute='test_searchRenderer', pattern='search')])
        result = self.navMixin.render_search(None, None)
        self.assertEqual(result.attributes['attribute'], 'test_searchRenderer')


    def test_searchFormAction(self):
        """
        L{webnav.NavMixin.render_searchFormAction} should fill the
        I{search-action} slot in its tag with the URL of the search
        aggregator.
        """
        searchAggregator = _MockSearchAggregator(
            store=Store(), _providers=['a provider'])
        self.navMixin.pageComponents.searchAggregator = searchAggregator
        ctx = context.WebContext(
            tag=tags.div(attribute='test_searchFormAction')[tags.slot('form-action')])
        result = self.navMixin.render_searchFormAction(ctx, None)
        self.assertEqual(result.attributes['attribute'], 'test_searchFormAction')
        self.assertEqual(
            result.slotData['form-action'],
            self.privateApplication.linkTo(searchAggregator.storeID))
