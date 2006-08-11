from nevow import loaders, tags
from nevow.livetrial import testcase

from axiom.item import Item
from axiom.store import Store
from axiom.attributes import integer

from xmantissa.scrolltable import ScrollingFragment
from xmantissa.webtheme import getLoader


class ItemItem(Item):
    column = integer()



class ScrollTableTestCase(testcase.TestCase):
    jsClass = u'Mantissa.Test.ScrollTable'

    def getWidgetDocument(self):
        s = Store()
        for i in xrange(25):
            ItemItem(store=s, column=i)

        sf = ScrollingFragment(s, ItemItem, None, (ItemItem.column,))
        sf.jsClass = 'Mantissa.Test.TestableScrollTable'
        sf.setFragmentParent(self)
        sf.docFactory = getLoader(sf.fragmentName)
        return sf
