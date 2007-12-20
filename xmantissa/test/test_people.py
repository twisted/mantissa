
"""
Tests for L{xmantissa.people}.
"""
import warnings

from xml.dom.minidom import parseString

from zope.interface import implements

from string import lowercase

from twisted.python.reflect import qual
from twisted.python.filepath import FilePath
from twisted.python.components import registerAdapter
from twisted.trial import unittest

from nevow.loaders import stan
from nevow.tags import div, slot
from nevow.flat import flatten
from nevow.athena import expose
from nevow.page import renderer
from nevow.testutil import FakeRequest
from nevow import context

from epsilon import extime
from epsilon.extime import Time
from epsilon.structlike import record

from axiom.store import Store, AtomicFile
from axiom.dependency import installOn, installedOn
from axiom.item import Item
from axiom.attributes import inmemory, text
from axiom.errors import DeletionDisallowed

from axiom.userbase import LoginSystem

from axiom.plugins.userbasecmd import Create
from axiom.plugins.mantissacmd import Mantissa

from xmantissa.test.rendertools import renderLiveFragment, TagTestingMixin
from xmantissa.scrolltable import UnsortableColumn, ScrollingElement
from xmantissa import people
from xmantissa.people import (
    Organizer, Person, EmailAddress, AddPersonFragment, ImportPeopleWidget,
    Mugshot, addContactInfoType, contactInfoItemTypeFromClassName,
    _CONTACT_INFO_ITEM_TYPES, ContactInfoFragment, PersonDetailFragment,
    PhoneNumber, PhoneNumberContactType, ReadOnlyPhoneNumberView,
    setIconURLForContactInfoType, iconURLForContactInfoType,
    _CONTACT_INFO_ICON_URLS, PersonScrollingFragment, OrganizerFragment,
    EditPersonView, BaseContactType, EmailContactType, _normalizeWhitespace,
    PostalAddress, PostalContactType, VIPPersonContactType, _PersonVIPStatus,
    ReadOnlyEmailView, ReadOnlyPostalAddressView, getPersonURL,
    _stringifyKeys, makeThumbnail, _descriptiveIdentifier,
    ReadOnlyContactInfoView, PersonSummaryView, MugshotUploadForm,
    ORGANIZER_VIEW_STATES, MugshotResource, Notes, NotesContactType,
    ReadOnlyNotesView)

from xmantissa.webapp import PrivateApplication
from xmantissa.liveform import (
    TEXT_INPUT, InputError, Parameter, LiveForm, ListChangeParameter,
    ListChanges, CreateObject, EditObject, FormParameter, ChoiceParameter,
    TEXTAREA_INPUT)
from xmantissa.ixmantissa import (
    IOrganizerPlugin, IContactType, IWebTranslator, IPersonFragment)
from xmantissa.signup import UserInfo


# the number of non-plugin IContactType implementations provided by Mantissa.
builtinContactTypeCount = 5



class PeopleUtilitiesTestCase(unittest.TestCase):
    """
    Tests for module-level utility functions in L{xmantissa.people}.
    """
    def test_stringifyKeys(self):
        """
        Verify that L{_stringifyKeys} returns a dictionary which is the same
        as the input except for having C{str} keys.
        """
        input = {u'a': u'b', u'b': u'c'}
        output = _stringifyKeys(input)
        self.assertEqual(len(output), 2)
        keys = output.keys()
        self.failUnless(isinstance(keys[0], str))
        self.failUnless(isinstance(keys[1], str))
        self.assertEqual(sorted(keys), ['a', 'b'])
        self.failUnless(isinstance(output['a'], unicode))
        self.failUnless(isinstance(output['b'], unicode))
        self.assertEqual(output['a'], u'b')
        self.assertEqual(output['b'], u'c')


    def test_makeThumbnail(self):
        """
        Verify that L{makeThumbnail} makes a correctly scaled thumbnail image.
        """
        try:
            from PIL import Image
        except ImportError:
            raise unittest.SkipTest('PIL is not available')

        # make an image to thumbnail
        fullSizePath = self.mktemp()
        fullSizeFormat = 'JPEG'
        fullWidth = 543
        fullHeight = 102
        Image.new('RGB', (fullWidth, fullHeight)).save(
            file(fullSizePath, 'w'), fullSizeFormat)
        # thumbnail it
        thumbnailPath = self.mktemp()
        thumbnailSize = 60
        thumbnailFormat = 'TIFF'
        makeThumbnail(
            fullSizePath, thumbnailPath, thumbnailSize, thumbnailFormat)
        # open the thumbnail, make sure it's the right size and format
        thumbnailImage = Image.open(file(thumbnailPath))
        scaleFactor = float(thumbnailSize) / fullWidth
        expectedHeight = int(fullHeight * scaleFactor)
        self.assertEqual(
            thumbnailImage.size, (thumbnailSize, expectedHeight))
        self.assertEqual(thumbnailImage.format, thumbnailFormat)
        # make sure the original image is untouched
        originalImage = Image.open(file(fullSizePath))
        self.assertEqual(originalImage.format, fullSizeFormat)
        self.assertEqual(originalImage.size, (fullWidth, fullHeight))


    def test_descriptiveIdentifier(self):
        """
        Verify that L{_descriptiveIdentifier} returns the result of the
        C{descriptiveIdentifier} method if its passed an object that defines
        one.
        """
        identifier = u'lol identifier'
        class MyContactType:
            def descriptiveIdentifier(self):
                return identifier
        self.assertEqual(
            _descriptiveIdentifier(MyContactType()), identifier)


    def test_noDescriptiveIdentifier(self):
        """
        Verify that L{_descriptiveIdentifier} returns a sensible identifier
        based on the class name of the object it is passed, and issues a
        warning, if the object doesn't implement C{descriptiveIdentifier}.
        """
        class MyContactType:
            pass
        self.assertEqual(
            _descriptiveIdentifier(MyContactType()), u'My Contact Type')
        self.assertWarns(
            PendingDeprecationWarning,
            "IContactType now has the 'descriptiveIdentifier'"
            " method, xmantissa.test.test_people.MyContactType"
            " did not implement it",
            people.__file__,
            lambda: _descriptiveIdentifier(MyContactType()))



class MugshotUploadFormTestCase(unittest.TestCase):
    """
    Tests for L{MugshotUploadForm}.
    """
    def setUp(self):
        """
        Construct a L{Person}, suitable for passing to L{MugshotUploadForm}'s
        constructor.
        """
        # can't use mock objects because we need ITemplateNameResolver to
        # render MugshotUploadForm
        store = Store()
        self.organizer = Organizer(store=store)
        installOn(self.organizer, store)
        self.person = Person(store=store, organizer=self.organizer)


    def test_callback(self):
        """
        Verify that L{MugshotUploadForm} calls the supplied callback after a
        successful POST.
        """
        cbGotMugshotArgs = []
        def cbGotMugshot(contentType, file):
            cbGotMugshotArgs.append((contentType, file))
        form = MugshotUploadForm(self.person, cbGotMugshot)

        theContentType = 'image/tiff'
        theFile = object()
        class FakeUploadField:
            type = theContentType
            file = theFile

        request = FakeRequest()
        request.method = 'POST'
        request.fields = {'uploaddata': FakeUploadField}
        ctx = context.PageContext(
            tag=form, parent=context.RequestContext(
                tag=request))
        form.renderHTTP(ctx)
        self.assertEqual(
            cbGotMugshotArgs,
            [(u'image/tiff', theFile)])


    def test_smallerMugshotURL(self):
        """
        L{MugshotUploadForm.render_smallerMugshotURL} should return the
        correct URL.
        """
        form = MugshotUploadForm(self.person, None)
        self.assertEqual(
            form.render_smallerMugshotURL(None, None),
            self.organizer.linkToPerson(self.person) + '/mugshot/smaller')



class MugshotTestCase(unittest.TestCase):
    """
    Tests for L{Mugshot}.
    """
    def _doFromFileTest(self, store, person):
        """
        Verify that the L{Mugshot} returned from L{Mugshot.fromFile} has the
        correct attribute values.
        """
        newBody = store.newFilePath('newBody')
        newSmallerBody = store.newFilePath('newSmallerBody')
        newFormat = u'TIFF'
        def _makeThumbnail(cls, inputFile, person, format, smaller):
            if smaller:
                return newSmallerBody
            return newBody
        originalMakeThumbnail = Mugshot.makeThumbnail
        try:
            Mugshot.makeThumbnail = classmethod(_makeThumbnail)
            mugshot = Mugshot.fromFile(
                person, file(self.mktemp(), 'w'), newFormat)
        finally:
            Mugshot.makeThumbnail = originalMakeThumbnail
        # and no others should have been created
        self.assertEqual(store.count(Mugshot), 1)
        # the item should have been updated with the paths returned from our
        # fake Mugshot.makeThumbnail()
        self.assertEqual(mugshot.body, newBody)
        self.assertEqual(mugshot.smallerBody, newSmallerBody)
        # the 'person' attribute should be unchanged
        self.assertIdentical(mugshot.person, person)
        # the format attribute should be updated
        self.assertEqual(mugshot.type, u'image/' + newFormat)
        return mugshot


    def test_fromFileExistingMugshot(self):
        """
        Verify that L{Mugshot.fromFile} will update the attributes on an
        existing L{Mugshot} item for the given person, if one exists.
        """
        store = Store(filesdir=self.mktemp())
        person = Person(store=store)
        mugshot = Mugshot(
            store=store,
            type=u'JPEG',
            body=store.newFilePath('body'),
            smallerBody=store.newFilePath('smallerBody'),
            person=person)
        self.assertIdentical(
            self._doFromFileTest(store, person),
            mugshot)


    def test_fromFileNoMugshot(self):
        """
        Verify that L{Mugshot.fromFile} creates a new L{Mugshot} for the given
        person, if one does not exist.
        """
        store = Store(filesdir=self.mktemp())
        person = Person(store=store)
        self._doFromFileTest(store, person)


    def _doMakeThumbnailTest(self, smaller):
        """
        Verify that L{Mugshot.makeThumbnail} passes the correct arguments to
        L{makeThumbnail}, when passed the given value for the C{smaller}
        argument.
        """
        makeThumbnailCalls = []
        def _makeThumbnail(
            inputFile, outputFile, thumbnailSize, outputFormat='jpeg'):
            makeThumbnailCalls.append((
                inputFile, outputFile, thumbnailSize, outputFormat))

        store = Store(filesdir=self.mktemp())
        person = Person(store=store)
        inputFile = file(self.mktemp(), 'w')
        inputFormat = 'JPEG'
        originalMakeThumbnail = people.makeThumbnail
        try:
            people.makeThumbnail = _makeThumbnail
            thumbnailPath = Mugshot.makeThumbnail(
                inputFile, person, inputFormat, smaller)
        finally:
            people.makeThumbnail = originalMakeThumbnail
        self.assertEqual(len(makeThumbnailCalls), 1)
        (gotInputFile, outputFile, thumbnailSize, outputFormat) = (
            makeThumbnailCalls[0])
        self.assertEqual(gotInputFile, inputFile)
        if smaller:
            self.assertEqual(thumbnailSize, Mugshot.smallerSize)
        else:
            self.assertEqual(thumbnailSize, Mugshot.size)
        self.assertEqual(outputFormat, inputFormat)
        self.assertTrue(isinstance(outputFile, AtomicFile))
        # it should return the right path
        self.assertEqual(outputFile.finalpath, thumbnailPath)


    def test_makeThumbnail(self):
        """
        Verify that L{Mugshot.makeThumbnail} passes the correct arguments to
        L{makeThumbnail}.
        """
        self._doMakeThumbnailTest(smaller=False)


    def test_makeThumbnailSmaller(self):
        """
        Like L{test_makeThumbnail}, but for when the method is asked to make a
        smaller-sized thumbnail.
        """
        self._doMakeThumbnailTest(smaller=True)



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
        A list of all L{Person} items created since this item was last loaded
        from the database.
        """)

    contactTypes = inmemory(
        doc="""
        A list of L{IContact} implementors to return from L{getContactTypes}.
        """)

    renamedPeople = inmemory(
        doc="""
        A list of two-tuples of C{unicode} with the first element giving the
        name of each L{Person} item whose name changed at the time of the
        change and the second element giving the value passed for the old name
        parameter.
        """)

    createdContactItems = inmemory(
        doc="""
        A list of contact items created since this item was last loaded from
        the database.
        """)

    editedContactItems = inmemory(
        doc="""
        A list of contact items edited since this item was last loaded from
        the database.
        """)

    personalization = inmemory(
        doc="""
        An objects to be returned by L{personalize}.
        """)

    personalizedPeople = inmemory(
        doc="""
        A list of people passed to L{personalize}.
        """)

    def activate(self):
        """
        Initialize in-memory state tracking attributes to default values.
        """
        self.createdPeople = []
        self.renamedPeople = []
        self.createdContactItems = []
        self.editedContactItems = []
        self.personalization = None
        self.personalizedPeople = []


    def personCreated(self, person):
        """
        Record the creation of a L{Person}.
        """
        self.createdPeople.append(person)


    def personNameChanged(self, person, oldName):
        """
        Record the change of a L{Person}'s name.
        """
        self.renamedPeople.append((person.name, oldName))


    def contactItemCreated(self, contactItem):
        """
        Record the creation of a contact item.
        """
        self.createdContactItems.append(contactItem)


    def contactItemEdited(self, contactItem):
        """
        Record the editing of a contact item.
        """
        self.editedContactItems.append(contactItem)


    def getContactTypes(self):
        """
        Return the contact types list this item was constructed with.
        """
        return self.contactTypes


    def personalize(self, person):
        """
        Record a personalization attempt and return C{self.personalization}.
        """
        self.personalizedPeople.append(person)
        return self.personalization



class StubReadOnlyView(object):
    """
    Test double for the objects returned by L{IContactType.getReadOnlyView}.

    @ivar item: The contact item the view is for.
    @ivar type: The contact type the contact item comes from.
    """
    def __init__(self, contactItem, contactType):
        self.item = contactItem
        self.type = contactType




class StubContactType(object):
    """
    Behaviorless contact type implementation used for tests.

    @ivar parameters: A list of L{xmantissa.liveform.Parameter} instances which
        will become the return value of L{getParameters}.
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
    @ivar theDescriptiveIdentifier: The object to return from
    L{descriptiveIdentifier}.
    """
    implements(IContactType)

    def __init__(self, parameters, editorialForm, contactItems,
            createContactItems=True, allowMultipleContactItems=True,
            theDescriptiveIdentifier=u''):
        self.parameters = parameters
        self.createdContacts = []
        self.editorialForm = editorialForm
        self.editedContacts = []
        self.contactItems = contactItems
        self.queriedPeople = []
        self.editedContacts = []
        self.createContactItems = createContactItems
        self.allowMultipleContactItems = allowMultipleContactItems
        self.theDescriptiveIdentifier = theDescriptiveIdentifier


    def getParameters(self, ignore):
        """
        Return L{parameters}.
        """
        return self.parameters


    def uniqueIdentifier(self):
        """
        Return the L{qual} of this class.
        """
        return qual(self.__class__).decode('ascii')


    def descriptiveIdentifier(self):
        """
        Return L{theDescriptiveIdentifier}.
        """
        return self.theDescriptiveIdentifier


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


    def getReadOnlyView(self, contact):
        """
        Return a stub view object for the given contact.

        @rtype: L{StubReadOnlyView}
        """
        return StubReadOnlyView(contact, self)



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


    def test_organizerIncludesIt(self):
        """
        L{Organizer.getContactTypes} should include an instance of our contact
        type in its return value.
        """
        organizer = Organizer(store=self.store)
        self.assertTrue([
                contactType
                for contactType
                in organizer.getContactTypes()
                if isinstance(contactType, self.contactType.__class__)])



class EmailContactTests(unittest.TestCase, ContactTestsMixin):
    """
    Tests for the email address parameters defined by L{EmailContactType}.
    """
    def setUp(self):
        self.store = Store()
        self.contactType = EmailContactType(self.store)


    def test_descriptiveIdentifier(self):
        """
        L{EmailContactType.descriptiveIdentifier} should be "Email Address".
        """
        self.assertEqual(
            self.contactType.descriptiveIdentifier(), u'Email Address')


    def test_allowsMultipleContactItems(self):
        """
        L{EmailContactType.allowMultipleContactItems} should be C{True}.
        """
        self.assertTrue(self.contactType.allowMultipleContactItems)


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


    def test_getReadOnlyView(self):
        """
        L{EmailContactType.getReadOnlyView} should return a
        L{ReadOnlyEmailView} wrapped around the given contact item.
        """
        store = Store()
        person = Person(store=store)
        contact = EmailAddress(store=store, person=person, address=u'')
        view = self.contactType.getReadOnlyView(contact)
        self.assertTrue(isinstance(view, ReadOnlyEmailView))
        self.assertIdentical(view.email, contact)



class VIPPersonContactTypeTestCase(unittest.TestCase):
    """
    Tests for L{VIPPersonContactType}.
    """
    def setUp(self):
        """
        Create a L{Person} and a L{VIPPersonContactType}.
        """
        self.person = Person(vip=False)
        self.contactType = VIPPersonContactType()


    def test_providesContactType(self):
        """
        L{VIPPersonContactType} should provide L{IContactType}.
        """
        self.assertTrue(IContactType.providedBy(self.contactType))


    def test_createContactItem(self):
        """
        L{VIPPersonContactType.createContactItem} should set the C{vip}
        attribute of the given person to the specified value, and return a
        L{_PersonVIPStatus} wrapping the person.
        """
        contactItem = self.contactType.createContactItem(
            self.person, True)
        self.assertTrue(isinstance(contactItem, _PersonVIPStatus))
        self.assertIdentical(contactItem.person, self.person)
        self.assertTrue(self.person.vip)
        contactItem = self.contactType.createContactItem(
            self.person, False)
        self.assertTrue(isinstance(contactItem, _PersonVIPStatus))
        self.assertIdentical(contactItem.person, self.person)
        self.assertFalse(self.person.vip)


    def test_editContactItem(self):
        """
        L{VIPPersonContactType.editContactItem} should set the C{vip}
        attribute of the wrapped person to the specified value.
        """
        self.contactType.editContactItem(
            _PersonVIPStatus(self.person), True)
        self.assertTrue(self.person.vip)
        self.contactType.editContactItem(
            _PersonVIPStatus(self.person), False)
        self.assertFalse(self.person.vip)


    def test_getParametersNoPerson(self):
        """
        L{VIPPersonContactType.getParameters} should return a parameter with a
        default of C{False} when it's passed C{None}.
        """
        params = self.contactType.getParameters(None)
        self.assertEqual(len(params), 1)
        param = params[0]
        self.assertFalse(param.default)


    def test_getParametersPerson(self):
        """
        L{VIPPersonContactType.getParameters} should return a parameter with
        the correct default when it's passed a L{_PersonVIPStatus} wrapping a
        person.
        """
        params = self.contactType.getParameters(
            _PersonVIPStatus(self.person))
        self.assertEqual(len(params), 1)
        param = params[0]
        self.assertFalse(param.default)
        self.person.vip = True
        params = self.contactType.getParameters(
            _PersonVIPStatus(self.person))
        self.assertEqual(len(params), 1)
        param = params[0]
        self.assertTrue(param.default)


    def test_getReadOnlyView(self):
        """
        L{VIPPersonContactType.getReadOnlyView} should return something which
        flattens to the empty string.
        """
        view = self.contactType.getReadOnlyView(
            _PersonVIPStatus(self.person))
        self.assertEqual(flatten(view), '')



class PostalContactTests(unittest.TestCase, ContactTestsMixin):
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


    def test_descriptiveIdentifier(self):
        """
        L{PostalContactType.descriptiveIdentifier} should be "Postal Address".
        """
        self.assertEqual(
            self.contactType.descriptiveIdentifier(), u'Postal Address')


    def test_allowsMultipleContactItems(self):
        """
        L{PostalContactType.allowMultipleContactItems} should be C{True}.
        """
        self.assertTrue(self.contactType.allowMultipleContactItems)


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


    def test_getReadOnlyView(self):
        """
        L{PostalContactType.getReadOnlyView} should return a
        L{ReadOnlyPostalAddressView} wrapped around the given contact item.
        """
        store = Store()
        person = Person(store=store)
        contact = PostalAddress(store=store, person=person, address=u'')
        view = self.contactType.getReadOnlyView(contact)
        self.assertTrue(isinstance(view, ReadOnlyPostalAddressView))
        self.assertIdentical(view._address, contact)



class PhoneNumberContactTypeTestCase(unittest.TestCase, ContactTestsMixin):
    """
    Tests for L{PhoneNumberContactType}.
    """
    def setUp(self):
        """
        Create a store, L{PhoneNumberContactType} and L{Person}.
        """
        self.store = Store()
        self.person = Person(store=self.store)
        self.contactType = PhoneNumberContactType()


    def test_descriptiveIdentifier(self):
        """
        L{PhoneNumberContactType.descriptiveIdentifier} should be "Phone
        Number".
        """
        self.assertEqual(
            self.contactType.descriptiveIdentifier(), u'Phone Number')


    def test_allowsMultipleContactItems(self):
        """
        L{PhoneNumberContactType.allowMultipleContactItems} should be C{True}.
        """
        self.assertTrue(self.contactType.allowMultipleContactItems)


    def test_createContactItem(self):
        """
        L{PhoneNumberContactType.createContactItem} should create a
        L{PhoneNumber} item with the supplied value.
        """
        contactItem = self.contactType.createContactItem(
            self.person,
            label=PhoneNumber.LABELS.HOME,
            number=u'123456')
        numbers = list(self.store.query(PhoneNumber))
        self.assertEqual(numbers, [contactItem])
        self.assertEqual(
            contactItem.label, PhoneNumber.LABELS.HOME)
        self.assertEqual(contactItem.number, u'123456')
        self.assertIdentical(contactItem.person, self.person)


    def test_createContactItemWithEmptyString(self):
        """
        L{PhoneNumberContactType.createContactItem} shouldn't create an item
        if it's passed an empty number.
        """
        self.assertIdentical(
            self.contactType.createContactItem(
                self.person,
                label=PhoneNumber.LABELS.HOME,
                number=u''),
            None)
        self.assertEqual(self.store.query(PhoneNumber).count(), 0)


    def test_editContactItem(self):
        """
        L{PhoneNumberContactType.editContactItem} should update the I{number}
        and I{label} attribute sof the given item.
        """
        contactItem = PhoneNumber(
            store=self.store,
            person=self.person,
            label=PhoneNumber.LABELS.HOME,
            number=u'123456')
        self.contactType.editContactItem(
            contactItem,
            label=PhoneNumber.LABELS.WORK,
            number=u'654321')
        self.assertEqual(
            contactItem.label, PhoneNumber.LABELS.WORK)
        self.assertEqual(contactItem.number, u'654321')


    def test_getParameters(self):
        """
        L{PhoneNumberContactType.getParameters} should return a list
        containing two parameters.
        """
        parameters = self.contactType.getParameters(None)
        self.assertEqual(len(parameters), 2)
        (labelParam, numberParam) = parameters
        self.assertTrue(isinstance(labelParam, ChoiceParameter))
        self.assertEqual(labelParam.name, 'label')
        self.assertEqual(
            [c.value for c in labelParam.choices],
            PhoneNumber.LABELS.ALL_LABELS)
        self.assertTrue(isinstance(numberParam, Parameter))
        self.assertEqual(numberParam.name, 'number')
        self.assertEqual(numberParam.default, '')
        self.assertEqual(numberParam.type, TEXT_INPUT)


    def test_getParametersWithDefault(self):
        """
        L{PhoneNumberContactType.getParameters} should correctly default the
        returned parameter if its passed a contact item.
        """
        contactItem = PhoneNumber(
            store=self.store,
            person=self.person,
            label=PhoneNumber.LABELS.HOME,
            number=u'123456')
        parameters = self.contactType.getParameters(contactItem)
        self.assertEqual(len(parameters), 2)
        (labelParam, numberParam) = parameters
        selectedOptions = []
        for choice in labelParam.choices:
            if choice.selected:
                selectedOptions.append(choice.value)
        self.assertEqual(selectedOptions, [contactItem.label])
        self.assertEqual(numberParam.default, contactItem.number)


    def test_getContactItems(self):
        """
        L{PhoneNumberContactType.getContactItems} should return only
        L{PhoneNumber} items associated with the given person.
        """
        otherPerson = Person(store=self.store)
        PhoneNumber(
            store=self.store, person=otherPerson, number=u'123455')
        expectedNumbers = [
            PhoneNumber(
                store=self.store, person=self.person, number=u'123456'),
            PhoneNumber(
                store=self.store, person=self.person, number=u'123457')]
        self.assertEqual(
            list(self.contactType.getContactItems(self.person)),
            expectedNumbers)


    def test_getReadOnlyView(self):
        """
        L{PhoneNumberContactType.getReadOnlyView} should return a
        correctly-initialized L{ReadOnlyPhoneNumberView}.
        """
        contactItem = PhoneNumber(
            store=self.store, person=self.person, number=u'123456')
        view = self.contactType.getReadOnlyView(contactItem)
        self.assertTrue(isinstance(view, ReadOnlyPhoneNumberView))
        self.assertIdentical(view.phoneNumber, contactItem)



class NotesContactTypeTestCase(unittest.TestCase, ContactTestsMixin):
    """
    Tests for L{NotesContactType}.
    """
    def setUp(self):
        """
        Create a store, L{NotesContactType} and L{Person}.
        """
        self.store = Store()
        self.person = Person(store=self.store)
        self.contactType = NotesContactType()


    def test_descriptiveIdentifier(self):
        """
        L{NotesContactType.descriptiveIdentifier} should be "Notes".
        """
        self.assertEqual(
            self.contactType.descriptiveIdentifier(), u'Notes')


    def test_allowsMultipleContactItems(self):
        """
        L{NotesContactType.allowMultipleContactItems} should be C{False}.
        """
        self.assertFalse(self.contactType.allowMultipleContactItems)


    def test_createContactItem(self):
        """
        L{NotesContactType.createContactItem} should create a
        L{Notes} item with the supplied value.
        """
        contactItem = self.contactType.createContactItem(
            self.person, notes=u'some notes')
        notes = list(self.store.query(Notes))
        self.assertEqual(notes, [contactItem])
        self.assertEqual(contactItem.notes, u'some notes')
        self.assertIdentical(contactItem.person, self.person)


    def test_createContactItemWithEmptyString(self):
        """
        L{NotesContactType.createContactItem} shouldn't create an item
        if it's passed an empty string.
        """
        self.assertIdentical(
            self.contactType.createContactItem(
                self.person, notes=u''),
            None)
        self.assertEqual(self.store.query(Notes).count(), 0)


    def test_editContactItem(self):
        """
        L{NotesContactType.editContactItem} should update the I{notes}
        attribute of the given item.
        """
        contactItem = Notes(
            store=self.store,
            person=self.person,
            notes=u'some notes')
        self.contactType.editContactItem(
            contactItem,
            notes=u'revised notes')
        self.assertEqual(contactItem.notes, u'revised notes')


    def test_getParameters(self):
        """
        L{NotesContactType.getParameters} should return a list
        containing a single parameter.
        """
        parameters = self.contactType.getParameters(None)
        self.assertEqual(len(parameters), 1)
        param = parameters[0]
        self.assertTrue(isinstance(param, Parameter))
        self.assertEqual(param.name, 'notes')
        self.assertEqual(param.default, '')
        self.assertEqual(param.type, TEXTAREA_INPUT)
        self.assertEqual(param.label, u'Notes')


    def test_getParametersWithDefault(self):
        """
        L{NotesContactType.getParameters} should correctly default the
        returned parameter if it's passed a contact item.
        """
        contactItem = Notes(
            store=self.store,
            person=self.person,
            notes=u'some notes')
        parameters = self.contactType.getParameters(contactItem)
        self.assertEqual(len(parameters), 1)
        self.assertEqual(parameters[0].default, contactItem.notes)


    def test_getContactItems(self):
        """
        L{NotesContactType.getContactItems} should return only
        the L{Notes} item associated with the given person.
        """
        Notes(store=self.store,
              person=Person(store=self.store),
              notes=u'notes')
        expectedNotes = [
            Notes(store=self.store,
                  person=self.person,
                  notes=u'some notes')]
        self.assertEqual(
            list(self.contactType.getContactItems(self.person)),
            expectedNotes)


    def test_getContactItemsCreates(self):
        """
        L{NotesContactType.getContactItems} should create a L{Notes} item for
        the given person, if one does not exist.
        """
        # sanity check
        self.assertEqual(self.store.query(Notes).count(), 0)

        contactItems = self.contactType.getContactItems(self.person)
        self.assertEqual(len(contactItems), 1)
        self.assertEqual(contactItems, list(self.store.query(Notes)))
        self.assertEqual(contactItems[0].notes, u'')
        self.assertIdentical(contactItems[0].person, self.person)


    def test_getReadOnlyView(self):
        """
        L{NotesContactType.getReadOnlyView} should return a
        correctly-initialized L{ReadOnlyNotesView}.
        """
        contactItem = Notes(
            store=self.store, person=self.person, notes=u'notes')
        view = self.contactType.getReadOnlyView(contactItem)
        self.assertTrue(isinstance(view, ReadOnlyNotesView))
        self.assertIdentical(view._notes, contactItem)



class ReadOnlyNotesViewTests(unittest.TestCase, TagTestingMixin):
    """
    Tests for L{ReadOnlyNotesView}.
    """
    def test_notes(self):
        """
        The I{notes} renderer of L{ReadOnlyNotesView} should return
        the C{notes} attribute of the wrapped L{Notes}.
        """
        person = Person()
        notes = Notes(person=person, notes=u'good notes')
        view = ReadOnlyNotesView(notes)
        value = renderer.get(view, 'notes')(None, div)
        self.assertTag(value, 'div', {}, [notes.notes])



class ReadOnlyPhoneNumberViewTestCase(unittest.TestCase, TagTestingMixin):
    """
    Tests for L{ReadOnlyPhoneNumberView}.
    """
    def test_number(self):
        """
        The I{number} renderer of L{ReadOnlyPhoneNumberView} should return the
        value of the wrapped L{PhoneNumber}'s C{number} attribute.
        """
        contactItem = PhoneNumber(
            person=Person(), number=u'123456')
        view = ReadOnlyPhoneNumberView(contactItem)
        value = renderer.get(view, 'number')(None, div)
        self.assertTag(value, 'div', {}, [contactItem.number])


    def test_label(self):
        """
        The I{label} renderer of L{ReadOnlyPhoneNumberView} should return the
        value of the wrapped L{PhoneNumber}'s C{label} attribute.
        """
        contactItem = PhoneNumber(
            person=Person(),
            label=PhoneNumber.LABELS.WORK,
            number=u'123456')
        view = ReadOnlyPhoneNumberView(contactItem)
        value = renderer.get(view, 'label')(None, div)
        self.assertTag(value, 'div', {}, [contactItem.label])



class ReadOnlyEmailViewTests(unittest.TestCase, TagTestingMixin):
    """
    Tests for L{ReadOnlyEmailView}.
    """
    def test_address(self):
        """
        The I{address} renderer of L{ReadOnlyEmailView} should return the
        C{address} attribute of the wrapped L{EmailAddress}.
        """
        person = Person()
        email = EmailAddress(person=person, address=u'testuser@example.org')
        view = ReadOnlyEmailView(email)
        value = renderer.get(view, 'address')(None, div)
        self.assertTag(value, 'div', {}, [email.address])



class ReadOnlyPostalAddressViewTests(unittest.TestCase, TagTestingMixin):
    """
    Tests for L{ReadOnlyPostalAddressView}.
    """
    def test_address(self):
        """
        The I{address} renderer of L{ReadOnlyPostalAddressView} should return
        the C{address} attribute of the wrapped L{PostalAddress}.
        """
        person = Person()
        address = PostalAddress(person=person, address=u'123 Street')
        view = ReadOnlyPostalAddressView(address)
        value = renderer.get(view, 'address')(None, div)
        self.assertTag(value, 'div', {}, [address.address])



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
        installOn(self.organizer, self.store)

        letters = lowercase.decode('ascii')
        for firstPrefix, lastPrefix in zip(letters, reversed(letters)):
            name = u'Alice ' + lastPrefix + u'Jones'
            person = Person(
                store=self.store,
                organizer=self.organizer,
                created=Time(),
                name=name)


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
        self.assertFalse(person.vip)


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


    def test_caseInsensitiveName(self):
        """
        L{Person.name} should not be case-sensitive.
        """
        name = u'alice'
        store = Store()
        person = Person(store=store, name=name.upper())
        self.assertEqual(
            list(store.query(Person, Person.name == name.lower())),
            [person])


    def test_editPersonChangesName(self):
        """
        L{Organizer.editPerson} should change the I{name} of the given
        L{Person}.
        """
        person = self.organizer.createPerson(u'alice')
        self.organizer.editPerson(person, u'bob', [])
        self.assertEqual(person.name, u'bob')


    def test_editPersonEditsContactInfo(self):
        """
        L{Organizer.editPerson} should call I{editContactItem} on each element
        of the edits sequence it is passed.
        """
        person = self.organizer.createPerson(u'alice')
        contactType = StubContactType((), None, None)
        contactItem = object()
        contactInfo = {u'foo': u'bar'}
        self.organizer.editPerson(
            person,
            u'alice',
            [(contactType, ListChanges(
            [], [EditObject(contactItem, contactInfo)], []))])
        self.assertEqual(
            contactType.editedContacts,
            [(contactItem, contactInfo)])


    def test_editPersonEditsUnrepeatableContactInfo(self):
        """
        Like L{test_editPersonEditsContactInfo}, but for the case where the
        contact type doesn't support multiple contact items.
        """
        person = self.organizer.createPerson(u'alice')
        contactItem = object()
        contactType = StubContactType(
            (), None, contactItems=[contactItem],
            allowMultipleContactItems=False)
        contactInfo = {u'foo': u'bar'}
        self.organizer.editPerson(
            person, u'alice', [(contactType, contactInfo)])
        self.assertEqual(
            contactType.editedContacts,
            [(contactItem, contactInfo)])


    def test_editPersonCreatesContactInfo(self):
        """
        L{Organizer.editPerson} should call I{createContactItem} on each
        element in the create sequence it is passed.
        """
        person = self.organizer.createPerson(u'alice')
        contactType = StubContactType((), None, None, createContactItems=True)
        contactInfo = {u'foo': u'bar'}
        createdObjects = []
        def setter(createdObject):
            createdObjects.append(createdObject)
        self.organizer.editPerson(
            person,
            u'alice',
            [(contactType, ListChanges(
            [CreateObject(contactInfo, setter)], [], []))])
        self.assertEqual(
            contactType.createdContacts, [(person, contactInfo)])
        self.assertEqual(createdObjects, [(person, contactInfo)])


    def test_editPersonContactCreationNotification(self):
        """
        Contact items created through L{Organizer.editPerson} should be sent
        to L{IOrganizerPlugin.contactItemCreated} for all L{IOrganizerPlugin}
        powerups on the store.
        """
        contactType = StubContactType((), None, None, createContactItems=True)
        contactInfo = {u'foo': u'bar'}
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        person = self.organizer.createPerson(u'alice')
        self.organizer.editPerson(
            person, person.name,
            [(contactType,
              ListChanges([CreateObject(contactInfo,
                                                 lambda obj: None)],
                                   [], []))])
        self.assertEqual(
            observer.createdContactItems, [(person, contactInfo)])


    def test_editPersonContactEditNotification(self):
        """
        Contact items edit through L{Organizer.editPerson} should be sent to
        L{IOrganizerPlugin.contactItemEdited} for all L{IOrganizerPlugin}
        powerups on the store.
        """
        contactType = StubContactType((), None, None)
        contactItem = object()
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        person = self.organizer.createPerson(u'alice')
        self.organizer.editPerson(
            person, person.name,
            [(contactType,
              ListChanges([], [EditObject(contactItem, {})], []))])
        self.assertEqual(
            observer.editedContactItems, [contactItem])


    def test_editPersonDeletesContactInfo(self):
        """
        L{Organizer.editPerson} should call L{deleteFromStore} on each element
        in the delete sequence it is passed.
        """
        class DeletableObject(object):
            deleted = False
            def deleteFromStore(self):
                self.deleted = True

        person = self.organizer.createPerson(u'alice')
        contactType = StubContactType((), None, None)
        contactItem = DeletableObject()
        self.organizer.editPerson(
            person,
            u'alice',
            [(contactType, ListChanges([], [], [contactItem]))])
        self.assertTrue(contactItem.deleted)


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


    def test_editPersonNotifiesPlugins(self):
        """
        L{Organizer.editPerson} should call C{personNameChanged} on all
        L{IOrganizerPlugin} powerups on the store.
        """
        nickname = u'test person'
        newname = u'alice'
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        person = self.organizer.createPerson(nickname)
        self.organizer.editPerson(person, newname, [])
        self.assertEqual(
            observer.renamedPeople,
            [(newname, nickname)])


    def test_createVeryImportantPerson(self):
        """
        L{Organizer.createPerson} should set L{Person.vip} to match the value
        it is passed for the C{vip} parameter, and issue a deprecation
        warning.
        """
        self.assertWarns(
            DeprecationWarning,
            "Usage of Organizer.createPerson's 'vip' parameter is deprecated",
            people.__file__,
            lambda: self.organizer.createPerson(u'alice', True))
        alice = self.store.findUnique(Person, Person.name == u'alice')
        self.assertTrue(alice.vip)


    def test_createPersonNoVIP(self):
        """
        L{Organizer.createPerson} shouldn't issue a warning if no C{vip}
        argument is passed.
        """
        originalWarnExplicit = warnings.warn_explicit
        def warnExplicit(*args):
            self.fail('Organizer.createPerson warned us: %r' % (args[0],))
        try:
            warnings.warn_explicit = warnExplicit
            person = self.organizer.createPerson(u'alice')
        finally:
            warnings.warn_explicit = originalWarnExplicit


    def test_noMugshot(self):
        """
        L{Person.getMugshot} should return C{None} for a person with whom no
        mugshot item is associated.
        """
        person = Person(store=self.store)
        self.assertIdentical(person.getMugshot(), None)


    def test_getMugshot(self):
        """
        L{Person.getMugshot} should return the L{Mugshot} item which refers to
        the person on which it is called when one exists.
        """
        store = Store(filesdir=self.mktemp())
        person = Person(store=store)
        image = Mugshot(
            store=store, type=u"image/png",
            body=store.filesdir.child('a'),
            smallerBody=store.filesdir.child('b'),
            person=person)
        self.assertIdentical(person.getMugshot(), image)


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
        L{Organizer.createContactItem} should call L{contactItemCreated} on
        all L{IOrganizerPlugin} powerups on the store.
        """
        nickname = u'test person'
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        person = self.organizer.createPerson(nickname)
        contactType = StubContactType((), None, None)
        parameters = {'key': u'value'}
        contactItem = self.organizer.createContactItem(
            contactType, person, parameters)
        self.assertEqual(len(observer.createdContactItems), 1)
        [(observedPerson, observedParameters)] = observer.createdContactItems
        self.assertIdentical(person, observedPerson)
        self.assertEqual(parameters, observedParameters)


    def test_notificationSkippedForUncreatedContactItems(self):
        """
        L{Organizer.createContactItem} should not call L{contactItemCreated}
        on any L{IOrganizerPlugin} powerups on the store if
        L{IContactType.createContactItem} returns C{None} to indicate that it
        is not creating a contact item.
        """
        nickname = u'test person'
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        person = self.organizer.createPerson(nickname)
        contactType = StubContactType((), None, None, False)
        parameters = {'key': u'value'}
        contactItem = self.organizer.createContactItem(
            contactType, person, parameters)
        self.assertEqual(observer.createdContactItems, [])


    def test_editContactItemNotifiesPlugins(self):
        """
        L{Organizer.editContactItem} should call L{contactItemEdited} on all
        L{IOrganizerPlugin} powerups in the store.
        """
        observer = StubOrganizerPlugin(store=self.store)
        self.store.powerUp(observer, IOrganizerPlugin)
        contactType = StubContactType((), None, None)
        contactItem = object()
        self.organizer.editContactItem(contactType, contactItem, {})
        self.assertEqual(observer.editedContactItems, [contactItem])


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

        self.assertEqual(plugins[1].createdPeople,
                         [organizer.storeOwnerPerson, person])


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
            list(self.organizer.getContactTypes())[builtinContactTypeCount:],
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

        self.assertEqual(contactTypes[builtinContactTypeCount:], [])


    def test_getContactCreationParameters(self):
        """
        L{Organizer.getContactCreationParameters} should return a list
        containing a L{ListChangeParameter} for each contact type available
        in the system which allows multiple contact items.
        """
        contactTypes = [StubContactType(
            (), None, None,
            allowMultipleContactItems=True,
            theDescriptiveIdentifier=u'Very Descriptive')]
        contactPowerup = StubOrganizerPlugin(
            store=self.store, contactTypes=contactTypes)
        self.store.powerUp(contactPowerup, IOrganizerPlugin)

        parameters = list(self.organizer.getContactCreationParameters())
        self.assertEqual(len(parameters), builtinContactTypeCount + 1)
        self.assertTrue(
            isinstance(parameters[builtinContactTypeCount], ListChangeParameter))
        self.assertEqual(
            parameters[builtinContactTypeCount].modelObjectDescription,
            u'Very Descriptive')
        self.assertEqual(
            parameters[builtinContactTypeCount].name,
            qual(StubContactType))


    def test_getContactCreationParametersUnrepeatable(self):
        """
        L{Organizer.getContactCreationParameters} should return a list
        containing a L{FormParameter} for each contact type which doesn't
        support multiple contact items.
        """
        contactTypeParameters = [Parameter('foo', TEXT_INPUT, lambda x: None)]
        contactTypes = [StubContactType(
            contactTypeParameters, None, None,
            allowMultipleContactItems=False)]
        contactPowerup = StubOrganizerPlugin(
            store=self.store, contactTypes=contactTypes)
        self.store.powerUp(contactPowerup, IOrganizerPlugin)

        parameters = list(self.organizer.getContactCreationParameters())
        liveFormParameter = parameters[builtinContactTypeCount]
        self.assertTrue(isinstance(liveFormParameter, FormParameter))
        self.assertEqual(liveFormParameter.name, qual(StubContactType))
        liveForm = liveFormParameter.form
        self.assertTrue(isinstance(liveForm, LiveForm))
        self.assertEqual(liveForm.parameters, contactTypeParameters)


    def test_getContactEditorialParameters(self):
        """
        L{Organizer.getContactEditorialParameters} should return a list
        containing a L{ListChangeParameter} for each contact type available in
        the system which supports multiple contact items.
        """
        contactTypes = [StubContactType(
            (), None, [], theDescriptiveIdentifier=u'So Descriptive')]
        contactPowerup = StubOrganizerPlugin(
            store=self.store, contactTypes=contactTypes)
        self.store.powerUp(contactPowerup, IOrganizerPlugin)

        person = self.organizer.createPerson(u'nickname')

        parameters = list(self.organizer.getContactEditorialParameters(person))

        self.assertIdentical(
            parameters[builtinContactTypeCount][0], contactTypes[0])
        self.failUnless(
            isinstance(
                parameters[builtinContactTypeCount][1],
                ListChangeParameter))
        self.assertEqual(
            parameters[builtinContactTypeCount][1].modelObjectDescription,
            u'So Descriptive')


    def test_getContactEditorialParametersNone(self):
        """
        The L{ListChangeParameter} returned by
        L{Organizer.getContactEditorialParameters} for a particular
        L{IContactType} should not have a model object or defaults dict if the
        L{IContactType} indicates that the contact item is immutable (by
        returning C{None} from its  C{getParameters} implementation).
        """
        class PickyContactType(StubContactType):
            def getParameters(self, contactItem):
                return self.parameters[contactItem]

        mutableContactItem = object()
        immutableContactItem = object()

        makeParam = lambda default=None: Parameter(
            'foo', TEXT_INPUT, lambda x: None, default=default)

        contactType = PickyContactType(
            {mutableContactItem: [makeParam('the default')],
             None: [makeParam(None)],
             immutableContactItem: None},
            None,
            [mutableContactItem, immutableContactItem])

        contactTypes = [contactType]
        contactPowerup = StubOrganizerPlugin(
            store=self.store, contactTypes=contactTypes)
        self.store.powerUp(contactPowerup, IOrganizerPlugin)
        person = self.organizer.createPerson(u'nickname')
        parameters = list(
            self.organizer.getContactEditorialParameters(person))

        (gotContactType, parameter) = parameters[builtinContactTypeCount]
        self.assertEqual(parameter.modelObjects, [mutableContactItem])
        self.assertEqual(parameter.defaults, [{'foo': 'the default'}])


    def test_getContactEditorialParametersUnrepeatable(self):
        """
        L{Organizer.getContactEditorialParameters} should return a list
        containing a L{FormParameter} for each contact type available in the
        system which doesn't support multiple contact items.
        """
        contactTypeParameters = [Parameter('foo', TEXT_INPUT, lambda x: x)]
        contactTypes = [StubContactType(
            contactTypeParameters, None, [None],
            allowMultipleContactItems=False)]

        contactPowerup = StubOrganizerPlugin(
            store=self.store, contactTypes=contactTypes)
        self.store.powerUp(contactPowerup, IOrganizerPlugin)

        person = self.organizer.createPerson(u'nickname')

        parameters = list(self.organizer.getContactEditorialParameters(person))

        (contactType, liveFormParameter) = parameters[builtinContactTypeCount]
        self.assertIdentical(contactType, contactTypes[0])
        self.assertTrue(isinstance(liveFormParameter, FormParameter))
        self.assertEqual(liveFormParameter.name, qual(StubContactType))
        liveForm = liveFormParameter.form
        self.assertTrue(isinstance(liveForm, LiveForm))
        self.assertEqual(liveForm.parameters, contactTypeParameters)


    def test_getContactEditorialParametersDefaults(self):
        """
        L{Organizer.getContactEditorialParameters} should return some
        parameters with correctly initialized lists of defaults and model
        objects.
        """
        person = self.organizer.createPerson(u'nickname')
        contactItems = [PostalAddress(store=self.store, person=person, address=u'1'),
                        PostalAddress(store=self.store, person=person, address=u'2')]
        editParameters = list(self.organizer.getContactEditorialParameters(person))
        (editType, editParameter) = editParameters[2]
        self.assertEqual(
            editParameter.defaults, [{u'address': u'1'}, {u'address': u'2'}])
        self.assertEqual(
            editParameter.modelObjects, contactItems)


    def test_navigation(self):
        """
        L{Organizer.getTabs} should return a single tab, 'People', that points
        to itself.
        """
        tabs = self.organizer.getTabs()
        self.assertEqual(len(tabs), 1)
        tab = tabs[0]
        self.assertEqual(tab.name, "People")
        self.assertEqual(tab.storeID, self.organizer.storeID)
        self.assertEqual(tab.children, ())
        self.assertEqual(tab.authoritative, True)
        self.assertEqual(tab.linkURL, None)



class POBox(Item):
    number = text()



def _keyword(contactType):
    return contactType.uniqueIdentifier().encode('ascii')


CONTACT_EMAIL = u'jlp@starship.enterprise'
CONTACT_ADDRESS = u'123 Street Rd'
def createAddPersonContactInfo(store):
    """
    Create a structure suitable to be passed to AddPersonFragment.addPerson.

    Since the structure keeps changing slightly, this lets some tests be
    independent of those details and so avoids requiring them to change every
    time the structure does.
    """
    return {
        _keyword(EmailContactType(store)): ListChanges(
            [CreateObject({u'email': CONTACT_EMAIL}, lambda x: None)],
            [], []),
        _keyword(PostalContactType()): ListChanges(
            [CreateObject({u'address': CONTACT_ADDRESS}, lambda x: None)],
            [], [])}


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


    def test_docFactory(self):
        """
        L{AddPersonFragment.docFactory.load} should not return C{None}.
        """
        self.assertNotIdentical(
            AddPersonFragment(self.organizer).docFactory.load(),
            None)


    def test_addPersonParameters(self):
        """
        L{AddPersonFragment.render_addPersonForm} should return a L{LiveForm}
        with several fixed parameters and any parameters from available
        powerups.
        """
        addPersonFrag = AddPersonFragment(self.organizer)

        # Whatever is in _baseParameters should end up in the resulting form's
        # parameters.  Explicitly define _baseParameters here so that changes
        # to the actual value don't affect this test.  The actual value is
        # effectively a declaration, so the only thing one could test about it
        # is that it is equal to itself, anyway.
        addPersonFrag._baseParameters = [
            Parameter('foo', TEXT_INPUT, unicode, 'Foo')]

        # With no plugins, only the parameters for the builtin contact types
        # should be returned
        addPersonForm = addPersonFrag.render_addPersonForm(None, None)
        self.assertEqual(
            len(addPersonForm.parameters), builtinContactTypeCount + 1)

        contactTypes = [StubContactType((), None, None)]
        observer = StubOrganizerPlugin(
            store=self.store, contactTypes=contactTypes)
        self.store.powerUp(observer, IOrganizerPlugin)

        addPersonForm = addPersonFrag.render_addPersonForm(None, None)
        self.assertEqual(
            len(addPersonForm.parameters), builtinContactTypeCount + 2)


    def test_addPersonWithContactItems(self):
        """
        L{AddPersonFragment.addPerson} should give the L{IContactType} plugins
        their information from the form submission.
        """
        contactType = StubContactType((), None, None)
        observer = StubOrganizerPlugin(
            store=self.store, contactTypes=[contactType])
        self.store.powerUp(observer, IOrganizerPlugin)

        addPersonFragment = AddPersonFragment(self.organizer)

        values = {u'stub': 'value'}
        addPersonFragment.addPerson(
            u'nickname',
            **{_keyword(contactType): ListChanges(
                [CreateObject(values, lambda x: None)], [], [])})

        person = self.store.findUnique(
            Person, Person.storeID != self.organizer.storeOwnerPerson.storeID)
        self.assertEqual(contactType.createdContacts, [(person, values)])


    def test_addPersonWithUnrepeatableContactItems(self):
        """
        Similar to L{test_addPersonWithContactItems}, but for the case where
        the L{IContactType} doesn't allow multiple contact items.
        """
        contactType = StubContactType(
            [Parameter('stub', TEXT_INPUT, lambda x: x)], None, None,
            allowMultipleContactItems=False)
        observer = StubOrganizerPlugin(
            store=self.store, contactTypes=[contactType])
        self.store.powerUp(observer, IOrganizerPlugin)

        addPersonFragment = AddPersonFragment(self.organizer)

        values = {u'stub': 'value'}
        addPersonFragment.addPerson(
            u'nickname', **{_keyword(contactType): values})

        person = self.store.findUnique(
            Person, Person.storeID != self.organizer.storeOwnerPerson.storeID)
        self.assertEqual(contactType.createdContacts, [(person, values)])


    def test_addPersonWithBuiltinContactItems(self):
        """
        L{AddPersonFragment.addPerson} should work correctly when creating
        contact items with builtin contact types.
        """
        addPersonFrag = AddPersonFragment(self.organizer)
        addPersonFrag.addPerson(
            u'Captain P.', **createAddPersonContactInfo(self.store))

        person = self.store.findUnique(
            Person, Person.storeID != self.organizer.storeOwnerPerson.storeID)
        self.assertEquals(person.name, 'Captain P.')

        email = self.store.findUnique(
            EmailAddress, EmailAddress.person == person)
        self.assertEquals(email.address, CONTACT_EMAIL)

        pa = self.store.findUnique(
            PostalAddress, PostalAddress.person == person)
        self.assertEqual(pa.address, CONTACT_ADDRESS)


    def test_addPersonCallsCreateSetter(self):
        """
        L{AddPersonFragment.addPerson} should call the L{CreateObject.setter}
        on the appropriate object, for each item it creates.
        """
        def setter(object):
            setter.objects.append(object)
        setter.objects = []

        addPersonFragment = AddPersonFragment(self.organizer)
        addPersonFragment.addPerson(
            u'Name',
            **{_keyword(EmailContactType(self.store)): ListChanges(
                [CreateObject({u'email': u'x@y.z'}, setter)], [], [])})

        person = self.store.findUnique(
            Person, Person.storeID != self.organizer.storeOwnerPerson.storeID)
        email = self.store.findUnique(EmailAddress, EmailAddress.person == person)
        self.assertEqual(setter.objects, [email])


    def test_addVeryImportantPerson(self):
        """
        L{AddPersonFragment.addPerson} should use L{VIPPersonContactType} to
        set the C{vip} attribute of the new person.
        """
        people = []
        argument = {u'stub': 'value'}
        view = AddPersonFragment(self.organizer)
        view.addPerson(
            u'alice', **{_keyword(VIPPersonContactType()): {u'vip': True}})
        alice = self.store.findUnique(
            Person, Person.storeID != self.organizer.storeOwnerPerson.storeID)
        self.assertTrue(alice.vip)


    def test_addPersonValueError(self):
        """
        L{AddPersonFragment.addPerson} raises L{InputError} if
        L{AddPersonFragment._addPerson} raises a L{ValueError}.
        """
        addPersonFragment = AddPersonFragment(self.organizer)
        def stubAddPerson(*a, **kw):
            raise ValueError("Stub nickname rejection")
        addPersonFragment._addPerson = stubAddPerson
        exception = self.assertRaises(
            InputError, addPersonFragment.addPerson, u'nickname')
        self.assertEqual(exception.args, ("Stub nickname rejection",))
        self.assertTrue(isinstance(exception.args[0], unicode))


    def test_linkToPerson(self):
        """
        Verify that L{Organizer.linkToPerson} generates the correct URL, with
        the web ID of the person item appended to the organizer's url.
        """
        privapp = self.store.findUnique(PrivateApplication)
        p = Person(store=self.store)
        self.assertEqual(self.organizer.linkToPerson(p),
                         (privapp.linkTo(self.organizer.storeID)
                          + '/'
                          + privapp.toWebID(p)))


    def test_urlForViewState(self):
        """
        L{Organizer.urlForViewState} should generate a valid, correctly quoted
        url.
        """
        organizerURL = IWebTranslator(self.store).linkTo(
            self.organizer.storeID)
        person = self.organizer.createPerson(u'A Person')
        self.assertEqual(
            str(self.organizer.urlForViewState(
                person, ORGANIZER_VIEW_STATES.EDIT)),
            organizerURL + '?initial-person=A%20Person&initial-state=edit')



class StubPerson(object):
    """
    Stub implementation of L{Person} used for testing.

    @ivar contactItems: A list of three-tuples of the arguments passed to
        createContactInfoItem.
    """
    name = u'person'

    def __init__(self, contactItems):
        self.contactItems = contactItems
        self.store = object()


    def createContactInfoItem(self, cls, attr, value):
        """
        Record the creation of a new contact item.
        """
        self.contactItems.append((cls, attr, value))


    def getContactInfoItems(self, itemType, valueColumn):
        """
        Return an empty list.
        """
        return []


    def getMugshot(self):
        """
        Return C{None} since there is no mugshot.
        """
        return None


    def getDisplayName(self):
        """
        Return a name of some sort.
        """
        return u"Alice"


    def getEmailAddress(self):
        """
        Return an email address.
        """
        return u"alice@example.com"



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


    def test_flattenableWithoutExplicitDocFactory(self):
        """
        L{flatten} should not raise an exception when passed a
        L{ContactInfoFragment} instance which has not had its C{docFactory} set
        explicitly.
        """
        store = Store()
        organizer = Organizer(store=store)
        installOn(organizer, store)
        person = organizer.createPerson(u'testuser')
        fragment = ContactInfoFragment(person)
        renderLiveFragment(fragment)



class PersonDetailFragmentTests(unittest.TestCase):
    """
    Tests for L{xmantissa.people.PersonDetailFragment}.
    """
    def test_mugshotUploadForm(self):
        """
        L{PersonDetailFragment}'s I{mugshotUploadForm} child should return a
        L{MugshotUploadForm}.
        """
        person = StubPerson([])
        person.organizer = StubOrganizer()
        fragment = PersonDetailFragment(person)
        (resource, segments) = fragment.locateChild(
            None, ('mugshotUploadForm',))
        self.assertTrue(isinstance(resource, MugshotUploadForm))
        self.assertIdentical(resource.person, person)


    def test_getPersonURL(self):
        """
        Test that L{getPersonURL} returns the URL for the Person.
        """
        person = StubPerson([])
        person.organizer = StubOrganizer()
        self.assertEqual(getPersonURL(person), "/person/Alice")


    def test_mugshotChild(self):
        """
        L{PersonDetailFragment}'s I{mugshot} child should return a
        L{MugshotResource} wrapping the person's L{Mugshot} item.
        """
        store = Store(filesdir=self.mktemp())
        organizer = Organizer(store=store)
        installOn(organizer, store)
        person = organizer.createPerson(u'Alice')
        mugshot = Mugshot(
            store=store,
            person=person,
            type=u'image/png',
            body=store.filesdir.child('a'),
            smallerBody=store.filesdir.child('b'))
        fragment = PersonDetailFragment(person)
        (res, segments) = fragment.locateChild(None, ('mugshot',))
        self.assertTrue(isinstance(res, MugshotResource))
        self.assertIdentical(res.mugshot, mugshot)
        self.assertEqual(segments, ())


    def test_mugshotChildNoMugshot(self):
        """
        Similar to L{test_displayMugshot}, but for the case where the person
        has no mugshot.  The returned L{MugshotResource} should wrap a
        L{Mugshot} item with attributes pointing at the mugshot placeholder
        images.
        """
        store = Store(self.mktemp())
        organizer = Organizer(store=store)
        installOn(organizer, store)
        person = organizer.createPerson(u'Alice')
        fragment = PersonDetailFragment(person)
        (res, segments) = fragment.locateChild(None, ('mugshot',))
        self.assertTrue(isinstance(res, MugshotResource))
        mugshot = res.mugshot
        self.assertTrue(isinstance(mugshot, Mugshot))
        self.assertIdentical(mugshot.store, None)
        self.assertIdentical(mugshot.person, person)
        self.assertEqual(mugshot.type, u'image/png')
        imageDir = FilePath(people.__file__).parent().child(
            'static').child('images')
        self.assertEqual(
            mugshot.body, imageDir.child('mugshot-placeholder.png'))
        self.assertEqual(
            mugshot.smallerBody,
            imageDir.child('smaller-mugshot-placeholder.png'))



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
    def setUp(self):
        """
        Make an L{Organizer}.
        """
        self.store = Store()
        self.organizer = Organizer(store=self.store)
        installOn(self.organizer, self.store)


    def test_scrollingAttributes(self):
        """
        L{PersonScrollingFragment} should have the attributes its base class
        wants to use.
        """
        baseConstraint = object()
        fragment = PersonScrollingFragment(
            self.organizer, baseConstraint, Person.name,
            StubTranslator(None, None))
        self.assertIdentical(fragment.baseConstraint, baseConstraint)
        self.assertIdentical(
            fragment.currentSortColumn.sortAttribute(), Person.name)
        self.assertIdentical(fragment.itemType, Person)
        self.assertEqual(len(fragment.columns), 2)
        self.assertEqual(fragment.columns['name'], Person.name)
        self.assertTrue(isinstance(fragment.columns['vip'], UnsortableColumn))
        self.assertEqual(fragment.columns['vip'].attribute, Person.vip)


    def test_initialArguments(self):
        """
        L{PersonScrollingFragment.getInitialArguments} should include the
        store owner person's name in its result.
        """
        storeOwnerPersonName = u'Store Owner'
        self.organizer.storeOwnerPerson.name = storeOwnerPersonName
        fragment = PersonScrollingFragment(
            self.organizer, object(), Person.name, StubTranslator(None, None))
        self.assertEqual(
            fragment.getInitialArguments(),
            (ScrollingElement.getInitialArguments(fragment)
                + [storeOwnerPersonName]))



class StubOrganizer(object):
    """
    Mimic some of the API presented by L{Organizer}.

    @ivar people: A C{dict} mapping C{unicode} strings giving person names to
    person objects.  These person objects will be returned from appropriate
    calls to L{personByName}.

    @ivar peoplePluginList: a C{list} of L{IOrganizerPlugin}s.

    @ivar contactTypes: a C{list} of L{IContactType}s.

    @ivar editedPeople: A list of the arguments which have been passed to the
    C{editPerson} method.

    @ivar deletedPeople: A list of the arguments which have been passed to the
    C{deletePerson} method.

    @ivar contactEditorialParameters: A mapping of people to lists.  When
    passed a person, L{getContactEditorialParameters} will return the
    corresponding list.
    """
    _webTranslator = StubTranslator(None, None)

    def __init__(self, store=None, peoplePlugins=None, contactTypes=None,
            deletedPeople=None, editedPeople=None,
            contactEditorialParameters=None):
        self.store = store
        self.people = {}
        if peoplePlugins is None:
            peoplePlugins = []
        if contactTypes is None:
            contactTypes = []
        if deletedPeople is None:
            deletedPeople = []
        if editedPeople is None:
            editedPeople = []
        if contactEditorialParameters is None:
            contactEditorialParameters = []
        self.peoplePluginList = peoplePlugins
        self.contactTypes = contactTypes
        self.deletedPeople = deletedPeople
        self.editedPeople = editedPeople
        self.contactEditorialParameters = contactEditorialParameters


    def peoplePlugins(self, person):
        return [p.personalize(person) for p in self.peoplePluginList]


    def personByName(self, name):
        return self.people[name]


    def lastNameOrder(self):
        return None


    def deletePerson(self, person):
        self.deletedPeople.append(person)


    def editPerson(self, person, name, edits):
        self.editedPeople.append((person, name, edits))


    def getContactEditorialParameters(self, person):
        return self.contactEditorialParameters[person]


    def getContactTypes(self):
        return self.contactTypes


    def linkToPerson(self, person):
        return "/person/" + person.getDisplayName()



class OrganizerFragmentTests(unittest.TestCase):
    """
    Tests for L{OrganizerFragment}.

    @ivar contactTypes: A list of L{StubContactType} instances which will be
        returned by the C{getContactTypes} method of the stub organizer used by
        these tests.

    @ivar organizer: The L{StubOrganizer} which is used by these tests.
    @ivar fragment: An L{OrganizerFragment} to test.
    @ivar deletedPeople: A list of the arguments which have been passed to the
        C{deletePerson} method of L{organizer}.
    """
    def setUp(self):
        """
        Create an L{OrganizerFragment} wrapped around a double for
        L{Organizer}.
        """
        deletedPeople = []
        contactTypes = []
        peoplePlugins = []

        self.store = Store()
        self.contactTypes = contactTypes
        self.organizer = StubOrganizer(
            self.store, peoplePlugins, contactTypes, deletedPeople)
        self.fragment = OrganizerFragment(self.organizer)
        self.deletedPeople = deletedPeople
        self.peoplePlugins = peoplePlugins


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


    def test_getImportPeople(self):
        """
        L{OrganizerFragment.getImportPeople} should return an
        L{ImportPeopleWidget}.
        """
        widget = expose.get(self.fragment, 'getImportPeople')()
        self.assertTrue(isinstance(widget, ImportPeopleWidget))
        self.assertIdentical(widget.organizer, self.organizer)
        self.assertIdentical(widget.fragmentParent, self.fragment)


    def test_getEditPerson(self):
        """
        L{OrganizerFragment.getEditPerson} should return an
        L{EditPersonView}.
        """
        name = u'testuser'
        person = Person()
        self.organizer.people[name] = person

        editPersonFragment = expose.get(
            self.fragment, 'getEditPerson')(name)
        self.assertTrue(isinstance(editPersonFragment, EditPersonView))
        self.assertIdentical(editPersonFragment.person, person)
        self.assertIdentical(editPersonFragment.fragmentParent, self.fragment)


    def test_deletePerson(self):
        """
        L{OrganizerFragment.deletePerson} should call
        L{Organizer.deletePerson}.
        """
        name = u'testuser'
        person = Person()
        self.organizer.people[name] = person

        expose.get(self.fragment, 'deletePerson', None)(name)
        self.assertEqual(self.fragment.organizer.deletedPeople, [person])


    def test_getContactInfoWidget(self):
        """
        L{OrganizerFragment.getContactInfoWidget} should return a
        L{ReadOnlyContactInfoView} for the named person.
        """
        name = u'testuser'
        person = Person()
        self.organizer.people[name] = person

        widget = expose.get(
            self.fragment, 'getContactInfoWidget')(name)
        self.assertTrue(isinstance(widget, ReadOnlyContactInfoView))
        self.assertIdentical(widget.person, person)


    def test_initialArgumentsNoInitialPerson(self):
        """
        When L{Organizer.initialPerson} is C{None},
        L{Organizer.getInitialArguments} should be a one-element tuple
        containing the name of the store owner person.
        """
        storeOwnerPersonName = u'Alice'
        self.organizer.storeOwnerPerson = Person(
            name=storeOwnerPersonName)
        self.assertEqual(
            self.fragment.getInitialArguments(),
            (storeOwnerPersonName,))


    def test_initialArgumentsInitialPerson(self):
        """
        When L{Organizer.initialPerson} is not C{None},
        L{Organizer.getInitialArguments} should be a three-element tuple
        containing the name of the store owner person, the name of the initial
        person, and the initial view state.
        """
        storeOwnerPersonName = u'Alice'
        initialPersonName = u'Bob'
        initialState = ORGANIZER_VIEW_STATES.EDIT

        self.organizer.storeOwnerPerson = Person(
            name=storeOwnerPersonName)
        initialPerson = Person(name=initialPersonName)

        fragment = OrganizerFragment(
            self.organizer, initialPerson, initialState)
        self.assertEqual(
            fragment.getInitialArguments(),
            (storeOwnerPersonName, initialPersonName, initialState))



class OrganizerFragmentBeforeRenderTestCase(unittest.TestCase):
    """
    Tests for L{OrganizerFragment.beforeRender}.  These tests require more
    expensive setup than is provided by L{OrganizerFragmentTests}.
    """
    def setUp(self):
        """
        Make a substore with a L{PrivateApplication} and an L{Organizer}.
        """
        self.siteStore = Store(filesdir=self.mktemp())
        def siteStoreTxn():
            Mantissa().installSite(self.siteStore, '/')
            userAccount = Create().addAccount(
                self.siteStore,
                u'testuser',
                u'example.com',
                u'password')
            self.userStore = userAccount.avatars.open()
        self.siteStore.transact(siteStoreTxn)

        def userStoreTxn():
            self.organizer = Organizer(store=self.userStore)
            installOn(self.organizer, self.userStore)
            self.fragment = OrganizerFragment(self.organizer)
        self.userStore.transact(userStoreTxn)


    def _makeContextWithRequestArgs(self, args):
        """
        Make a context which contains a request with args C{args}.
        """
        request = FakeRequest()
        request.args = args
        return context.PageContext(
            tag=None, parent=context.RequestContext(
                tag=request))


    def test_validPersonAndValidState(self):
        """
        L{OrganizerFragment.beforeRender} should correctly intialize the
        L{OrganizerFragment} if a valid person name and valid initial view
        state are present in the query args.
        """
        person = self.organizer.createPerson(u'Alice')
        self.fragment.beforeRender(
            self._makeContextWithRequestArgs(
                {'initial-person': [person.name],
                 'initial-state': [ORGANIZER_VIEW_STATES.EDIT]}))
        self.assertIdentical(self.fragment.initialPerson, person)
        self.assertEqual(
            self.fragment.initialState, ORGANIZER_VIEW_STATES.EDIT)


    def test_invalidPersonAndValidState(self):
        """
        L{OrganizerFragment.beforeRender} shouldn't modify the
        L{OrganizerFragment} if an invalid person name and valid view state
        are present in the query args.
        """
        self.fragment.beforeRender(
            self._makeContextWithRequestArgs(
                {'initial-person': ['Alice'],
                 'initial-state': [ORGANIZER_VIEW_STATES.EDIT]}))
        self.assertIdentical(self.fragment.initialPerson, None)
        self.assertIdentical(self.fragment.initialState, None)


    def test_validPersonAndInvalidState(self):
        """
        Similar to L{test_invalidPersonAndValidState}, but for a valid person
        name and invalid initial view state.
        """
        person = self.organizer.createPerson(u'Alice')
        self.fragment.beforeRender(
            self._makeContextWithRequestArgs(
                {'initial-person': ['Alice'],
                 'initial-state': ['invalid view state']}))
        self.assertIdentical(self.fragment.initialPerson, None)
        self.assertIdentical(self.fragment.initialState, None)



class AddPersonFragmentTests(unittest.TestCase):
    """
    Tests for L{AddPersonFragment}.
    """
    def test_jsClass(self):
        """
        L{AddPersonFragment} should have a customized C{jsClass} in order to
        expose methods on its L{LiveForm}.
        """
        self.assertEqual(AddPersonFragment.jsClass, u'Mantissa.People.AddPerson')


    def test_renders(self):
        """
        An L{AddPersonFragment} should be renderable.
        """
        store = Store()
        installOn(PrivateApplication(store=store), store)
        organizer = Organizer(store=store)
        fragment = AddPersonFragment(organizer)
        result = renderLiveFragment(fragment)
        self.assertTrue(isinstance(result, str))


    def test_addPersonFormRenderer(self):
        """
        L{AddPersonFragment.render_addPersonForm} should return a L{LiveForm}
        with a customized I{jsClass} attribute.
        """
        store = Store()
        organizer = Organizer(store=store)
        fragment = AddPersonFragment(organizer)
        form = fragment.render_addPersonForm(None, None)
        self.assertTrue(isinstance(form, LiveForm))
        self.assertEqual(form.jsClass, u'Mantissa.People.AddPersonForm')



class ImportPeopleWidgetTests(unittest.TestCase):
    """
    Tests for L{ImportPeopleWidget}.
    """

    def test_parseAddresses(self):
        """
        L{_parseAddresses} should extract valid-looking names and addresses.
        """
        def _assert(input, expected):
            self.assertEqual(ImportPeopleWidget._parseAddresses(input),
                             expected)

        # Empty
        for s in [u'', u'  ', u'<>', u',', u'<>, <>']:
            _assert(s, [])
        # Name defaulting to local-part
        _assert(u'alice@example.com', [(u'alice', u'alice@example.com')])
        _assert(u' alice@example.com, ', [(u'alice', u'alice@example.com')])
        # Separators and display names
        for sep in u', ', u'\n', u', foo <>, ':
            _assert(sep.join([u'alice@example.com', u'bob@example.com']),
                    [(u'alice', u'alice@example.com'),
                     (u'bob', u'bob@example.com')])
            _assert(sep.join([u'<Alice.Allison@example.com>',
                              u'Alice Allison <alice@example.com>',
                              u'"Bob Boberton" <bob@example.com>']),
                    [(u'Alice.Allison', u'Alice.Allison@example.com'),
                     (u'Alice Allison', u'alice@example.com'),
                     (u'Bob Boberton', u'bob@example.com')])


    def test_importAddresses(self):
        """
        L{ImportPeopleWidget.importAddresses} should create entries for the
        given addresses (ignoring names/addresses that exist already).
        """
        store = Store()
        organizer = Organizer(store=store)
        owner = organizer.storeOwnerPerson
        importFragment = ImportPeopleWidget(organizer)

        self.assertEqual(list(store.query(Person)), [owner])
        importFragment.importAddresses([])
        self.assertEqual(list(store.query(Person)), [owner])

        addresses = [(u'Alice', u'alice@example.com'),
                     (u'Bob', u'bob@example.com')]
        # Import twice to check idempotency, and make sure both the name and
        # address are checked.
        for input in [addresses, addresses, [(u'Alice', u'chaff'),
                                             (u'chaff', u'bob@example.com')]]:
            importFragment.importAddresses(input)
            self.assertEqual(set((p.name, p.getEmailAddress())
                                 for p in store.query(Person)
                                 if p is not owner),
                             set(addresses))



class ReadOnlyContactInfoViewTestCase(unittest.TestCase):
    """
    Tests for L{ReadOnlyContactInfoView}.
    """
    def test_personSummary(self):
        """
        The I{personSummary} renderer should return a L{PersonSummaryView}
        for the wrapped person.
        """
        person = Person()
        personSummary = renderer.get(
            ReadOnlyContactInfoView(person),
            'personSummary',
            None)
        fragment = personSummary(None, None)
        self.assertTrue(isinstance(fragment, PersonSummaryView))
        self.assertIdentical(fragment.person, person)


    def test_contactInfo(self):
        """
        The I{contactInfo} renderer should return the result of calling
        L{IContactType.getReadOnlyView} on each contact type for each contact
        item of the wrapped person.
        """
        person = StubPerson([])
        contactItems = [object(), object(), object()]
        person.organizer = StubOrganizer(
            contactTypes=[
                StubContactType(None, None, [contactItems[0]]),
                StubContactType(None, None, contactItems[1:])])
        contactInfo = renderer.get(
            ReadOnlyContactInfoView(person),
            'contactInfo',
            None)
        fragments = list(contactInfo(None, None))
        self.assertEqual(len(fragments), 3)

        self.assertTrue(isinstance(fragments[0], StubReadOnlyView))
        self.assertIdentical(fragments[0].item, contactItems[0])

        self.assertTrue(isinstance(fragments[1], StubReadOnlyView))
        self.assertIdentical(fragments[1].item, contactItems[1])
        self.assertTrue(isinstance(fragments[2], StubReadOnlyView))
        self.assertIdentical(fragments[2].item, contactItems[2])


    def test_peoplePlugins(self):
        """
        The I{peoplePlugins} renderer should return the result of adapting
        each element in L{Organizer.peoplePlugins} to L{IPersonFragment}.
        """
        person = StubPerson([])
        class _SimpleStubOrganizerPlugin:
            adapted = False
            personalizedFor = None

            def personalize(self, person):
                self.personalizedFor = person
                return self

        def adapter(plugin):
            plugin.adapted = True
            return plugin

        registerAdapter(adapter, _SimpleStubOrganizerPlugin, IPersonFragment)

        person.organizer = StubOrganizer(peoplePlugins=[
            _SimpleStubOrganizerPlugin()])
        peoplePlugins = renderer.get(
            ReadOnlyContactInfoView(person),
            'peoplePlugins',
            None)
        fragments = list(peoplePlugins(None, None))
        self.assertEqual(len(fragments), 1)
        self.assertTrue(
            isinstance(fragments[0], _SimpleStubOrganizerPlugin))
        self.assertIdentical(fragments[0].personalizedFor, person)
        self.assertTrue(fragments[0].adapted)



class PersonSummaryViewTestCase(unittest.TestCase):
    """
    Tests for L{PersonSummaryView}.
    """
    def test_mugshotURL(self):
        """
        The I{mugshotURL} renderer should return the correct URL if the person
        has a mugshot.
        """
        store = Store(self.mktemp())
        organizer = Organizer(store=store)
        installOn(organizer, store)
        person = Person(store=store, organizer=organizer)
        Mugshot(
            store=store,
            person=person,
            body=store.newFilePath(u'body'),
            smallerBody=store.newFilePath(u'smallerBody'),
            type=u'image/jpeg')
        mugshotURL = renderer.get(
            PersonSummaryView(person), 'mugshotURL', None)
        self.assertEqual(
            mugshotURL(None, None),
            organizer.linkToPerson(person) + '/mugshot/smaller')


    def test_mugshotURLNoMugshot(self):
        """
        The I{mugshotURL} renderer should return the correct URL if the person
        has no mugshot.
        """
        store = Store()
        organizer = Organizer(store=store)
        installOn(organizer, store)
        person = Person(store=store, organizer=organizer)
        mugshotURL = renderer.get(
            PersonSummaryView(person),
            'mugshotURL',
            None)
        self.assertEqual(
            mugshotURL(None, None),
            organizer.linkToPerson(person) + '/mugshot/smaller')


    def test_personName(self):
        """
        The I{personName} renderer should return the display name of the
        wrapped person.
        """
        name = u'A Person Name'
        personName = renderer.get(
            PersonSummaryView(Person(store=Store(), name=name)),
            'personName',
            None)
        self.assertEqual(personName(None, None), name)


    def test_vipStatus(self):
        """
        The I{vipStatus} renderer should return its tag if the wrapped person
        is a VIP.
        """
        vipStatus = renderer.get(
            PersonSummaryView(Person(store=Store(), vip=True)),
            'vipStatus',
            None)
        tag = object()
        self.assertIdentical(vipStatus(None, tag), tag)


    def test_vipStatusNoVip(self):
        """
        The I{vipStatus} renderer should return the empty string if the
        wrapped person is not a VIP.
        """
        vipStatus = renderer.get(
            PersonSummaryView(Person(store=Store(), vip=False)),
            'vipStatus',
            None)
        self.assertEqual(vipStatus(None, None), '')



class EditPersonViewTests(unittest.TestCase):
    """
    Tests for L{EditPersonView}.
    """
    def setUp(self):
        """
        Create an L{EditPersonView} wrapped around a stub person and stub organizer.
        """
        self.contactType = StubContactType((), None, None)
        self.contactParameter = ListChangeParameter(
            u'blah', [], [], modelObjects=[])

        self.person = StubPerson(None)
        self.person.organizer = StubOrganizer(
            contactEditorialParameters={self.person: [
                (self.contactType, self.contactParameter)]})
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
        contactType = StubContactType((), None, None)
        self.view.contactTypes = {'contactTypeName': contactType}

        MODEL_OBJECT = object()

        # Submit the form
        submission = object()
        self.view.editContactItems(u'nick', contactTypeName=submission)
        # A transaction should happen, and nothing should change until it's
        # run.
        self.assertEqual(len(transactions), 1)
        self.assertEqual(self.person.name, StubPerson.name)
        self.assertEqual(contactType.editedContacts, [])
        # Okay run it.
        transactions[0].function(
            *transactions[0].args, **transactions[0].kwargs)
        self.assertEqual(
            self.person.organizer.editedPeople,
            [(self.person, u'nick', [(contactType, submission)])])


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
        self.assertEqual(form.parameters[1:], [self.contactParameter])
        self.assertIdentical(form.fragmentParent, self.view)
        self.assertEqual(
            self.view.contactTypes[form.parameters[1].name],
            self.contactType)


    def test_mugshotFormURL(self):
        """
        The I{mugshotFormURL} renderer of L{EditPersonView} should return the
        correct URL.
        """
        mugshotFormURLRenderer = renderer.get(
            self.view, 'mugshotFormURL')
        self.assertEqual(
            mugshotFormURLRenderer(None, None),
            '/person/Alice/mugshotUploadForm')


    def test_renderable(self):
        """
        L{EditPersonView} should be renderable in the typical manner.
        """
        # XXX I have no hope of asserting anything meaningful about the return
        # value of renderLiveFragment.  However, even calling it at all pointed
        # out that: there was no docFactory; the fragmentName didn't reference
        # an extant template; the LiveForm had no fragment parent (for which I
        # also updated test_editorialContactForms to do a direct
        # assertion). -exarkun
        store = Store()
        installOn(PrivateApplication(store=store), store)
        organizer = Organizer(store=store)
        installOn(organizer, store)
        person = organizer.createPerson(u'Alice')
        markup = renderLiveFragment(EditPersonView(person))
        self.assertIn(self.view.jsClass, markup)


    def test_makeEditorialLiveForm(self):
        """
        L{EditPersonView.makeEditorialLiveForm} should make a liveform with the
        correct parameters.
        """
        liveForm = self.view.makeEditorialLiveForm()
        self.assertEqual(len(liveForm.parameters), 2)

        nameParam = liveForm.parameters[0]
        self.assertEqual(nameParam.name, 'nickname')
        self.assertEqual(nameParam.default, self.person.name)
        self.assertEqual(nameParam.type, TEXT_INPUT)

        contactParam = liveForm.parameters[1]
        self.assertIdentical(contactParam, self.contactParameter)



class StoreOwnerPersonTestCase(unittest.TestCase):
    """
    Tests for L{Organizer._makeStoreOwnerPerson} and related functionality.
    """
    def test_noStore(self):
        """
        L{Organizer.storeOwnerPerson} should be C{None} if the L{Organizer}
        doesn't live in a store.
        """
        self.assertIdentical(Organizer().storeOwnerPerson, None)


    def test_emptyStore(self):
        """
        Test that when an L{Organizer} is inserted into an empty store,
        L{Organizer.storeOwnerPerson} is set to a L{Person} with an empty
        string for a name.
        """
        store = Store()
        organizer = Organizer(store=store)
        self.failUnless(organizer.storeOwnerPerson)
        self.assertIdentical(organizer.storeOwnerPerson.organizer, organizer)
        self.assertEqual(organizer.storeOwnerPerson.name, u'')


    def test_differentStoreOwner(self):
        """
        Test that when an L{Organizer} is passed a C{storeOwnerPerson}
        explicitly, it does not create any additional L{Person} items.
        """
        store = Store()
        person = Person(store=store)
        organizer = Organizer(store=store, storeOwnerPerson=person)
        self.assertIdentical(store.findUnique(Person), person)
        self.assertIdentical(organizer.storeOwnerPerson, person)


    def test_storeOwnerDeletion(self):
        """
        Verify that we fail if we attempt to delete
        L{Organizer.storeOwnerPerson}.
        """
        store = Store()
        organizer = Organizer(store=store)
        self.assertRaises(
            DeletionDisallowed, organizer.storeOwnerPerson.deleteFromStore)


    def test_personNameFromUserInfo(self):
        """
        The L{Person} created to be the store owner by L{Organizer} should have
        its I{name} attribute set to a string computed from the L{UserInfo}
        item.
        """
        name = u'Joe Rogers'
        store = Store()
        UserInfo(store=store, realName=name)
        organizer = Organizer(store=store)
        self.assertEqual(organizer.storeOwnerPerson.name, name)


    def test_personEmailFromUserInfo(self):
        """
        The L{Person} created to be the store owner by L{Organizer} should have
        an L{EmailAddress} item created with an address computed from the
        available 'email' login methods.

        (In the course of doing so, make sure that it creates them correctly
        and notifies the organizer plugins of the L{EmailAddress} item's
        existence.)
        """
        siteStore = Store()
        ls = LoginSystem(store=siteStore)

        # It should NOT consider the login method created implicitly as a
        # result of the signup process.  Too bad that actually defaults to the
        # 'email' protocol!
        acct = ls.addAccount(u'jim.bean',
                             u'service.example.com',
                             u'nevermind',
                             internal=True)
        userStore = acct.avatars.open()
        acct.addLoginMethod(localpart=u'jim',
                            domain=u'bean.example.com',
                            protocol=u'email',
                            verified=False,
                            internal=False)
        stub = StubOrganizerPlugin(store=userStore)
        # This is _slightly_ unrealistic for real-world usage, because
        # generally L{IOrganizerPlugin} providers will also just happen to
        # depend on the organizer (and therefore won't get notified of this
        # first item).  However, nothing says they *need* to depend on it, and
        # if they don't, the contact items should be created the proper,
        # suggested way.
        userStore.powerUp(stub, IOrganizerPlugin)
        organizer = Organizer(store=userStore)
        person = organizer.storeOwnerPerson
        self.assertEqual(list(person.getEmailAddresses()),
                         [u'jim@bean.example.com'])
        self.assertEqual(stub.createdPeople, [organizer.storeOwnerPerson])
        self.assertEqual(stub.createdContactItems,
                         [userStore.findUnique(EmailAddress)])

