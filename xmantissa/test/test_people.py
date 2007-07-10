
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
from nevow.athena import expose
from nevow.page import renderer
from nevow.testutil import FakeRequest

from epsilon import extime
from epsilon.extime import Time
from epsilon.structlike import record

from axiom.store import Store
from axiom.dependency import installOn, installedOn
from axiom.item import Item
from axiom.attributes import inmemory, text

from xmantissa.test.rendertools import renderLiveFragment
from xmantissa.people import (
    Organizer, Person, RealName, EmailAddress, AddPersonFragment, Mugshot,
    addContactInfoType, contactInfoItemTypeFromClassName,
    _CONTACT_INFO_ITEM_TYPES, ContactInfoFragment, PhoneNumber,
    setIconURLForContactInfoType, iconURLForContactInfoType,
    _CONTACT_INFO_ICON_URLS, PersonScrollingFragment,
    PersonNameColumn, OrganizerFragment, EditPersonView, NameContactType,
    BaseContactType, EmailContactType, _normalizeWhitespace, PostalAddress,
    PostalContactType)

from xmantissa.webapp import PrivateApplication
from xmantissa.liveform import TEXT_INPUT, FORM_INPUT, Parameter, LiveForm
from xmantissa.ixmantissa import IOrganizerPlugin, IContactType, IWebTranslator



class WhitespaceNormalizationTests(unittest.TestCase):
    """
    Tests for L{_normalizeWhitespace}.
    """
    def test_empty(self):
        """
        L{_normalizeWhitespace} should return an empty string for an empty
        string.
        """
        self.assertEqual(_normalizeWhitespace(u''), u'')


    def test_spaces(self):
        """
        L{_normalizeWhitespace} should return an empty string for a string
        consisting only of whitespace.
        """
        self.assertEqual(_normalizeWhitespace(u' \t\v'), u'')


    def test_leadingSpace(self):
        """
        L{_normalizeWhitespace} should remove leading whitespace in its result.
        """
        self.assertEqual(_normalizeWhitespace(u' x'), u'x')


    def test_trailingSpace(self):
        """
        L{_normalizeWhitespace} should remove trailing whitespace in its result.
        """
        self.assertEqual(_normalizeWhitespace(u'x '), u'x')


    def test_multipleSpace(self):
        """
        L{_normalizeWhitespace} should replace occurrences of contiguous
        whitespace characters with a single space character.
        """
        self.assertEqual(_normalizeWhitespace(u'x  x'), u'x x')



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

    createdContactItems = inmemory(
        doc="""
        A list of contact items created since this item was last loaded from
        the database.
        """)

    def activate(self):
        """
        Initialize C{createdPeople} and C{createdContactItems} to empty lists.
        """
        self.createdPeople = []
        self.createdContactItems = []


    def personCreated(self, person):
        """
        Record the creation of a L{Person}.
        """
        self.createdPeople.append(person)


    def contactItemCreated(self, contactItem):
        """
        Record the creation of a contact item.
        """
        self.createdContactItems.append(contactItem)


    def getContactTypes(self):
        """
        Return the contact types list this item was constructed with.
        """
        return self.contactTypes



class StubContactType(object):
    """
    Behaviorless contact type implementation used for tests.

    @ivar creationForm: The object which will be returned from
        L{getCreationForm}.
    @ivar createdContacts: A list of tuples of the arguments passed to
        C{createContactItem}.
    @ivar editorialForm: The object which will be returned from
        L{getEditorialForm}.
    @ivar editedContacts: A list of the contact items passed to
        L{getEditorialForm}.
    @ivar contactItems: The list of objects which will be returned from
        L{getContactItems}.
    @ivar queriedPeople: A list of the person items passed to
        L{getContactItems}.
    @ivar editedContacts: A list of two-tuples of the arguments passed to
        L{editContactItem}.
    @ivar createContactItems: A boolean indicating whether C{createContactItem}
        will return an object pretending to be a new contact item (C{True}) or
        C{None} to indicate no contact item was created (C{False}).
    """
    implements(IContactType)

    def __init__(self, creationForm, editorialForm, contactItems,
                 createContactItems=True):
        self.creationForm = creationForm
        self.createdContacts = []
        self.editorialForm = editorialForm
        self.editedContacts = []
        self.contactItems = contactItems
        self.queriedPeople = []
        self.editedContacts = []
        self.createContactItems = createContactItems


    def uniqueIdentifier(self):
        """
        Return the L{qual} of this class.
        """
        return qual(self.__class__).decode('ascii')


    def getCreationForm(self):
        """
        Return an object which is supposed to be a form for creating a new
        instance of this contact type.
        """
        return self.creationForm


    def getEditorialForm(self, contact):
        """
        Return an object which is supposed to be a form for editing an existing
        instance of this contact type and record the contact object which was
        passed in.
        """
        self.editedContacts.append(contact)
        return self.editorialForm


    def createContactItem(self, person, **parameters):
        """
        Record an attempt to create a new contact item of this type for the
        given person.
        """
        contactItem = (person, parameters)
        self.createdContacts.append(contactItem)
        if self.createContactItems:
            return contactItem
        return None


    def getContactItems(self, person):
        """
        Return C{self.contactItems} and record the person item passed in.
        """
        self.queriedPeople.append(person)
        return self.contactItems


    def editContactItem(self, contact, **changes):
        """
        Record an attempt to edit the details of a contact item.
        """
        self.editedContacts.append((contact, changes))



class BaseContactTests(unittest.TestCase):
    """
    Tests for the utility base-class L{BaseContactType}.
    """
    def test_uniqueIdentifier(self):
        """
        L{BaseContactType.uniqueIdentifier} should return a unicode string
        giving the fully-qualifed Python name of the class of the instance it
        is called on.
        """
        class Dummy(BaseContactType):
            pass
        identifier = Dummy().uniqueIdentifier()
        self.assertTrue(isinstance(identifier, unicode))
        self.assertEqual(identifier, __name__ + '.' + Dummy.__name__)


    def test_getCreationForm(self):
        """
        L{BaseContactType.getCreationForm} should return a L{LiveForm} with the
        parameters specified by C{getParameters}.
        """
        contacts = []
        params = object()
        class Stub(BaseContactType):
            def getParameters(self, contact):
                contacts.append(contact)
                return params
        form = Stub().getCreationForm()
        self.assertTrue(isinstance(form, LiveForm))
        self.assertEqual(contacts, [None])
        self.assertIdentical(form.parameters, params)

        params = dict(a='b', c='d')
        self.assertEqual(form.callable(**params), params)


    def test_getEditorialForm(self):
        """
        L{BaseContactType.getEditorialForm} should return an L{LiveForm} with
        the parameters specified by L{getParameters}.
        """
        contact = object()
        contacts = []
        params = object()
        class Stub(BaseContactType):
            def getParameters(self, contact):
                contacts.append(contact)
                return params
        form = Stub().getEditorialForm(contact)
        self.assertTrue(isinstance(form, LiveForm))
        self.assertEqual(contacts, [contact])
        self.assertIdentical(form.parameters, params)

        params = dict(a='b', c='d')
        self.assertEqual(form.callable(**params), params)


class EmailAddressTests(unittest.TestCase):
    """
    Tests for L{EmailAddress}.
    """
    def test_deletedWithPerson(self):
        """
        An L{EmailAddress} should be deleted when the L{Person} it is
        associated with is deleted.
        """
        store = Store()
        person = Person(store=store)
        email = EmailAddress(
            store=store, person=person, address=u'testuser@example.com')
        person.deleteFromStore()
        self.assertEqual(store.query(EmailAddress).count(), 0)



class PostalAddressTests(unittest.TestCase):
    """
    Tests for L{PostalAddress}.
    """
    def test_deletedWithPerson(self):
        """
        A L{PostalAddress} should be deleted when the L{Person} it is
        associated with is deleted.
        """
        store = Store()
        person = Person(store=store)
        address = PostalAddress(
            store=store, person=person, address=u'123 Street Rd')
        person.deleteFromStore()
        self.assertEqual(store.query(PostalAddress).count(), 0)



class RealNameTests(unittest.TestCase):
    """
    Tests for L{RealName}.
    """
    def test_noFirstNameDisplay(self):
        """
        L{RealName.display} should be a unicode string giving the last name if
        there is only a last name.
        """
        store = Store()
        person = Person(store=store)
        realName = RealName(store=store, person=person, last=u'Last')
        self.assertTrue(isinstance(realName.display, unicode))
        self.assertEqual(realName.display, u'Last')


    def test_noLastNameDisplay(self):
        """
        L{RealName.display} should be a unicode string giving the first name if
        there is only a first name.
        """
        store = Store()
        person = Person(store=store)
        realName = RealName(store=store, person=person, first=u'First')
        self.assertTrue(isinstance(realName.display, unicode))
        self.assertEqual(realName.display, u'First')


    def test_noNamesDisplay(self):
        """
        L{RealName.display} should be an empty unicode string if is no first or
        last name.
        """
        store = Store()
        person = Person(store=store)
        realName = RealName(store=store, person=person)
        self.assertTrue(isinstance(realName.display, unicode))
        self.assertEqual(realName.display, u'')


    def test_deletedWithPerson(self):
        """
        A L{RealName} should be deleted when the L{Person} it is associated
        with is deleted.
        """
        store = Store()
        person = Person(store=store)
        realName = RealName(store=store, person=person)
        person.deleteFromStore()
        self.assertEqual(store.query(RealName).count(), 0)



class ContactTestsMixin(object):
    """
    Define tests common to different L{IContactType} implementations.

    Mix this in to a L{unittest.TestCase} and bind C{self.contactType} to the
    L{IContactType} provider in C{setUp}.
    """
    def test_providesContactType(self):
        """
        C{self.contactType} should provide L{IContactType}.
        """
        self.assertTrue(IContactType.providedBy(self.contactType))

        # I would really like to use verifyObject here.  However, the
        # **parameters in IContactType.editContactItem causes it to fail for
        # reasonably conformant implementations.
        # self.assertTrue(verifyObject(IContactType, self.contactType))



class NameContactTests(unittest.TestCase, ContactTestsMixin):
    """
    Tests for the naming parameters defined by L{NameContactType}.
    """
    def setUp(self):
        """
        Create a L{NameContactType} for use by the tests.
        """
        self.contactType = NameContactType()


    def test_organizerIncludesIt(self):
        """
        L{Organizer.getContactTypes} should include an instance of
        L{NameContactType} in its return value.
        """
        store = Store()
        organizer = Organizer(store=store)
        self.assertTrue([
                contactType
                for contactType
                in organizer.getContactTypes()
                if isinstance(contactType, NameContactType)])


    def test_createContactItem(self):
        """
        L{NameContactType.createContactItem} should create a L{RealName} with
        the supplied values.
        """
        store = Store()
        person = Person(store=store)
        contactType = NameContactType()
        contactItem = contactType.createContactItem(
            person, firstname=u'First', lastname=u'Last')
        names = list(store.query(RealName))
        self.assertEqual(names, [contactItem])
        self.assertEqual(contactItem.first, u'First')
        self.assertEqual(contactItem.last, u'Last')
        self.assertIdentical(contactItem.person, person)


    def test_createContactItemWithoutNames(self):
        """
        L{NameContactType.createContactItem} should create no L{RealName} item
        if called with empty strings.
        """
        store = Store()
        person = Person(store=store)
        contactType = NameContactType()
        contactItem = contactType.createContactItem(
            person, firstname=u'', lastname=u'')
        self.assertIdentical(contactItem, None)
        self.assertEqual(list(store.query(RealName)), [])


    def test_editContactItem(self):
        """
        L{NameContactType.editContactItem} should update the first and last
        name fields of the L{RealName} it is passed.
        """
        class StubRealName(object):
            pass
        realName = StubRealName()
        contactType = NameContactType()
        contactType.editContactItem(
            realName, firstname=u'First', lastname=u'Last')
        self.assertEqual(realName.first, u'First')
        self.assertEqual(realName.last, u'Last')


    def test_getParameters(self):
        """
        L{NameContactType.getParameters} should return a C{list} of L{LiveForm}
        parameters for the first and last name fields.
        """
        contactType = NameContactType()
        firstName, lastName = contactType.getParameters(None)
        self.assertEqual(firstName.name, 'firstname')
        self.assertEqual(firstName.default, '')
        self.assertEqual(lastName.name, 'lastname')
        self.assertEqual(lastName.default, '')


    def test_getParametersWithDefaults(self):
        """
        L{NameContactType.getParameters} should return a C{list} of L{LiveForm}
        parameters with default values supplied from the L{RealName} item it is
        passed.
        """
        store = Store()
        person = Person(store=store)
        contactType = NameContactType()
        firstName, lastName = contactType.getParameters(
            RealName(person=person, first=u'First', last=u'Last'))
        self.assertEqual(firstName.name, 'firstname')
        self.assertEqual(firstName.default, u'First')
        self.assertEqual(lastName.name, 'lastname')
        self.assertEqual(lastName.default, u'Last')



class EmailContactTests(unittest.TestCase, ContactTestsMixin):
    """
    Tests for the email address parameters defined by L{EmailContactType}.
    """
    def setUp(self):
        self.store = Store()
        self.contactType = EmailContactType(self.store)


    def test_organizerIncludesIt(self):
        """
        L{Organizer.getContactTypes} should include an instance of
        L{EmailContactType} in its return value.
        """
        organizer = Organizer(store=self.store)
        self.assertTrue([
                contactType
                for contactType
                in organizer.getContactTypes()
                if isinstance(contactType, EmailContactType)])


    def test_createContactItem(self):
        """
        L{EmailContactType.createContactItem} should create an L{EmailAddress}
        instance with the supplied values.
        """
        person = Person(store=self.store)
        contactItem = self.contactType.createContactItem(
            person, email=u'user@example.com')
        emails = list(self.store.query(EmailAddress))
        self.assertEqual(emails, [contactItem])
        self.assertEqual(contactItem.address, u'user@example.com')
        self.assertIdentical(contactItem.person, person)


    def test_createContactItemWithEmptyString(self):
        """
        L{EmailContactType.createContactItem} shouldn't create an
        L{EmailAddress} instance if it is given an empty string for the
        address.
        """
        person = Person(store=self.store)
        contactItem = self.contactType.createContactItem(
            person, email=u'')
        emails = list(self.store.query(EmailAddress))
        self.assertIdentical(contactItem, None)
        self.assertEqual(len(emails), 0)


    def test_createContactItemRejectsDuplicate(self):
        """
        L{EmailContactType.createContactItem} should raise an exception if it
        is given an email address already associated with an existing
        L{EmailAddress} item.
        """
        email = u'user@example.com'
        person = Person(store=self.store)
        emailAddress = EmailAddress(
            store=self.store, person=person, address=email)
        self.assertRaises(
            ValueError,
            self.contactType.createContactItem,
            person, email=email)


    def test_editContactItem(self):
        """
        L{EmailContactType.editContactItem} should update the address field of
        the L{EmailAddress} it is passed.
        """
        person = Person(store=self.store)
        emailAddress = EmailAddress(
            store=self.store, person=person, address=u'wrong')
        self.contactType.editContactItem(
            emailAddress, email=u'user@example.com')
        self.assertEqual(emailAddress.address, u'user@example.com')


    def test_editContactItemAcceptsSame(self):
        """
        L{EmailContactType.editContactItem} should update the address field of
        the L{EmailAddress} it is passed, even if it is passed the same value
        which is already set on the item.
        """
        address = u'user@example.com'
        person = Person(store=self.store)
        emailAddress = EmailAddress(
            store=self.store, person=person, address=address)
        self.contactType.editContactItem(
            emailAddress, email=address)
        self.assertEqual(emailAddress.address, address)


    def test_editContactItemRejectsDuplicate(self):
        """
        L{EmailContactType.editContactItem} should raise an exception if it is
        given an email address already associated with a different
        L{EmailAddress} item.
        """
        person = Person(store=self.store)
        existing = EmailAddress(
            store=self.store, person=person, address=u'user@example.com')
        editing = EmailAddress(
            store=self.store, person=person, address=u'user@example.net')
        self.assertRaises(
            ValueError,
            self.contactType.editContactItem,
            editing, email=existing.address)

        # It should be possible to set an EmailAddress's address attribute to
        # its current value, though.
        address = editing.address
        self.contactType.editContactItem(editing, email=address)
        self.assertEqual(editing.address, address)


    def test_getParameters(self):
        """
        L{EmailContactType.getParameters} should return a C{list} of
        L{LiveForm} parameters for an email address.
        """
        (email,) = self.contactType.getParameters(None)
        self.assertEqual(email.name, 'email')
        self.assertEqual(email.default, '')


    def test_getParametersWithDefaults(self):
        """
        L{EmailContactType.getParameters} should return a C{list} of
        L{LiveForm} parameters with default values supplied from the
        L{EmailAddress} item it is passed.
        """
        person = Person(store=self.store)
        (email,) = self.contactType.getParameters(
            EmailAddress(store=self.store, person=person,
                         address=u'user@example.com'))
        self.assertEqual(email.name, 'email')
        self.assertEqual(email.default, u'user@example.com')


    def test_coerce(self):
        """
        L{EmailContactType.coerce} should return a dictionary mapping
        C{'email'} to the email address passed to it.
        """
        self.assertEqual(
            self.contactType.coerce(email=u'user@example.com'),
            {'email': u'user@example.com'})



class PostalContactTests(unittest.TestCase):
    """
    Tests for snail-mail address contact information represented by
    L{PostalContactType}.
    """
    def setUp(self):
        """
        Create a L{Store}, L{PostalContactType}, and L{Person} for use by
        tests.
        """
        self.store = Store()
        self.person = Person(store=self.store)
        self.contactType = PostalContactType()


    def test_organizerIncludesIt(self):
        """
        L{Organizer.getContactTypes} should include an instance of
        L{PostalContactType} in its return value.
        """
        organizer = Organizer(store=self.store)
        self.assertTrue([
                contactType
                for contactType
                in organizer.getContactTypes()
                if isinstance(contactType, PostalContactType)])


    def test_createContactItem(self):
        """
        L{PostalContactType.createContactItem} should create a L{PostalAddress}
        instance with the supplied values.
        """
        contactItem = self.contactType.createContactItem(
            self.person, address=u'123 Street Rd')
        addresses = list(self.store.query(PostalAddress))
        self.assertEqual(addresses, [contactItem])
        self.assertEqual(contactItem.address, u'123 Street Rd')
        self.assertIdentical(contactItem.person, self.person)


    def test_createContactItemWithEmptyString(self):
        """
        L{PostalContactType.createContactItem} shouldn't create a
        L{PostalAddress} instance if it is given an empty string for the
        address.
        """
        contactItem = self.contactType.createContactItem(
            self.person, address=u'')
        addresses = list(self.store.query(PostalAddress))
        self.assertIdentical(contactItem, None)
        self.assertEqual(len(addresses), 0)


    def test_editContactItem(self):
        """
        L{PostalContactType.editContactItem} should update the address field of
        the L{PostalAddress} it is passed.
        """
        postalAddress = PostalAddress(
            store=self.store, person=self.person, address=u'wrong')
        self.contactType.editContactItem(
            postalAddress, address=u'123 Street Rd')
        self.assertEqual(postalAddress.address, u'123 Street Rd')


    def test_getParameters(self):
        """
        L{PostalContactType.getParameters} should return a C{list} of
        L{LiveForm} parameters for a mailing address.
        """
        (address,) = self.contactType.getParameters(None)
        self.assertEqual(address.name, 'address')
        self.assertEqual(address.default, '')


    def test_getParametersWithDefaults(self):
        """
        L{PostalContactType.getParameters} should return a C{list} of
        L{LiveForm} parameters with default values supplied from the
        L{PostalAddress} item it is passed.
        """
        (address,) = self.contactType.getParameters(
            PostalAddress(store=self.store, person=self.person,
                          address=u'123 Street Rd'))
        self.assertEqual(address.name, 'address')
        self.assertEqual(address.default, u'123 Street Rd')


    def test_getContactItems(self):
        """
        L{PostalContactType.getContactItems} should return a C{list} of all
        the L{PostalAddress} instances associated with the specified person.
        """
        firstAddress = PostalAddress(
            store=self.store, person=self.person, address=u'123 Street Rd')
        secondAddress = PostalAddress(
            store=self.store, person=self.person, address=u'456 Street Rd')
        anotherPerson = Person(store=self.store)
        anotherAddress = PostalAddress(
            store=self.store, person=anotherPerson, address=u'789 Street Rd')
        self.assertEqual(
            list(self.contactType.getContactItems(self.person)),
            [firstAddress, secondAddress])


    def test_coerce(self):
        """
        L{PostalContactType.coerce} should return a dictionary mapping
        C{'address'} to the postal address passed to it.
        """
        self.assertEqual(
            self.contactType.coerce(address=u'123 Street Rd'),
            {'address': u'123 Street Rd'})



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


    def test_createPersonDuplicateNickname(self):
        """
        L{Organizer.createPerson} raises an exception when passed a nickname
        which is already associated with a L{Person} in the database.
        """
        nickname = u'test person'
        self.organizer.createPerson(nickname)
        self.assertRaises(
            ValueError,
            self.organizer.createPerson, nickname)


    def test_editPerson(self):
        """
        L{Organizer.editPerson} should change the I{name} of the given
        L{Person} and call I{editContactItem} on each element of the edits
        sequence it is passed.
        """
        person = self.organizer.createPerson(u'alice')
        contactType = StubContactType(None, None, None)
        contactItem = object()
        contactInfo = {'foo': 'bar'}
        self.organizer.editPerson(
            person,
            u'bob',
            [(contactType, contactItem, contactInfo)])
        self.assertEqual(
            contactType.editedContacts,
            [(contactItem, contactInfo)])


    def test_editPersonDuplicateNickname(self):
        """
        L{Organizer.editPerson} raises an exception when passed a nickname
        which is already associated with a different L{Person} in the database.
        """
        alice = self.organizer.createPerson(u'alice')
        bob = self.organizer.createPerson(u'bob')
        self.assertRaises(ValueError,
                          self.organizer.editPerson, bob, alice.name, [])


    def test_editPersonSameName(self):
        """
        L{Organizer.editPerson} allows the new nickname it is passed to be the
        same as the existing name for the given L{Person}.
        """
        alice = self.organizer.createPerson(u'alice')
        self.organizer.editPerson(alice, alice.name, [])
        self.assertEqual(alice.name, u'alice')


    def test_deletePerson(self):
        """
        L{Organizer.deletePerson} should delete the specified person from the
        store.
        """
        person = Person(store=self.store)
        self.organizer.deletePerson(person)
        self.assertEqual(self.store.query(Person, Person.storeID == person.storeID).count(), 0)


    def test_getOrganizerPlugins(self):
        """
        L{Organizer.getOrganizerPlugins} should return an iterator of the
        installed L{IOrganizerPlugin} powerups.
        """
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        self.assertEqual(
            list(self.organizer.getOrganizerPlugins()), [observer])


    def test_createContactItemNotifiesPlugins(self):
        """
        L{Organizer.createContactItem} should call L{contactItemCreated} on all
        L{IOrganizerPlugin} powerups on the store.
        """
        nickname = u'test person'
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        person = self.organizer.createPerson(nickname)
        contactType = StubContactType(None, None, None)
        parameters = {'key': u'value'}
        contactItem = self.organizer.createContactItem(
            contactType, person, parameters)
        self.assertEqual(len(observer.createdContactItems), 1)
        [(observedPerson, observedParameters)] = observer.createdContactItems
        self.assertIdentical(person, observedPerson)
        self.assertEqual(parameters, observedParameters)


    def test_notificationSkippedForUncreatedContactItems(self):
        """
        L{Organizer.createContactItem} should not call L{contactItemCreated} on
        any L{IOrganizerPlugin} powerups on the store if
        L{IContactType.createContactItem} returns C{None} to indicate that it
        is not creating a contact item.
        """
        nickname = u'test person'
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        person = self.organizer.createPerson(nickname)
        contactType = StubContactType(None, None, None, False)
        parameters = {'key': u'value'}
        contactItem = self.organizer.createContactItem(
            contactType, person, parameters)
        self.assertEqual(observer.createdContactItems, [])


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
        store = Store()
        class OldOrganizerPlugin(object):
            """
            An L{IOrganizerPlugin} which does not implement C{getContactTypes}.
            """
        getOrganizerPlugins = Organizer.getOrganizerPlugins.im_func
        plugins = [OldOrganizerPlugin(), StubOrganizerPlugin(createdPeople=[])]
        Organizer.getOrganizerPlugins = lambda self: plugins
        try:
            organizer = Organizer(store=store)
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
            list(self.organizer.getContactTypes())[3:],
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

        self.assertEqual(contactTypes[3:], [])


    def test_getContactCreationParameters(self):
        """
        L{Organizer.getContactCreationParameters} should return a list
        containing C{FORM_INPUT} parameters for each contact type available in
        the system.
        """
        contactForm = object()
        contactTypes = [StubContactType(contactForm, None, None)]
        contactPowerup = StubOrganizerPlugin(
            store=self.store, contactTypes=contactTypes)
        self.store.powerUp(contactPowerup, IOrganizerPlugin)

        parameters = list(self.organizer.getContactCreationParameters())
        self.assertEqual(len(parameters), 4)
        self.assertTrue(isinstance(parameters[3], Parameter))
        self.assertEqual(parameters[3].name, qual(StubContactType))
        self.assertEqual(parameters[3].type, FORM_INPUT)
        self.assertIdentical(parameters[3].coercer, contactForm)


    def test_getContactEditorialParameters(self):
        """
        L{Organizer.getContactEditParameters} should return a list containing
        C{FORM_INPUT} parameters for each contact item available in the system.
        """
        contactItems = [object(), object()]
        editorialForm = object()
        contactTypes = [StubContactType(None, editorialForm, contactItems)]
        contactPowerup = StubOrganizerPlugin(
            store=self.store, contactTypes=contactTypes)
        self.store.powerUp(contactPowerup, IOrganizerPlugin)

        person = self.organizer.createPerson(u'nickname')

        parameters = list(self.organizer.getContactEditorialParameters(person))
        self.assertEqual(len(parameters), 2)

        self.assertIdentical(parameters[0][0], contactTypes[0])
        self.assertIdentical(parameters[0][1], contactItems[0])
        self.assertEqual(parameters[0][2].type, FORM_INPUT)
        self.assertIdentical(parameters[0][2].coercer, editorialForm)

        self.assertIdentical(parameters[1][0], contactTypes[0])
        self.assertIdentical(parameters[1][1], contactItems[1])
        self.assertEqual(parameters[1][2].type, FORM_INPUT)
        self.assertIdentical(parameters[1][2].coercer, editorialForm)

        self.assertNotEqual(parameters[0][2].name, parameters[1][2].name)



class POBox(Item):
    number = text()



class PeopleTests(unittest.TestCase):
    def setUp(self):
        """
        Create an in-memory store and organizer.
        """
        self.store = Store()
        self.organizer = Organizer(store=self.store)
        installOn(self.organizer, self.store)


    def testPersonCreation(self):
        beforeCreation = extime.Time()
        p = self.organizer.personByName(u'testuser')
        afterCreation = extime.Time()

        self.assertEquals(p.name, u'testuser')
        self.failUnless(
            beforeCreation <= p.created <= afterCreation,
            "not (%r <= %r <= %r)" % (beforeCreation, p.created, afterCreation))

        # Make sure people from that organizer don't collide with
        # people from a different organizer
        another = Organizer(store=self.store)
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
        p = Person(store=self.store)
        EmailAddress(store=self.store, person=p, address=u'a@b.c')
        EmailAddress(store=self.store, person=p, address=u'c@d.e')
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
        person = Person(store=self.store)
        person.createContactInfoItem(EmailAddress, 'address', email)
        contacts = list(self.store.query(EmailAddress))
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
        alice = Person(store=self.store)
        bob = Person(store=self.store)
        emailObj = EmailAddress(store=self.store, person=alice, address=email)
        self.assertEqual(alice.findContactInfoItem(EmailAddress, 'address', email), emailObj)
        self.assertEqual(bob.findContactInfoItem(EmailAddress, 'address', email), None)


    def test_editContactInfoItem(self):
        """
        Verify that L{Person.editContactInfoItem} changes the value of
        the contact info item's attribute in the database.
        """
        oldEmail = u'username@hostname'
        newEmail = u'notusername@hostname'

        alice = Person(store=self.store)
        bob = Person(store=self.store)

        aliceEmail = EmailAddress(
            store=self.store, person=alice, address=oldEmail)
        bobEmail = EmailAddress(store=self.store, person=bob, address=oldEmail)

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

        alice = Person(store=self.store)
        bob = Person(store=self.store)
        aliceEmail = EmailAddress(
            store=self.store, person=alice, address=email)
        bobEmail = EmailAddress(store=self.store, person=bob, address=email)

        alice.deleteContactInfoItem(
            EmailAddress, 'address', email)

        emails = list(self.store.query(EmailAddress))
        self.assertEqual(len(emails), 1)
        self.assertIdentical(emails[0], bobEmail)


    def test_getContactInfoItems(self):
        """
        Verify that L{Person.getContactInfoItems} returns the values
        of all contact info items that belong to it.
        """
        alice = Person(store=self.store)
        bob = Person(store=self.store)
        aliceEmail1 = EmailAddress(
            store=self.store, person=alice, address=u'alice1@host')
        aliceEmail2 = EmailAddress(
            store=self.store, person=alice, address=u'alice2@host')
        bobEmail = EmailAddress(
            store=self.store, person=bob, address=u'bob@host')

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
        p = Person(store=self.store)
        EmailAddress(store=self.store, person=p, address=u'a@b.c')
        self.assertEquals(p.getEmailAddress(), u'a@b.c')

    def testPersonRetrieval(self):
        name = u'testuser'
        firstPerson = self.organizer.personByName(name)
        self.assertIdentical(firstPerson, self.organizer.personByName(name))


    def test_addPersonParameters(self):
        """
        L{AddPersonFragment.render_addPersonForm} should return a L{LiveForm}
        with several fixed parameters and any parameters from available
        powerups.
        """
        # With no plugins, only the NameContactType, EmailContactType, and
        # PostalContactType parameters should be returned.
        addPersonFrag = AddPersonFragment(self.organizer)
        addPersonForm = addPersonFrag.render_addPersonForm(None, None)
        self.assertEqual(len(addPersonForm.parameters), 4)

        contactTypes = [StubContactType(LiveForm('foo', []), None, None)]
        observer = StubOrganizerPlugin(
            store=self.store, contactTypes=contactTypes)
        self.store.powerUp(observer, IOrganizerPlugin)

        addPersonForm = addPersonFrag.render_addPersonForm(None, None)
        self.assertEqual(len(addPersonForm.parameters), 5)


    def test_addPersonWithContactItems(self):
        """
        L{AddPersonFragment.addPerson} should give the L{IContactType} plugins
        their information from the form submission.
        """
        creationForm = object()
        contactType = StubContactType(creationForm, None, None)
        observer = StubOrganizerPlugin(
            store=self.store, contactTypes=[contactType])
        self.store.powerUp(observer, IOrganizerPlugin)

        addPersonFragment = AddPersonFragment(self.organizer)

        def keyword(contactType):
            return contactType.uniqueIdentifier().encode('ascii')

        argument = {u'stub': 'value'}
        addPersonFragment.addPerson(
            u'nickname',
            **{contactType.uniqueIdentifier().encode('ascii'): argument,
               keyword(NameContactType()): {
                    u'firstname': u'First',
                    u'lastname': u'Last'},
               keyword(EmailContactType(self.store)): {
                    u'email': u'user@example.com'},
               keyword(PostalContactType()): {
                    u'address': u'123 Street Rd'}})

        person = self.store.findUnique(Person)
        self.assertEqual(contactType.createdContacts, [(person, argument)])


    def testPersonCreation2(self):
        def keyword(contactType):
            return contactType.uniqueIdentifier().encode('ascii')

        addPersonFrag = AddPersonFragment(self.organizer)
        addPersonFrag.addPerson(
            u'Captain P.',
            **{keyword(NameContactType()): {
                    u'firstname': u'Jean-Luc',
                    u'lastname': u'Picard'},
               keyword(EmailContactType(self.store)): {
                    u'email': u'jlp@starship.enterprise'},
               keyword(PostalContactType()): {
                    u'address': u'123 Street Rd'}})

        person = self.store.findUnique(Person)
        self.assertEquals(person.name, 'Captain P.')

        email = self.store.findUnique(
            EmailAddress, EmailAddress.person == person)
        self.assertEquals(email.address, 'jlp@starship.enterprise')

        rn = self.store.findUnique(RealName, RealName.person == person)
        self.assertEquals(rn.first + ' ' + rn.last, 'Jean-Luc Picard')

        pa = self.store.findUnique(
            PostalAddress, PostalAddress.person == person)
        self.assertEqual(pa.address, u'123 Street Rd')


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
        privapp = self.store.findUnique(PrivateApplication)
        p = Person(store=self.store)
        self.assertEqual(self.organizer.linkToPerson(p),
                         (privapp.linkTo(self.organizer.storeID)
                          + '/'
                          + privapp.toWebID(p)))



class StubPerson(object):
    """
    Stub implementation of L{Person} used for testing.

    @ivar contactItems: A list of three-tuples of the arguments passed to
    createContactInfoItem.
    """
    name = u'person'

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



class StubTranslator(object):
    """
    Translate between a dummy row identifier and a dummy object.
    """
    implements(IWebTranslator)

    def __init__(self, rowIdentifier, item):
        self.fromWebID = {rowIdentifier: item}.__getitem__



class PersonScrollingFragmentTests(unittest.TestCase):
    """
    Tests for L{PersonScrollingFragment}.
    """
    def test_performAction(self):
        """
        L{PersonScrollingFragment.performAction} should dispatch the action to
        the object given to the L{PersonScrollingFragment}'s initializer.
        """
        actionName = u'the-action'
        rowIdentifier = u'12345'
        item = object()

        performedActions = []
        def performAction(actionName, rowIdentifier):
            """
            Record an action performed.
            """
            performedActions.append((actionName, rowIdentifier))

        scrollingFragment = PersonScrollingFragment(
            None, None, None,
            StubTranslator(rowIdentifier, item),
            performAction)
        performAction = expose.get(scrollingFragment, 'performAction')
        performAction(actionName, rowIdentifier)

        self.assertEqual(performedActions, [(actionName, item)])


    def test_scrollingAttributes(self):
        """
        L{PersonScrollingFragment} should have the attributes its base class
        wants to use.
        """
        baseConstraint = object()
        sort = object()

        fragment = PersonScrollingFragment(
            None, baseConstraint, sort,
            StubTranslator(None, None), None)
        self.assertIdentical(fragment.baseConstraint, baseConstraint)
        self.assertIdentical(fragment.currentSortColumn, sort)
        self.assertIdentical(fragment.itemType, Person)
        self.assertEqual(len(fragment.columns), 1)
        self.assertTrue(isinstance(fragment.columns['name'], PersonNameColumn))



class OrganizerFragmentTests(unittest.TestCase):
    """
    Tests for L{OrganizerFragment}.
    """
    def setUp(self):
        """
        Create an L{OrganizerFragment} wrapped around a double for
        L{Organizer}.
        """
        deletedPeople = []
        class StubOrganizer(object):
            _webTranslator = StubTranslator(None, None)

            def __init__(self, store):
                self.store = store

            def lastNameOrder(self):
                return None

            def deletePerson(self, person):
                deletedPeople.append(person)

        self.organizer = StubOrganizer(Store())
        self.fragment = OrganizerFragment(self.organizer)
        self.deletedPeople = deletedPeople


    def test_peopleTable(self):
        """
        L{OrganizerFragment.render_peopleTable} should return a
        L{PersonScrollingFragment}.
        """
        request = FakeRequest(args={})
        scroller = self.fragment.render_peopleTable(request, None)
        self.assertTrue(isinstance(scroller, PersonScrollingFragment))


    def test_getAddPerson(self):
        """
        L{OrganizerFragment.getAddPerson} should return an
        L{AddPersonFragment}.
        """
        addPersonFragment = expose.get(self.fragment, 'getAddPerson')()
        self.assertTrue(isinstance(addPersonFragment, AddPersonFragment))
        self.assertIdentical(addPersonFragment.organizer, self.organizer)
        self.assertIdentical(addPersonFragment.fragmentParent, self.fragment)


    def test_performAction(self):
        """
        L{OrganizerFragment.performAction} should dispatch to a
        C{action_}-prefixed method.
        """
        ran = []
        item = object()
        self.fragment.action_mock = ran.append
        self.fragment.performAction(u'mock', item)
        self.assertEqual(ran, [item])


    def test_editAction(self):
        """
        L{OrganizerFragment.action_edit} should return an L{EditPersonView}
        wrapped around the appropriate person item.
        """
        item = object()
        editView = self.fragment.action_edit(item)
        self.assertTrue(isinstance(editView, EditPersonView))
        self.assertIdentical(editView.person, item)
        self.assertIdentical(editView.fragmentParent, self.fragment)


    def test_deleteAction(self):
        """
        L{OrganizerFragment.action_delete} should call L{deletePerson} on the
        object it wraps, passing it the person object it received.
        """
        person = object()
        self.fragment.action_delete(person)
        self.assertEqual(self.deletedPeople, [person])



class AddPersonFragmentTests(unittest.TestCase):
    """
    Tests for L{AddPersonFragment}.
    """
    def test_renders(self):
        """
        An L{AddPersonFragment} should be renderable.
        """
        store = Store()
        organizer = Organizer(store=store)
        fragment = AddPersonFragment(organizer)
        result = renderLiveFragment(fragment)
        self.assertTrue(isinstance(result, str))



class EditPersonViewTests(unittest.TestCase):
    """
    Tests for L{EditPersonView}.
    """
    def setUp(self):
        """
        Create an L{EditPersonView} wrapped around a stub person and stub organizer.
        """
        self.contactType = StubContactType(None, None, None)
        self.contactItem = object()
        self.contactForm = Parameter(u'contact-form', TEXT_INPUT, unicode)

        class StubOrganizer(record('person contactType contactItem contactForm')):
            """
            L{Organizer}-alike

            @ivar edits: A list of three-tuples giving the arguments passed to
                editPerson.
            """
            def __init__(self, *a, **kw):
                super(StubOrganizer, self).__init__(*a, **kw)
                self.edits = []

            def editPerson(self, person, nickname, edits):
                self.edits.append((person, nickname, edits))


            def getContactEditorialParameters(self, person):
                return {
                    self.person: [
                        (self.contactType,
                         self.contactItem,
                         self.contactForm)]}[person]

        self.person = StubPerson(None)
        self.person.organizer = StubOrganizer(
            self.person, self.contactType, self.contactItem, self.contactForm)
        self.view = EditPersonView(self.person)


    def test_editContactItems(self):
        """
        L{EditPersonView.editContactItems} should take a dictionary mapping
        parameter names to values and update its person's contact information
        in a transaction.
        """
        transactions = []
        transaction = record('function args kwargs')
        class StubStore(object):
            def transact(self, f, *a, **kw):
                transactions.append(transaction(f, a, kw))
        self.person.store = StubStore()
        contactInfo = {u'stub': 'value'}
        contactType = StubContactType(None, None, None)
        self.view.contactItems = {'name': (contactType, self.contactItem)}
        self.view.editContactItems(u'nick', name=contactInfo)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(self.person.name, StubPerson.name)
        self.assertEqual(contactType.editedContacts, [])
        transactions[0].function(
            *transactions[0].args, **transactions[0].kwargs)
        self.assertEqual(
            self.person.organizer.edits,
            [(self.person, u'nick',
              [(contactType, self.contactItem, contactInfo)])])


    def test_editorialContactForms(self):
        """
        L{EditPersonView.editorialContactForms} should return an instance of
        L{EditorialContactForms} for the wrapped L{Person} as a child of the
        tag it is passed.
        """
        editorialContactForms = renderer.get(
            self.view, 'editorialContactForms')
        tag = div()
        forms = editorialContactForms(None, tag)
        self.assertEqual(forms.tagName, 'div')
        self.assertEqual(forms.attributes, {})
        self.assertEqual(len(forms.children), 1)

        form = forms.children[0]
        self.assertTrue(isinstance(form, LiveForm))
        self.assertEqual(form.callable, self.view.editContactItems)
        self.assertEqual(form.parameters[1:], [self.contactForm])
        self.assertIdentical(form.fragmentParent, self.view)
        self.assertEqual(
            self.view.contactItems[form.parameters[1].name],
            (self.contactType, self.contactItem))


    def test_rend(self):
        """
        L{EditPersonView} should be renderable in the typical manner.
        """
        # XXX I have no hope of asserting anything meaningful about the return
        # value of renderLiveFragment.  However, even calling it at all pointed
        # out that: there was no docFactory; the fragmentName didn't reference
        # an extant template; the LiveForm had no fragment parent (for which I
        # also updated test_editorialContactForms to do a direct
        # assertion). -exarkun
        markup = renderLiveFragment(self.view)
        self.assertIn(self.view.jsClass, markup)
