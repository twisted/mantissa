# Copyright 2005 Divmod, Inc.  See LICENSE file for details

from twisted.trial import unittest

from axiom.store import Store

from nevow.url import URL

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

    def testTabMerge(self):
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

    def testSetTabURLs(self):
        """
        Check that L{webnav.setTabURLs} correctly sets the C{linkURL}
        attribute of L{webnav.Tab} instances to the result of
        passing tab.storeID to L{xmantissa.ixmantissa.IWebTranslator.linkTo}
        if C{linkURL} is not set, and that it leaves it alone if it is
        """

        s = Store()

        privapp = PrivateApplication(store=s)
        privapp.installOn(s)

        tabs = [webnav.Tab('PrivateApplication', privapp.storeID, 0),
                webnav.Tab('Something Else', None, 0, linkURL='/foo/bar')]

        webnav.setTabURLs(tabs, privapp)

        self.assertEqual(tabs[0].linkURL, privapp.linkTo(privapp.storeID))
        self.assertEqual(tabs[1].linkURL, '/foo/bar')

    def testGetSelectedTabExactMatch(self):
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

    def testGetSelectedTabPrefixMatch(self):
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
