
from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer, text
from twisted.trial import unittest

from xmantissa.scrolltable import (
    ScrollingFragment, SequenceScrollingFragment,
    StoreIDSequenceScrollingFragment,
    AttributeColumn,
    UnsortableColumnWrapper,
    UnsortableColumn)


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
        sf = ScrollingFragment(
            self.store, DataThunk, DataThunk.a > 4,
            [DataThunk.b, DataThunk.c], DataThunk.a)
        sf.linkToItem = lambda ign: None
        return sf


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


    def testSortsOnFirstSortable(self):
        """
        Test that the scrolltable sorts on the first sortable column
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (UnsortableColumn(DataThunk.a),
                 DataThunk.b))

        self.assertEquals(sf.currentSortColumn, DataThunk.b)


    def testSortsOnFirstSortable2(self):
        """
        Same as L{testSortsOnFirstSortable}, but for the case where the first
        sortable column is the first in the column list
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (DataThunk.a, UnsortableColumn(DataThunk.b)))

        self.assertEquals(sf.currentSortColumn, DataThunk)


    def testTestNoSortables(self):
        """
        Test that the scrolltable can handle the case where all columns are
        unsortable
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (UnsortableColumn(DataThunk.a),
                 UnsortableColumn(DataThunk.b)))

        self.assertEquals(sf.currentSortColumn, None)


    def testUnsortableColumnWrapper(self):
        """
        Test that an L{UnsortableColumnWrapper} wrapping an L{AttributeColumn}
        is treated the same as L{UnsortableColumn}
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (UnsortableColumnWrapper(AttributeColumn(DataThunk.a)),
                 DataThunk.b))

        self.assertEquals(sf.currentSortColumn, DataThunk.b)


    def  testSortMetadata(self):
        """
        Test that C{getTableMetadata} is correct with respect to the
        sortability of columns
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (UnsortableColumn(DataThunk.a),
                 UnsortableColumn(DataThunk.b)))

        meta = sf.getTableMetadata()
        cols = meta[1]
        self.assertEquals(cols['a'][1], False)
        self.assertEquals(cols['b'][1], False)


    def testSortMetadata2(self):
        """
        Same as L{testSortMetadata}, but with one sortable column
        """
        sf = ScrollingFragment(
                self.store, DataThunk, None,
                (DataThunk.a,
                 UnsortableColumn(DataThunk.b)))

        meta = sf.getTableMetadata()
        cols = meta[1]
        self.assertEquals(cols['a'][1], True)
        self.assertEquals(cols['b'][1], False)



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


class UnsortableColumnWrapperTestCase(unittest.TestCase):
    """
    Tests for L{UnsortableColumnWrapper}
    """

    def test_unsortableColumnWrapper(self):
        attr = DataThunk.a
        col = AttributeColumn(attr)
        unsortableCol = UnsortableColumnWrapper(col)

        item = DataThunk(store=Store(), a=26)

        value = unsortableCol.extractValue(None, item)
        self.assertEquals(value, item.a)
        self.assertEquals(value, col.extractValue(None, item))

        typ = unsortableCol.getType()
        self.assertEquals(typ, 'integer')
        self.assertEquals(typ, col.getType())

        self.assertEquals(unsortableCol.sortAttribute(), None)
