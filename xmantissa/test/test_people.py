
"""
Tests for L{xmantissa.people}.
"""

from xml.dom.minidom import parseString

from zope.interface import implements

from string import lowercase

from twisted.python.util import sibpath
from twisted.python.reflect import qual
from twisted.trial import unittest

from nevow.loaders import stan
from nevow.tags import div, slot
from nevow.flat import flatten

from epsilon import extime
from epsilon.extime import Time

from axiom.store import Store
from axiom.dependency import installOn, installedOn
from axiom.item import Item
from axiom.attributes import inmemory, text

from xmantissa.people import (Organizer, Person, RealName, EmailAddress,
                              AddPersonFragment, Mugshot, addContactInfoType,
                              contactInfoItemTypeFromClassName,
                              _CONTACT_INFO_ITEM_TYPES, ContactInfoFragment,
                              PhoneNumber, setIconURLForContactInfoType,
                              iconURLForContactInfoType, _CONTACT_INFO_ICON_URLS,
                              AddPerson)
from xmantissa.webapp import PrivateApplication
from xmantissa.liveform import FORM_INPUT, Parameter
from xmantissa.ixmantissa import IOrganizerPlugin, IContactType


class StubOrganizerPlugin(Item):
    """
    Organizer powerup which records which people are created and gives back
    canned responses to method calls.
    """
    value = text(
        doc="""
        Mandatory attribute.
        """)

    createdPeople = inmemory(
        doc="""
        A list of all L{People} created since this item was last loaded from
        the database.
        """)

    contactTypes = inmemory(
        doc="""
        A list of L{IContact} implementors to return from L{getContactTypes}.
        """)

    def activate(self):
        """
        Initialize C{createdPeople} to an empty list.
        """
        self.createdPeople = []


    def personCreated(self, person):
        """
        Record the creation of a L{Person}.
        """
        self.createdPeople.append(person)


    def getContactTypes(self):
        """
        Return the contact types list this item was constructed with.
        """
        return self.contactTypes



class StubContactType(object):
    """
    Behaviorless contact type implementation used for tests.

    @ivar creationForm: The object which will be returned from L{getCreationForm}.
    @ivar createdContacts: A list of tuples of the arguments passed to
        C{createContactItem}.

    """
    implements(IContactType)

    def __init__(self, creationForm):
        self.creationForm = creationForm
        self.createdContacts = []


    def uniqueIdentifier(self):
        """
        Return the L{qual} of this class.
        """
        return qual(self.__class__)


    def getCreationForm(self):
        """
        Return an object which is supposed to be a form for creating a new
        instance of this contact type.
        """
        return self.creationForm


    def createContactItem(self, person, argument):
        """
        Record an attempt to create a new contact item of this type for the
        given person.
        """
        self.createdContacts.append((person, argument))


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


    def test_createPerson(self):
        """
        L{Organizer.createPerson} should instantiate and return a L{Person} item
        with the specified nickname, a reference to the creating L{Organizer},
        and a creation timestamp set to the current time.
        """
        nickname = u'test person'
        beforeCreation = extime.Time()
        person = self.organizer.createPerson(nickname)
        afterCreation = extime.Time()
        self.assertEqual(person.name, nickname)
        self.assertIdentical(person.organizer, self.organizer)
        self.assertTrue(beforeCreation <= person.created <= afterCreation)


    def test_getOrganizerPlugins(self):
        """
        L{Organizer.getOrganizerPlugins} should return an iterator of the
        installed L{IOrganizerPlugin} powerups.
        """
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        self.assertEqual(
            list(self.organizer.getOrganizerPlugins()), [observer])


    def test_createPersonNotifiesPlugins(self):
        """
        L{Organizer.createPerson} should call L{personCreated} on all
        L{IOrganizerPlugin} powerups on the store.
        """
        nickname = u'test person'
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        person = self.organizer.createPerson(nickname)
        self.assertEqual(observer.createdPeople, [person])


    def test_organizerPluginWithoutPersonCreated(self):
        """
        L{IOrganizerPlugin} powerups which don't have the C{personCreated}
        method should not cause problems with L{Organizer.createPerson} (The
        method was added after the interface was initially defined so there may
        be implementations which have not yet been updated).
        """
        class OldOrganizerPlugin(object):
            """
            An L{IOrganizerPlugin} which does not implement C{getContactTypes}.
            """
        getOrganizerPlugins = Organizer.getOrganizerPlugins.im_func
        plugins = [OldOrganizerPlugin(), StubOrganizerPlugin(createdPeople=[])]
        Organizer.getOrganizerPlugins = lambda self: plugins
        try:
            organizer = Organizer()
            person = organizer.createPerson(u'nickname')
        finally:
            Organizer.getOrganizerPlugins = getOrganizerPlugins

        self.assertEqual(plugins[1].createdPeople, [person])


    def test_getContactTypes(self):
        """
        L{Organizer.getContactTypes} should return an iterable of all the
        L{IContactType} plugins available on the store.
        """
        firstContactTypes = [object(), object()]
        firstContactPowerup = StubOrganizerPlugin(
            store=self.store, contactTypes=firstContactTypes)
        self.store.powerUp(
            firstContactPowerup, IOrganizerPlugin, priority=1)

        secondContactTypes = [object()]
        secondContactPowerup = StubOrganizerPlugin(
            store=self.store, contactTypes=secondContactTypes)
        self.store.powerUp(
            secondContactPowerup, IOrganizerPlugin, priority=0)

        self.assertEqual(
            list(self.organizer.getContactTypes()),
            firstContactTypes + secondContactTypes)


    def test_organizerPluginWithoutContactTypes(self):
        """
        L{IOrganizerPlugin} powerups which don't have the C{getContactTypes}
        method should not cause problems with L{Organizer.getContactTypes} (The
        method was added after the interface was initially defined so there may
        be implementations which have not yet been updated).
        """
        class OldOrganizerPlugin(object):
            """
            An L{IOrganizerPlugin} which does not implement C{getContactTypes}.
            """
        getOrganizerPlugins = Organizer.getOrganizerPlugins.im_func
        Organizer.getOrganizerPlugins = lambda self: [OldOrganizerPlugin()]
        try:
            organizer = Organizer()
            contactTypes = list(organizer.getContactTypes())
        finally:
            Organizer.getOrganizerPlugins = getOrganizerPlugins

        self.assertEqual(contactTypes, [])


    def test_getContactCreationParameters(self):
        """
        L{Organizer.getContactCreationParameters} should return a list
        containing C{FORM_INPUT} parameters for each contact type available in
        the system.
        """
        contactForm = object()
        contactTypes = [StubContactType(contactForm)]
        contactPowerup = StubOrganizerPlugin(
            store=self.store, contactTypes=contactTypes)
        self.store.powerUp(contactPowerup, IOrganizerPlugin)

        parameters = list(self.organizer.getContactCreationParameters())
        self.assertEqual(len(parameters), 1)
        self.assertTrue(isinstance(parameters[0], Parameter))
        self.assertEqual(parameters[0].name, qual(StubContactType))
        self.assertEqual(parameters[0].type, FORM_INPUT)
        self.assertIdentical(parameters[0].coercer, contactForm)



class POBox(Item):
    number = text()



class PeopleTests(unittest.TestCase):
    def testPersonCreation(self):
        s = Store()
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
        s = Store()
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
        s = Store()
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
        s = Store()
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
        s = Store()
        p = Person(store=s)
        EmailAddress(store=s, person=p, address=u'a@b.c')
        self.assertEquals(p.getEmailAddress(), u'a@b.c')

    def testPersonRetrieval(self):
        s = Store()
        o = Organizer(store=s)

        name = u'testuser'
        firstPerson = o.personByName(name)
        self.assertIdentical(firstPerson, o.personByName(name))


    def test_addPersonParameters(self):
        """
        L{AddPersonFragment.render_addPersonForm} should return a L{LiveForm}
        with several fixed parameters and any parameters from available
        powerups.
        """
        store = Store()
        adder = AddPerson(store=store)
        installOn(adder, store)

        addPersonFrag = AddPersonFragment(adder)
        addPersonForm = addPersonFrag.render_addPersonForm(None, None)
        self.assertEqual(len(addPersonForm.parameters), 4)

        contactTypes = [StubContactType(object())]
        observer = StubOrganizerPlugin(
            store=store, contactTypes=contactTypes)
        store.powerUp(observer, IOrganizerPlugin)

        addPersonForm = addPersonFrag.render_addPersonForm(None, None)
        self.assertEqual(len(addPersonForm.parameters), 5)


    def test_addPersonWithContactItems(self):
        """
        L{AddPersonFragment.addPerson} should give the L{IContactType} plugins
        their information from the form submission.
        """
        store = Store()
        adder = AddPerson(store=store)
        installOn(adder, store)

        creationForm = object()
        contactType = StubContactType(creationForm)
        observer = StubOrganizerPlugin(
            store=store, contactTypes=[contactType])
        store.powerUp(observer, IOrganizerPlugin)

        addPersonFragment = AddPersonFragment(adder)

        argument = object()
        addPersonFragment.addPerson(
            u'nickname', u'firstname', u'lastname', u'email@example.com',
            **{contactType.uniqueIdentifier(): argument})

        person = store.findUnique(Person)

        self.assertEqual(contactType.createdContacts, [(person, argument)])


    def testPersonCreation2(self):
        store = Store()
        organizer = Organizer(store=store)
        adder = AddPerson(store=store, organizer=organizer)

        addPersonFrag = AddPersonFragment(adder)
        addPersonFrag.addPerson(u'Captain P.', u'Jean-Luc', u'Picard', u'jlp@starship.enterprise')

        person = store.findUnique(Person)
        self.assertEquals(person.name, 'Captain P.')

        email = store.findUnique(EmailAddress, EmailAddress.person == person)

        self.assertEquals(email.address, 'jlp@starship.enterprise')

        rn = store.findUnique(RealName, RealName.person == person)

        self.assertEquals(rn.first + ' ' + rn.last, 'Jean-Luc Picard')


    def test_doublePersonCreation(self):
        """
        Test that L{AddPersonFragment.addPerson} raises a ValueError when it is
        called twice with the same email address. This ensures that
        L{Organizer.personByEmailAddress} can always return a unique person.
        """
        # make ourselves an AddPersonFragment
        store = Store()
        organizer = Organizer(store=store)
        adder = AddPerson(store=store, organizer=organizer)
        fragment = AddPersonFragment(adder)

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

        s = Store(self.mktemp())

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
        s = Store()

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
