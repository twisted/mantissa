from nevow import loaders, tags
from nevow.athena import expose
from nevow.livetrial.testcase import TestCase

from axiom.item import Item
from axiom.store import Store
from axiom.attributes import integer

from xmantissa.scrolltable import SequenceScrollingFragment, ScrollingFragment
from xmantissa.webtheme import getLoader
from xmantissa.webapp import PrivateApplication


class ScrollElement(Item):
    """
    Dummy item used to populate scrolltables for the scrolltable tests.
    """
    column = integer()



class ScrollTableModelTestCase(TestCase):
    """
    Tests for the scrolltable's model class.
    """
    jsClass = u'Mantissa.Test.ScrollTableModelTestCase'



class ScrollTableWidgetTestCase(TestCase):
    """
    Tests for the scrolltable's view class.
    """
    jsClass = u'Mantissa.Test.ScrollTableViewTestCase'


    def __init__(self):
        TestCase.__init__(self)
        self.perTestData = {}


    def getScrollingWidget(self, key):
        store = Store()
        PrivateApplication(store=store).installOn(store)
        elements = [ScrollElement(store=store) for i in range(10)]
        columns = [ScrollElement.column]
        f = SequenceScrollingFragment(store, elements, columns)
        f.docFactory = getLoader(f.fragmentName)
        f.setFragmentParent(self)
        self.perTestData[key] = (store, elements, f)
        return f
    expose(getScrollingWidget)


    def changeRowCount(self, key, n):
        store, elements, fragment = self.perTestData[key]
        elements[:] = [ScrollElement(store=store) for i in range(n)]
    expose(changeRowCount)
