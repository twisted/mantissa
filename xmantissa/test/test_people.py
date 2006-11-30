
from string import lowercase

from twisted.python.util import sibpath
from twisted.trial import unittest

from epsilon import extime
from epsilon.extime import Time

from axiom import store
from axiom.store import Store
from axiom.dependency import installOn

from xmantissa import people
from xmantissa.people import Organizer, Person, RealName
from xmantissa.webapp import PrivateApplication

class PeopleModelTestCase(unittest.TestCase):
    """
    Tests for the model parts of the person organizer code.
    """
    def setUp(self):
        """
        Create a bunch of people with names beginning with various letters.
        """
        self.store = Store()
        self.organizer = Organizer(store=self.store)

        letters = lowercase.decode('ascii')
        for firstPrefix, lastPrefix in zip(letters, reversed(letters)):
            first = firstPrefix + u'Alice'
            last = lastPrefix + u'Jones'
            person = Person(
                store=self.store,
                organizer=self.organizer,
                created=Time(),
                name=first + u' ' + last)
            RealName(
                store=self.store,
                person=person,
                first=first,
                last=last)

    def test_nameRestriction(self):
        """
        Test the query which loads Person items with last names in a particular
        alphabetic range.
        """
        for case in (unicode.upper, unicode.lower):
            people = list(self.store.query(Person, self.organizer.lastNamesBetweenComparison(case(u'a'), case(u'b'))))
            self.assertEqual(len(people), 1)
            self.assertEqual(people[0].name, u'zAlice aJones')


    def test_nameSorting(self):
        """
        Test the query which loads Person items orders them alphabetically by
        name.
        """
        people = list(self.store.query(
            Person,
            self.organizer.lastNamesBetweenComparison(u'm', u'p'),
            sort=self.organizer.lastNameOrder().ascending))
        self.assertEqual(len(people), 3)
        self.assertEqual(people[0].name, u'nAlice mJones')
        self.assertEqual(people[1].name, u'mAlice nJones')
        self.assertEqual(people[2].name, u'lAlice oJones')



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


    def test_getEmailAddresses(self):
        """
        Verify that getEmailAddresses yields the associated email address
        strings for a person.
        """
        s = store.Store()
        p = people.Person(store=s)
        people.EmailAddress(store=s, person=p, address=u'a@b.c')
        people.EmailAddress(store=s, person=p, address=u'c@d.e')
        # Ordering is undefined, so let's use a set.
        self.assertEquals(set(p.getEmailAddresses()),
                          set([u'a@b.c', u'c@d.e']))


    def test_getEmailAddress(self):
        """
        Verify that getEmailAddress yields the only associated email address
        for a person if it is the only one.
        """
        s = store.Store()
        p = people.Person(store=s)
        people.EmailAddress(store=s, person=p, address=u'a@b.c')
        self.assertEquals(p.getEmailAddress(), u'a@b.c')


    def test_getEmailAddresses(self):
        """
        Verify that getEmailAddress yields an associated email address
        for a person.
        """
        s = store.Store()
        p = people.Person(store=s)
        people.EmailAddress(store=s, person=p, address=u'a@b.c')
        people.EmailAddress(store=s, person=p, address=u'c@d.e')
        # XXX: I know this test is awful, but it's testing existing behavior,
        # which is random.  I could make it well defined while writing the
        # test, but it'd be just as wrong and just as not-configurable.  Let's
        # just get rid of this method and delete these tests soon.  -glyph
        self.failUnlessIn(p.getEmailAddress(), [u'a@b.c', u'c@d.e'])


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

    def testLinkToPerson(self):
        s = store.Store()

        privapp = PrivateApplication(store=s)
        installOn(privapp, s)

        o = people.Organizer(store=s)
        installOn(o, s)

        p = people.Person(store=s)

        self.assertEqual(o.linkToPerson(p),
                         (privapp.linkTo(o.storeID)
                             + '/'
                             + privapp.toWebID(p)))
