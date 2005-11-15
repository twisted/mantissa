
from twisted.trial import unittest

from epsilon import extime

from vertex import q2q

from axiom import store

from xmantissa import people

class PeopleTests(unittest.TestCase):
    def testPersonCreation(self):
        s = store.Store()
        o = people.Organizer(store=s)

        beforeCreation = extime.Time()
        p = o.personByAddress(q2q.Q2QAddress('example.com', 'testuser'))
        afterCreation = extime.Time()

        self.assertEquals(p.address, u'testuser@example.com')
        self.failUnless(
            beforeCreation <= p.created <= afterCreation,
            "not (%r <= %r <= %r)" % (beforeCreation, p.created, afterCreation))

        # Make sure people from that organizer don't collide with
        # people from a different organizer
        another = people.Organizer(store=s)
        q = another.personByAddress(q2q.Q2QAddress('example.com', 'testuser'))
        self.failIfIdentical(p, q)
        self.assertEquals(q.address, u'testuser@example.com')

        # And make sure people within a single Organizer don't trample
        # on each other.
        notQ = another.personByAddress(q2q.Q2QAddress('example.com', 'nottestuser'))
        self.failIfIdentical(q, notQ)
        self.assertEquals(q.address, u'testuser@example.com')
        self.assertEquals(notQ.address, u'nottestuser@example.com')

        alsoNotQ = another.personByAddress(q2q.Q2QAddress('not.example.com', 'testuser'))
        self.failIfIdentical(q, alsoNotQ)
        self.failIfIdentical(notQ, alsoNotQ)
        self.assertEquals(notQ.address, u'nottestuser@example.com')
        self.assertEquals(alsoNotQ.address, u'testuser@not.example.com')

    def testPersonRetrieval(self):
        s = store.Store()
        o = people.Organizer(store=s)

        addr = q2q.Q2QAddress('example.com', 'testuser')
        firstPerson = o.personByAddress(addr)
        self.assertIdentical(firstPerson, o.personByAddress(addr))
