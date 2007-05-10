
from xml.dom.minidom import parseString

from string import lowercase

from twisted.python.util import sibpath
from twisted.trial import unittest

from nevow.loaders import stan
from nevow.tags import div, slot
from nevow.flat import flatten

from epsilon import extime
from epsilon.extime import Time

from axiom import store
from axiom.store import Store
from axiom.dependency import installOn, installedOn
from axiom.item import Item
from axiom.attributes import text

from xmantissa.people import (Organizer, Person, RealName, EmailAddress,
                              AddPersonFragment, Mugshot, addContactInfoType,
                              contactInfoItemTypeFromClassName,
                              _CONTACT_INFO_ITEM_TYPES, ContactInfoFragment,
                              PhoneNumber, setIconURLForContactInfoType,
                              iconURLForContactInfoType, _CONTACT_INFO_ICON_URLS)
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



class POBox(Item):
    number = text()



class PeopleTests(unittest.TestCase):
    def testPersonCreation(self):
        s = store.Store()
        o = Organizer(store=s)

        beforeCreation = extime.Time()
        p = o.personByName(u'testuser')
        afterCreation = extime.Time()

        self.assertEquals(p.name, u'testuser')
        self.failUnless(
            beforeCreation <= p.created <= afterCreation,
            "not (%r <= %r <= %r)" % (beforeCreation, p.created, afterCreation))

        # Make sure people from that organizer don't collide with
        # people from a different organizer
        another = Organizer(store=s)
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
        p = Person(store=s)
        EmailAddress(store=s, person=p, address=u'a@b.c')
        EmailAddress(store=s, person=p, address=u'c@d.e')
        # Ordering is undefined, so let's use a set.
        self.assertEquals(set(p.getEmailAddresses()),
                          set([u'a@b.c', u'c@d.e']))


    def test_createContactInfoItem(self):
        """
        Verify a new contact info item can be created using
        L{Person.createContactInfoItem} and that newly created contact
        info items are installed on their person item.
        """
        email = u'username@hostname'
        s = store.Store()
        person = Person(store=s)
        person.createContactInfoItem(EmailAddress, 'address', email)
        contacts = list(s.query(EmailAddress))
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0].person, person)
        self.assertEqual(contacts[0].address, email)
        self.assertEqual(installedOn(contacts[0]), person)


    def test_findContactInfoItem(self):
        """
        Verify an existing contact info item can be found with
        L{Person.findContactInfoItem}.
        """
        email = u'username@hostname'
        s = store.Store()
        alice = Person(store=s)
        bob = Person(store=s)
        emailObj = EmailAddress(store=s, person=alice, address=email)
        self.assertEqual(alice.findContactInfoItem(EmailAddress, 'address', email), emailObj)
        self.assertEqual(bob.findContactInfoItem(EmailAddress, 'address', email), None)


    def test_editContactInfoItem(self):
        """
        Verify that L{Person.editContactInfoItem} changes the value of
        the contact info item's attribute in the database.
        """
        oldEmail = u'username@hostname'
        newEmail = u'notusername@hostname'
        store = Store()

        alice = Person(store=store)
        bob = Person(store=store)

        aliceEmail = EmailAddress(store=store, person=alice, address=oldEmail)
        bobEmail = EmailAddress(store=store, person=bob, address=oldEmail)

        alice.editContactInfoItem(
            EmailAddress, 'address', oldEmail, newEmail)
        self.assertEqual(aliceEmail.address, newEmail)
        self.assertEqual(bobEmail.address, oldEmail)


    def test_deleteContactInfoItem(self):
        """
        Verify that L{Person.deleteContactInfoItem} removes the
        matching contact info item from the database.
        """
        email = u'username@hostname'

        store = Store()

        alice = Person(store=store)
        bob = Person(store=store)
        aliceEmail = EmailAddress(store=store, person=alice, address=email)
        bobEmail = EmailAddress(store=store, person=bob, address=email)

        alice.deleteContactInfoItem(
            EmailAddress, 'address', email)

        emails = list(store.query(EmailAddress))
        self.assertEqual(len(emails), 1)
        self.assertIdentical(emails[0], bobEmail)


    def test_getContactInfoItems(self):
        """
        Verify that L{Person.getContactInfoItems} returns the values
        of all contact info items that belong to it.
        """
        store = Store()

        alice = Person(store=store)
        bob = Person(store=store)
        aliceEmail1 = EmailAddress(store=store, person=alice, address=u'alice1@host')
        aliceEmail2 = EmailAddress(store=store, person=alice, address=u'alice2@host')
        bobEmail = EmailAddress(store=store, person=bob, address=u'bob@host')

        self.assertEqual(
            list(sorted(alice.getContactInfoItems(EmailAddress, 'address'))),
            ['alice1@host', 'alice2@host'])
        self.assertEqual(
            list(bob.getContactInfoItems(EmailAddress, 'address')),
            ['bob@host'])


    def test_contactInfoItemTypeFromClassName(self):
        """
        Test that we can register a new contact info item type and
        then find it by class name with
        L{contactInfoItemTypeFromClassName}
        """
        addContactInfoType(POBox, 'number')
        try:
            (itemClass, attr) = contactInfoItemTypeFromClassName(POBox.__name__)
            self.assertIdentical(itemClass, POBox)
            self.assertEqual(attr, 'number')
        finally:
            _CONTACT_INFO_ITEM_TYPES.remove((POBox, 'number'))


    def test_setIconURLForContactInfoType(self):
        """
        Test that we can register an URL for an icon for a contact
        info item type and then find it by type with
        L{iconURLForContactInfoType}.
        """
        url = '/foo/bar/pobox.png'
        setIconURLForContactInfoType(POBox, url)
        try:
            self.assertEqual(iconURLForContactInfoType(POBox), url)
        finally:
            del _CONTACT_INFO_ICON_URLS[POBox]


    def test_getEmailAddress(self):
        """
        Verify that getEmailAddress yields the only associated email address
        for a person if it is the only one.
        """
        s = store.Store()
        p = Person(store=s)
        EmailAddress(store=s, person=p, address=u'a@b.c')
        self.assertEquals(p.getEmailAddress(), u'a@b.c')

    def testPersonRetrieval(self):
        s = store.Store()
        o = Organizer(store=s)

        name = u'testuser'
        firstPerson = o.personByName(name)
        self.assertIdentical(firstPerson, o.personByName(name))

    def testPersonCreation2(self):
        s = store.Store()
        o = Organizer(store=s)

        class original:
            store = s

        addPersonFrag = AddPersonFragment(original)
        addPersonFrag.addPerson(u'Captain P.', u'Jean-Luc', u'Picard', u'jlp@starship.enterprise')

        person = s.findUnique(Person)
        self.assertEquals(person.name, 'Captain P.')

        email = s.findUnique(EmailAddress, EmailAddress.person == person)

        self.assertEquals(email.address, 'jlp@starship.enterprise')

        rn = s.findUnique(RealName, RealName.person == person)

        self.assertEquals(rn.first + ' ' + rn.last, 'Jean-Luc Picard')


    def test_doublePersonCreation(self):
        """
        Test that L{AddPersonFragment.addPerson} raises a ValueError when it is
        called twice with the same email address. This ensures that
        L{Organizer.personByEmailAddress} can always return a unique person.
        """
        # make ourselves an AddPersonFragment
        s = store.Store()
        o = Organizer(store=s)
        class original(object):
            store = s
        fragment = AddPersonFragment(original)

        address = u'test@example.com'
        fragment.addPerson(u'flast', u'First', u'Last', address)
        self.assertRaises(ValueError, fragment.addPerson, u'foobar', u'Foo',
                          u'Bar', address)


    def testMugshot(self):
        """
        Create a Mugshot item, check that it thumbnails it's image correctly
        """

        try:
            from PIL import Image
        except ImportError:
            raise unittest.SkipTest('PIL is not available')

        s = store.Store(self.mktemp())

        p = Person(store=s, name=u'Bob')

        imgpath = sibpath(__file__, 'resources/square.png')
        imgfile = file(imgpath)

        m = Mugshot.fromFile(p, imgfile, u'png')

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

        o = Organizer(store=s)
        installOn(o, s)

        p = Person(store=s)

        self.assertEqual(o.linkToPerson(p),
                         (privapp.linkTo(o.storeID)
                             + '/'
                             + privapp.toWebID(p)))



class StubPerson(object):
    """
    Stub implementation of L{Person} used for testing.

    @ivar contactItems: A list of three-tuples of the arguments passed to
    createContactInfoItem.
    """
    def __init__(self, contactItems):
        self.contactItems = contactItems


    def createContactInfoItem(self, cls, attr, value):
        self.contactItems.append((cls, attr, value))
        # maybe not so great!
        s = store.Store()
        return cls(store=s, person=s, **{attr: value})



class ContactInfoViewTests(unittest.TestCase):
    """
    Tests for L{ContactInfoFragment}.
    """
    def test_createContactInfoItem(self):
        """
        Verify that L{ContactInfoFragment.createContactInfoItem} calls
        C{createContactInfoItem} with the correct arguments on the object it
        wraps.
        """
        contactItems = []
        person = StubPerson(contactItems)
        fragment = ContactInfoFragment(
            person,
            stan(div(pattern='contact-info-item')[slot('value')]))
        fragment.createContactInfoItem(u'PhoneNumber', u'123-456-7890')
        self.assertEqual(
            contactItems, [(PhoneNumber, 'number', u'123-456-7890')])


    def test_createContactInfoItemReturnsFragment(self):
        """
        Verify that L{ContactInfoFragment.createContactInfoItem} returns a
        L{ContactInfoFragment} with the proper parent and docFactory.
        """
        person = StubPerson([])
        fragment = ContactInfoFragment(
            person,
            stan(div(pattern='contact-info-item')[slot('value')]))
        result = fragment.createContactInfoItem(
            u'PhoneNumber', u'123-456-7890')
        self.failUnless(isinstance(result, ContactInfoFragment))
        self.assertEqual(
            flatten(result.docFactory.load()),
            '<div>123-456-7890</div>')
        self.assertIdentical(result.fragmentParent, fragment)


    def test_contactInfoSummarySection(self):
        """
        Test that the renderer for a single section of the contact
        info summary points to the correct icon URL for that section's
        item type.
        """
        sectionPattern = div(pattern='contact-info-section')[
            div[slot(name='type')],
            div[slot(name='icon-path')],
            slot(name='items')]
        itemPattern = div(pattern='contact-info-item')[
            slot(name='value')]

        person = StubPerson([])
        fragment = ContactInfoFragment(
            person,
            stan(div[sectionPattern, itemPattern]))

        url = '/foo/bar/pobox.png'
        number = u'1234'
        setIconURLForContactInfoType(POBox, url)
        result = fragment._renderSection(POBox, [number])
        markup = flatten(result)
        document = parseString(markup)
        ele = document.documentElement
        self.assertEqual(ele.tagName, 'div')
        self.assertEqual(ele.childNodes[0].tagName, 'div')
        self.assertEqual(ele.childNodes[0].childNodes[0].nodeValue, 'POBox')
        self.assertEqual(ele.childNodes[1].tagName, 'div')
        self.assertEqual(ele.childNodes[1].childNodes[0].nodeValue, url)
        self.assertEqual(ele.childNodes[2].tagName, 'div')
        self.assertEqual(ele.childNodes[2].childNodes[0].nodeValue, number)
