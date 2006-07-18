from twisted.python.util import sibpath
from twisted.trial import unittest

from epsilon import extime

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

        rn = s.findUnique(people.RealName, people.RealName.person == person)

        self.assertEquals(rn.first + ' ' + rn.last, 'Jean-Luc Picard')

    def testMugshot(self):
        """
        Create a Mugshot item, check that it thumbnails it's image correctly
        """

        try:
            from PIL import Image
        except ImportError:
            raise unittest.SkipTest('PIL is not available')

        s = store.Store(self.mktemp())

        p = people.Person(store=s, name=u'Bob')

        imgpath = sibpath(__file__, 'resources/square.png')
        imgfile = file(imgpath)

        m = people.Mugshot.fromFile(p, imgfile, u'png')

        self.assertEqual(m.type, 'image/png')
        self.assertIdentical(m.person,  p)

        self.failUnless(m.body)
        self.failUnless(m.smallerBody)

        img = Image.open(m.body.open())
        self.assertEqual(img.size, (m.size, m.size))

        smallerimg = Image.open(m.smallerBody.open())
        self.assertEqual(smallerimg.size, (m.smallerSize, m.smallerSize))
