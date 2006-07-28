
from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer, text
from twisted.trial import unittest

from xmantissa.scrolltable import (
    ScrollingFragment, SequenceScrollingFragment,
    StoreIDSequenceScrollingFragment)


class DataThunk(Item):
    a = integer()
    b = integer()
    c = text()


class ScrollTestMixin(object):
    def setUp(self):
        self.store = Store()
        self.six = DataThunk(a=6, b=8157, c=u'six', store=self.store)
        self.three = DataThunk(a=3, b=821375, c=u'three', store=self.store)
        self.seven = DataThunk(a=7, b=4724, c=u'seven', store=self.store)
        self.eight = DataThunk(a=8, b=61, c=u'eight', store=self.store)
        self.one = DataThunk(a=1, b=435716, c=u'one', store=self.store)
        self.two = DataThunk(a=2, b=67145, c=u'two', store=self.store)
        self.four = DataThunk(a=4, b=6327, c=u'four', store=self.store)
        self.five = DataThunk(a=5, b=91856, c=u'five', store=self.store)
        self.scrollFragment = self.getScrollFragment()


    def test_performQueryAscending(self):
        """
        Test that some simple ranges can be correctly retrieved when the sort
        order is ascending on the default column.
        """
        self.scrollFragment.isAscending = True
        for low, high in [(0, 2), (1, 3), (2, 4)]:
            self.assertEquals(
                self.scrollFragment.performQuery(low, high),
                [self.five, self.six, self.seven, self.eight][low:high])


    def test_performQueryDescending(self):
        """
        Like L{test_performQueryAscending} but for the descending sort order.
        """
        self.scrollFragment.isAscending = False
        for low, high in [(0, 2), (1, 3), (2, 4)]:
            self.assertEquals(
                self.scrollFragment.performQuery(low, high),
                [self.eight, self.seven, self.six, self.five][low:high])



class ItemQueryScrollingFragmentTestCase(ScrollTestMixin, unittest.TestCase):
    def getScrollFragment(self):
        return ScrollingFragment(
            self.store, DataThunk, DataThunk.a > 4,
            [DataThunk.b, DataThunk.c], DataThunk.a)


    def testGetTwoChunks(self):
        self.assertEquals(
            self.scrollFragment.requestRowRange(0, 2),
            [{'c': u'five', 'b': 91856}, {'c': u'six', 'b': 8157}])

        self.assertEquals(
            self.scrollFragment.requestRowRange(2, 4),
            [{'c': u'seven', 'b': 4724}, {'c': u'eight', 'b': 61}])

        self.scrollFragment.resort('b')

        self.assertEquals(self.scrollFragment.requestRowRange(0, 2),
                          [{'c': u'eight', 'b': 61}, {'c': u'seven', 'b': 4724}])
        self.assertEquals(self.scrollFragment.requestRowRange(2, 4),
                          [{'c': u'six', 'b': 8157}, {'c': u'five', 'b': 91856}])



class SequenceScrollingFragmentTestCase(ScrollTestMixin, unittest.TestCase):
    """
    Run the general scrolling tests against L{SequenceScrollingFragment}.
    """
    def getScrollFragment(self):
        return SequenceScrollingFragment(
            self.store,
            [self.five, self.six, self.seven, self.eight],
            [DataThunk.b, DataThunk.c], DataThunk.a)


class StoreIDSequenceScrollingFragmentTestCase(ScrollTestMixin, unittest.TestCase):
    """
    Run the general scrolling tests against
    L{StoreIDSequenceScrollingFragmentTestCase}.
    """
    def getScrollFragment(self):
        return StoreIDSequenceScrollingFragment(
            self.store,
            [self.five.storeID, self.six.storeID,
             self.seven.storeID, self.eight.storeID],
            [DataThunk.b, DataThunk.c], DataThunk.a)
