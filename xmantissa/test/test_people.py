
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
        p = o.personByName(u'testuser')
        afterCreation = extime.Time()

        self.assertEquals(p.name, u'testuser')
        self.failUnless(
            beforeCreation <= p.created <= afterCreation,
            "not (%r <= %r <= %r)" % (beforeCreation, p.created, afterCreation))

        # Make sure people from that organizer don't collide with
        # people from a different organizer
        another = people.Organizer(store=s)
        q = another.personByName(u'testuser')
        self.failIfIdentical(p, q)
        self.assertEquals(q.name, u'testuser')

        # And make sure people within a single Organizer don't trample
        # on each other.
        notQ = another.personByName(u'nottestuser')
        self.failIfIdentical(q, notQ)
        self.assertEquals(q.name, u'testuser')
        self.assertEquals(notQ.name, u'nottestuser')

    def testPersonRetrieval(self):
        s = store.Store()
        o = people.Organizer(store=s)

        name = u'testuser'
        firstPerson = o.personByName(name)
        self.assertIdentical(firstPerson, o.personByName(name))

    def testPersonCreation2(self):
        s = store.Store()
        o = people.Organizer(store=s)

        class original:
            store = s

        addPersonFrag = people.AddPersonFragment(original)
        addPersonFrag.addPerson(u'Captain P.', u'Jean-Luc', u'Picard', u'jlp@starship.enterprise')

        person = s.findUnique(people.Person)
        self.assertEquals(person.name, 'Captain P.')

        email = s.findUnique(people.EmailAddress, people.EmailAddress.person == person)

        self.assertEquals(email.address, 'jlp@starship.enterprise')
        self.assertEquals(email.type, 'default')

        rn = s.findUnique(people.RealName, people.RealName.person == person)

        self.assertEquals(rn.first + ' ' + rn.last, 'Jean-Luc Picard')
