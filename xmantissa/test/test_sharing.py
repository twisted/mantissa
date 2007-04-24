
from zope.interface import Interface, implements

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer
from axiom.test.util import QueryCounter

from xmantissa import sharing

from twisted.trial import unittest

from twisted.python.components import registerAdapter

class IPrivateThing(Interface):
    def mutateSomeState():
        pass

class IReadOnly(Interface):
    def retrieveSomeState():
        """
        Retrieve the data.
        """


class PrivateThing(Item):
    implements(IPrivateThing, IReadOnly)
    publicData = integer()
    typeName = 'test_sharing_private_thing'
    schemaVersion = 1

    def mutateSomeState(self):
        self.publicData += 5

    def retrieveSomeState(self):
        """
        Retrieve my public data.
        """
        return self.publicData



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

registerAdapter(PublicFacingAdapter, IReadOnly, IPublicThing)


class SimpleSharing(unittest.TestCase):


    def setUp(self):
        self.store = Store()


    def test_differentUserSameID(self):
        """
        Verify that if different facets of the same item are shared to different
        users with the same shareID, each user will receive the correct
        respective facet with only the correct methods exposed.
        """
        t = PrivateThing(store=self.store, publicData=789)
        toBob = sharing.shareItem(t, toName=u'bob@example.com',
                                  interfaces=[IReadOnly])
        toAlice = sharing.shareItem(t, toName=u'alice@example.com',
                                    shareID=toBob.shareID,
                                    interfaces=[IPrivateThing])
        # Sanity check.
        self.assertEquals(toBob.shareID, toAlice.shareID)
        asBob = sharing.getShare(self.store,
                                 sharing.getPrimaryRole(
                self.store, u'bob@example.com'),
                                 toBob.shareID)
        asAlice = sharing.getShare(self.store,
                                 sharing.getPrimaryRole(
                self.store, u'alice@example.com'),
                                 toBob.shareID)
        self.assertEquals(asBob.retrieveSomeState(), 789)
        self.assertRaises(AttributeError, lambda : asBob.mutateSomeState)
        self.assertRaises(AttributeError, lambda : asAlice.retrieveSomeState)
        asAlice.mutateSomeState()
        # Make sure they're both seeing the same item.
        self.assertEquals(asBob.retrieveSomeState(), 789+5)


    def test_simpleShare(self):
        """
        Verify that an item which is shared with shareItem can be retrieved and
        manipulated with getShare.
        """
        t = PrivateThing(store=self.store, publicData=456)
        shareItemResult = sharing.shareItem(t, toName=u'bob@example.com')
        gotShare = sharing.getShare(self.store,
                                    sharing.getPrimaryRole(self.store,
                                                           u'bob@example.com'),
                                    shareItemResult.shareID)
        gotShare.mutateSomeState()
        self.assertEquals(t.publicData, 456 + 5)


    def test_invalidShareID(self):
        """
        Verify that NoSuchShare is raised when getShare is called without sharing
        anything first.
        """
        self.assertRaises(sharing.NoSuchShare,
                          sharing.getShare,
                          self.store,
                          sharing.getPrimaryRole(self.store,
                                                 u'nobody@example.com'),
                          u"not a valid shareID")

    def test_unauthorizedAccessNoShare(self):
        """
        Verify that NoSuchShare is raised when getShare is called with a user who
        is not allowed to access a shared item.
        """
        t = PrivateThing(store=self.store, publicData=345)
        theShare = sharing.shareItem(t, toName=u'somebody@example.com')
        self.assertRaises(sharing.NoSuchShare,
                          sharing.getShare,
                          self.store,
                          sharing.getPrimaryRole(self.store,
                                                 u'nobody@example.com'),
                          theShare.shareID)


    def test_shareAndAdapt(self):
        """
        Verify that when an item is shared to a particular user with a particular
        interface, retrieiving it for that user results in methods on the given
        interface being callable and other methods being restricted.
        """
        t = PrivateThing(store=self.store, publicData=789)

        # Sanity check.
        self.failUnless(IPublicThing(t).isMethodAvailable())

        shared = sharing.shareItem(t, toName=u'testshare', interfaces=[IReadOnly])
        proxy = sharing.getShare(self.store,
                                 sharing.getPrimaryRole(self.store, u'testshare'),
                                 shared.shareID)
        self.failIf(IPublicThing(proxy).isMethodAvailable())
        self.assertRaises(AttributeError, IPublicThing(proxy).callMethod)



class AccessibilityQuery(unittest.TestCase):

    def setUp(self):
        self.i = 0
        self.store = Store()
        self.things = []
        self.bobThings = []
        self.aliceThings = []
        self.bob = sharing.getPrimaryRole(self.store, u'bob@example.com',
                                          createIfNotFound=True)
        self.alice = sharing.getPrimaryRole(self.store, u'alice@example.com',
                                            createIfNotFound=True)


    def test_twoInterfacesTwoGroups(self):
        """
        Verify that when an item is shared to two roles that a user is a member of,
        they will have access to both interfaces when it is retrieved with
        getShare.
        """
        self.addSomeThings()
        us = sharing.getPrimaryRole(self.store, u'us', True)
        them = sharing.getPrimaryRole(self.store, u'them', True)
        self.bob.becomeMemberOf(us)
        self.bob.becomeMemberOf(them)
        it = PrivateThing(store=self.store, publicData=1234)
        sharing.shareItem(it, toRole=us, shareID=u'q', interfaces=[IPrivateThing])
        sharing.shareItem(it, toRole=them, shareID=u'q', interfaces=[IReadOnly])
        that = sharing.getShare(self.store, self.bob, u'q')
        self.assertEquals(that.retrieveSomeState(), 1234)
        that.mutateSomeState()
        self.assertEquals(that.retrieveSomeState(), 1239)


    def test_twoInterfacesTwoGroupsQuery(self):
        """
        Verify that when an item is shared to two roles that a user is a member of,
        and then retrieved by an asAccessibleTo query, both interfaces will be
        accessible on each object in the query result, and the same number of
        items will be accessible in the query as were shared.
        """
        us = sharing.getPrimaryRole(self.store, u'us', True)
        them = sharing.getPrimaryRole(self.store, u'them', True)
        self.bob.becomeMemberOf(us)
        self.bob.becomeMemberOf(them)
        for x in range(3):
            it = PrivateThing(store=self.store, publicData=x)
            sharing.shareItem(it, toRole=us, shareID=u'q',
                              interfaces=[IPrivateThing])
            sharing.shareItem(it, toRole=them, shareID=u'q',
                              interfaces=[IReadOnly])
        # sanity check
        self.assertEquals(self.store.query(PrivateThing).count(), 3)
        aat = list(sharing.asAccessibleTo(self.bob, self.store.query(
                    PrivateThing, sort=PrivateThing.publicData.descending)))
        aat2 = list(sharing.asAccessibleTo(self.bob, self.store.query(
                    PrivateThing, sort=PrivateThing.publicData.ascending)))
        # sanity check x2
        for acc in aat:
            acc.mutateSomeState()
        expectedData = [x + 5 for x in reversed(range(3))]
        self.assertEquals([acc.retrieveSomeState() for acc in aat],
                          expectedData)
        self.assertEquals([acc.retrieveSomeState() for acc in aat2],
                          list(reversed(expectedData)))


    def test_twoInterfacesTwoGroupsUnsortedQuery(self):
        """
        Verify that when duplicate shares exist for the same item and an
        asAccessibleTo query is made with no specified sort, the roles are
        still deduplicated properly.
        """
        us = sharing.getPrimaryRole(self.store, u'us', True)
        them = sharing.getPrimaryRole(self.store, u'them', True)
        self.bob.becomeMemberOf(us)
        self.bob.becomeMemberOf(them)
        for x in range(3):
            it = PrivateThing(store=self.store, publicData=x)
            sharing.shareItem(it, toRole=us, shareID=u'q',
                              interfaces=[IPrivateThing])
            sharing.shareItem(it, toRole=them, shareID=u'q',
                              interfaces=[IReadOnly])
        # sanity check
        self.assertEquals(self.store.query(PrivateThing).count(), 3)
        aat = list(sharing.asAccessibleTo(self.bob, self.store.query(
                    PrivateThing)))
        # sanity check x2
        for acc in aat:
            acc.mutateSomeState()
        expectedData = [x + 5 for x in range(3)]
        aat.sort(key=lambda i: i.retrieveSomeState())
        self.assertEquals([acc.retrieveSomeState() for acc in aat],
                          expectedData)


    def addSomeThings(self):
        t = PrivateThing(store=self.store, publicData=-self.i)
        self.i += 1
        self.things.append(t)
        self.bobThings.append(sharing.shareItem(
                t, toName=u'bob@example.com',
                interfaces=[IReadOnly]))
        self.aliceThings.append(sharing.shareItem(
                t,
                toName=u'alice@example.com',
                interfaces=[IPrivateThing]))


    def test_accessibilityQuery(self):
        """
        Ensure that asAccessibleTo returns only items actually accessible to
        the given role.
        """
        for i in range(10):
            self.addSomeThings()

        query = self.store.query(PrivateThing)
        aliceQuery = list(sharing.asAccessibleTo(self.alice, query))
        bobQuery = list(sharing.asAccessibleTo(self.bob, query))

        self.assertEqual(map(sharing.itemFromProxy, bobQuery),
                         map(lambda x: x.sharedItem, self.bobThings))
        self.assertEqual(map(sharing.itemFromProxy, aliceQuery),
                         map(lambda x: x.sharedItem, self.aliceThings))

        self.assertEqual([p.sharedInterfaces
                          for p in aliceQuery], [(IPrivateThing,)] * 10)
        self.assertEqual([p.sharedInterfaces
                          for p in bobQuery], [(IReadOnly,)] * 10)


    def test_sortOrdering(self):
        """
        Ensure that asAccessibleTo respects query sort order.
        """
        for i in range(10):
            self.addSomeThings()

        query = self.store.query(PrivateThing,
                                 sort=PrivateThing.publicData.ascending)
        # Sanity check.
        self.assertEquals([x.publicData for x in query], range(-9, 1, 1))
        bobQuery = list(sharing.asAccessibleTo(self.bob, query))
        self.assertEquals([x.retrieveSomeState() for x in bobQuery],
                          range(-9, 1, 1))
        query2 = self.store.query(PrivateThing,
                                  sort=PrivateThing.publicData.descending)
        # Sanity check #2
        self.assertEquals([x.publicData for x in query2], range(-9, 1, 1)[::-1])
        bobQuery2 = list(sharing.asAccessibleTo(self.bob, query2))
        self.assertEquals([x.retrieveSomeState() for x in bobQuery2], range(-9, 1, 1)[::-1])


    def test_limit(self):
        """
        Ensure that asAccessibleTo respects query limits.
        """
        for i in range(10):
            self.addSomeThings()

        query = self.store.query(PrivateThing, limit=3)
        bobQuery = list(sharing.asAccessibleTo(self.bob, query))
        self.assertEquals(len(bobQuery), 3)


    def test_limitEfficiency(self):
        """
        Verify that querying a limited number of shared items does not become
        slower as more items are shared.
        """
        zomg = QueryCounter(self.store)

        for i in range(10):
            self.addSomeThings()

        query = self.store.query(
            PrivateThing, limit=3, sort=PrivateThing.publicData.ascending)
        checkit = lambda : list(sharing.asAccessibleTo(self.bob, query))
        before = zomg.measure(checkit)

        for i in range(10):
            self.addSomeThings()

        after = zomg.measure(checkit)
        self.assertEquals(before, after)

    test_limitEfficiency.todo = (
        "An inherent limitation of the current implementation, we might be "
        "able to fix this by automatically duplicating colums or something.")
