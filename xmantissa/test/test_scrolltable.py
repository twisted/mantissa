
from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer, text
from twisted.trial import unittest

from xmantissa.scrolltable import ScrollingFragment


class DataThunk(Item):
    a = integer()
    b = integer()
    c = text()

class ScrollTableTest(unittest.TestCase):
    def setUp(self):
        self.store = Store()

    def testGetTwoChunks(self):
        six = DataThunk(a=6, b=8157, c=u'six', store=self.store)
        three = DataThunk(a=3, b=821375, c=u'three', store=self.store)
        seven = DataThunk(a=7, b=4724, c=u'seven', store=self.store)
        eight = DataThunk(a=8, b=61, c=u'eight', store=self.store)
        one = DataThunk(a=1, b=435716, c=u'one', store=self.store)
        two = DataThunk(a=2, b=67145, c=u'two', store=self.store)
        four = DataThunk(a=4, b=6327, c=u'four', store=self.store)
        five = DataThunk(a=5, b=91856, c=u'five', store=self.store)

        sf = ScrollingFragment(self.store, DataThunk, DataThunk.a > 4, [DataThunk.b, DataThunk.c], DataThunk.a)

        self.assertEquals(
            sf.requestRowRange(0, 2),
            [{'c': u'five', 'b': 91856}, {'c': u'six', 'b': 8157}])

        self.assertEquals(
            sf.requestRowRange(2, 4),
            [{'c': u'seven', 'b': 4724}, {'c': u'eight', 'b': 61}])

        sf.resort('b')

        self.assertEquals(sf.requestRowRange(0, 2),
                          [{'c': u'eight', 'b': 61}, {'c': u'seven', 'b': 4724}])
        self.assertEquals(sf.requestRowRange(2, 4),
                          [{'c': u'six', 'b': 8157}, {'c': u'five', 'b': 91856}])
