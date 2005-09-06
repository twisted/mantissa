
from twisted.trial import unittest

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import text

from xmantissa.website import PrefixURLMixin, WebSite
from xmantissa.ixmantissa import ISiteRootPlugin

from zope.interface import implements

class Dummy:
    def __init__(self, pfx):
        self.pfx = pfx

class PrefixTester(Item, PrefixURLMixin):

    implements(ISiteRootPlugin)

    typeName = 'test_prefix_widget'
    schemaVersion = 1

    prefixURL = text()

    def createResource(self):
        return Dummy(self.prefixURL)

class SiteRootTest(unittest.TestCase):
    def testPrefixPriorityMath(self):
        s = Store()

        PrefixTester(store=s,
                     prefixURL=u"hello").install()

        PrefixTester(store=s,
                     prefixURL=u"").install()

        ws = WebSite(store=s)
        res, segs = ws.locateChild(None, ('hello',))
        self.assertEquals(res.pfx, 'hello')
        self.assertEquals(segs, ())

        res, segs = ws.locateChild(None, ('',))
        self.assertEquals(res.pfx, '')
        self.assertEquals(segs, ('',))
