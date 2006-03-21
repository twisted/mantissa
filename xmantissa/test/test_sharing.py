
from zope.interface import Interface, implements

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer

from xmantissa import sharing

from twisted.trial import unittest

from twisted.python.components import registerAdapter

class IPrivateThing(Interface):
    def mutateSomeState():
        pass

class INoData(Interface):
    pass

class PrivateThing(Item):
    implements(IPrivateThing, INoData)
    publicData = integer()
    typeName = 'test_sharing_private_thing'
    schemaVersion = 1

    def mutateSomeState(self):
        self.publicData += 5

class IPublicThing(Interface):
    def callMethod():
        pass

    def isMethodAvailable(self):
        pass

class PublicFacingAdapter(object):

    implements(IPublicThing)

    def __init__(self, thunk):
        self.thunk = thunk

    def isMethodAvailable(self):
        return IPrivateThing.providedBy(self.thunk)

    def callMethod(self):
        return self.thunk.mutateSomeState()



class SimpleSharingTest(unittest.TestCase):

    def setUp(self):
        self.store = s = Store()

    def testSimpleShare(self):
        t = PrivateThing(store=self.store,
                         publicData=456)
        t2 = PrivateThing(store=self.store,
                          publicData=234) # not as good
        sharyMcFacet = sharing.shareItem(t, toName=u'bob@divmod.com')
        sharySharalot = sharing.shareItem(t2, toRole=sharing.getAuthenticatedRole(self.store),
                                          shareID=sharyMcFacet.shareID)

        shareReturn = sharing.getShare(self.store,
                                       sharing.getPrimaryRole(self.store,
                                                              u'bob@divmod.com'),
                                       sharyMcFacet.shareID)

        shareAdapt = IPrivateThing(shareReturn)

        shareAdapt.mutateSomeState()
        self.assertEquals(t.publicData, 456 + 5)


        self.assertRaises(sharing.NoSuchShare,
                          sharing.getShare,
                          self.store,
                          sharing.getPrimaryRole(self.store,
                                                 u''),
                          sharyMcFacet.shareID)

        alicesThing = sharing.getShare(
                self.store,
                sharing.getPrimaryRole(self.store,
                                       u'alice@divmod.com',
                                       True),
                sharyMcFacet.shareID)

        alicesThing.mutateSomeState()
        self.assertEquals(t2.publicData, 234 + 5)

    def testShareAndAdapt(self):
        t = PrivateThing(store=self.store,
                         publicData=789)
        self.failUnless(IPublicThing(t).isMethodAvailable())

        shared = sharing.shareItem(t, toName=u'testshare', interfaces=[INoData])
        proxy = sharing.getShare(self.store,
                sharing.getPrimaryRole(self.store, u'testshare'),
                shared.shareID)
        self.failIf(IPublicThing(proxy).isMethodAvailable())
        self.assertRaises(AttributeError, IPublicThing(proxy).callMethod)



registerAdapter(PublicFacingAdapter, INoData, IPublicThing)
