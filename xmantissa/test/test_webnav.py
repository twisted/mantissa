# Copyright 2005 Divmod, Inc.  See LICENSE file for details

from twisted.trial import unittest

from axiom.item import Item
from axiom.attributes import inmemory, integer
from axiom.store import Store
from axiom.dependency import installOn

from nevow.url import URL
from nevow import loaders, tags, context

from xmantissa import webnav
from xmantissa.webapp import PrivateApplication



class FakeNavigator1(object):
    def getTabs(self):
        return [webnav.Tab('Hello', 1234, 0.5,
                           [webnav.Tab('Super', 'sup', 1.0),
                            webnav.Tab('Mega', 'meg', 0.5)],
                           False)]



class FakeNavigator2(object):
    def getTabs(self):
        return [webnav.Tab('Hello', 5678, 1.,
                           [webnav.Tab('Ultra', 'ult', 0.75),
                            webnav.Tab('Hyper', 'hyp', 0.25)]),
                webnav.Tab('Goodbye', None, 0.9)]



class NavConfig(unittest.TestCase):
    def test_tabMerge(self):
        nav = webnav.getTabs([FakeNavigator1(),
                              FakeNavigator2()])

        self.assertEquals(
            nav[0].name, 'Hello')
        self.assertEquals(
            nav[0].storeID, 5678)

        self.assertEquals(
            nav[1].name, 'Goodbye')

        kids = [x.name for x in nav[0].children]
        self.assertEquals(kids, ['Super', 'Ultra', 'Mega', 'Hyper'])


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
