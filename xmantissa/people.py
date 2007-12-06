# -*- test-case-name: xmantissa.test.test_people -*-

from warnings import warn

try:
    from PIL import Image
except ImportError:
    Image = None

from zope.interface import implements

from twisted.python import components
from twisted.python.filepath import FilePath
from twisted.python.reflect import qual

from nevow import rend, athena, inevow, static, tags, url
from nevow.athena import expose, LiveElement
from nevow.loaders import stan
from nevow.page import Element, renderer
from formless import nameToLabel

from epsilon import extime

from axiom import item, attributes
from axiom.dependency import dependsOn, installOn
from axiom.attributes import boolean
from axiom.upgrade import (
    registerUpgrader, registerAttributeCopyingUpgrader,
    registerDeletionUpgrader)
from axiom.userbase import LoginAccount, LoginMethod

from xmantissa.ixmantissa import IPersonFragment
from xmantissa import ixmantissa, webnav, webtheme, liveform, signup
from xmantissa.ixmantissa import IOrganizerPlugin, IContactType
from xmantissa.webapp import PrivateApplication
from xmantissa.tdbview import TabularDataView, ColumnViewBase
from xmantissa.tdb import TabularDataModel
from xmantissa.scrolltable import ScrollingElement, UnsortableColumn
from xmantissa.fragmentutils import dictFillSlots
from xmantissa.webtheme import ThemedDocumentFactory, ThemedFragment


def makeThumbnail(inputFile, outputFile, thumbnailSize, outputFormat='jpeg'):
    """
    Make a thumbnail of the image stored at C{inputPath}, preserving its
    aspect ratio, and write the result to C{outputPath}.

    @param inputFile: The image file (or path to the file) to thumbnail.
    @type inputFile: C{file} or C{str}

    @param outputFile: The file (or path to the file) to write the thumbnail
    to.
    @type outputFile: C{file} or C{str}

    @param thumbnailSize: The maximum length (in pixels) of the longest side of
    the thumbnail image.
    @type thumbnailSize: C{int}

    @param outputFormat: The C{format} argument to pass to L{Image.save}.
    Defaults to I{jpeg}.
    @type format: C{str}
    """
    if Image is None:
        # throw the ImportError here
        import PIL
    image = Image.open(inputFile)
    image.thumbnail((thumbnailSize, thumbnailSize), Image.ANTIALIAS)
    image.save(outputFile, outputFormat)



_CONTACT_INFO_ICON_URLS = {}
def setIconURLForContactInfoType(itemType, iconPath):
    """
    Set the URL to the icon for a particular contact info type.

    @param itemType: an item type
    @type itemType: L{MetaItem}

    @param iconPath: The location of an image to be used as an icon
    when displaying contact information of the given type.
    """
    _CONTACT_INFO_ICON_URLS[itemType] = iconPath


def iconURLForContactInfoType(itemType):
    """
    Look up the URL to the icon for a particular contact info type.

    @param itemType: an item type
    @type itemType: L{MetaItem}
    """
    return _CONTACT_INFO_ICON_URLS[itemType]



def _normalizeWhitespace(text):
    """
    Remove leading and trailing whitespace and collapse adjacent spaces into a
    single space.

    @type text: C{unicode}
    @rtype: C{unicode}
    """
    return u' '.join(text.split())



def _guessDescriptiveIdentifier(contactType):
    """
    Figure out a possibly-useful default descriptive identifier for
    C{contactType}.

    @type contactType: L{IContactType} provider.

    @rtype: C{unicode}
    """
    return nameToLabel(contactType.__class__.__name__).lstrip()



def _descriptiveIdentifier(contactType):
    """
    Get a descriptive identifier for C{contactType}, taking into account the
    fact that it might not have implemented the C{descriptiveIdentifier}
    method.

    @type contactType: L{IContactType} provider.

    @rtype: C{unicode}
    """
    descriptiveIdentifierMethod = getattr(
        contactType, 'descriptiveIdentifier', None)
    if descriptiveIdentifierMethod is not None:
        return descriptiveIdentifierMethod()
    warn(
        "IContactType now has the 'descriptiveIdentifier'"
        " method, %s did not implement it" % (contactType.__class__,),
        category=PendingDeprecationWarning)
    return _guessDescriptiveIdentifier(contactType)



class BaseContactType(object):
    """
    Base class for L{IContactType} implementations which provides useful
    default behavior.
    """
    allowMultipleContactItems = True

    def uniqueIdentifier(self):
        """
        Uniquely identify this contact type.
        """
        return qual(self.__class__).decode('ascii')


    def getParameters(self, contact):
        """
        Return a list of L{liveform.Parameter} objects to be used to create
        L{liveform.LiveForm}s suitable for creating or editing contact
        information of this type.

        Override this in a subclass.

        @param contact: A contact item, values from which should be used as
            defaults in the parameters.  C{None} if the parameters are for
            creating a new contact item.

        """
        raise NotImplementedError("%s did not implement getParameters" % (self,))


    def coerce(self, **kw):
        """
        Callback for input validation.

        @param **kw: Mapping of submitted parameter names to values.

        @rtype: C{dict}
        @return: Mapping of coerced parameter names to values.
        """
        return kw


    def getEditorialForm(self, contact):
        """
        Create a L{liveform.LiveForm} for editing an instance of this kind of
        contact item using the parameters returned by L{getParameters}.
        """
        return liveform.LiveForm(self.coerce, self.getParameters(contact))



class _PersonVIPStatus:
    """
    Contact item type used by L{VIPPersonContactType}.

    @param person: The person whose VIP status we're interested in.
    @type person: L{Person}
    """
    def __init__(self, person):
        self.person = person



class VIPPersonContactType(BaseContactType):
    """
    A contact type for controlling whether L{Person.vip} is set.
    """
    implements(IContactType)
    allowMultipleContactItems = False

    def getParameters(self, contactItem):
        """
        Return a list containing a single parameter suitable for changing the
        VIP status of a person.

        @type contactItem: L{_PersonVIPStatus}

        @rtype: C{list} of L{liveform.Parameter}
        """
        isVIP = False # default
        if contactItem is not None:
            isVIP = contactItem.person.vip
        return [liveform.Parameter(
            'vip', liveform.CHECKBOX_INPUT, bool, 'VIP', default=isVIP)]


    def getContactItems(self, person):
        """
        Return a list containing a L{_PersonVIPStatus} instance for C{person}.

        @type person: L{Person}

        @rtype: C{list} of L{_PersonVIPStatus}
        """
        return [_PersonVIPStatus(person)]


    def createContactItem(self, person, vip):
        """
        Set the VIP status of C{person} to C{vip}.

        @type person: L{Person}

        @type vip: C{bool}

        @rtype: L{_PersonVIPStatus}
        """
        person.vip = vip
        return _PersonVIPStatus(person)


    def editContactItem(self, contactItem, vip):
        """
        Change the VIP status of C{contactItem}'s person to C{vip}.

        @type contactItem: L{_PersonVIPStatus}

        @type vip: C{bool}

        @rtype: C{NoneType}
        """
        contactItem.person.vip = vip


    def getReadOnlyView(self, contactItem):
        """
        Return a fragment which will render as the empty string.
        L{PersonSummaryView} handles the rendering of VIP status in the
        read-only L{Person} view.

        @type contactItem: L{_PersonVIPStatus}

        @rtype: L{Element}
        """
        return Element(docFactory=stan(tags.invisible()))



class EmailContactType(BaseContactType):
    """
    Contact type plugin which allows a person to have an email address.

    @ivar store: The L{Store} the contact items will be created in.
    """
    implements(IContactType)

    def __init__(self, store):
        self.store = store


    def getParameters(self, emailAddress):
        """
        Return a C{list} of one L{LiveForm} parameter for editing an
        L{EmailAddress}.

        @type emailAddress: L{EmailAddress} or C{NoneType}
        @param emailAddress: If not C{None}, an existing contact item from
            which to get the email address default value.

        @rtype: C{list}
        @return: The parameters necessary for specifying an email address.
        """
        if emailAddress is not None:
            address = emailAddress.address
        else:
            address = u''
        return [
            liveform.Parameter('email', liveform.TEXT_INPUT,
                               _normalizeWhitespace, 'Email Address',
                               default=address)]


    def descriptiveIdentifier(self):
        """
        Return 'Email Address'
        """
        return u'Email Address'


    def _existing(self, email):
        """
        Return the existing L{EmailAddress} item with the given address, or
        C{None} if there isn't one.
        """
        return self.store.findUnique(
            EmailAddress,
            EmailAddress.address == email,
            default=None)


    def createContactItem(self, person, email):
        """
        Create a new L{EmailAddress} associated with the given person based on
        the given email address.

        @type person: L{Person}
        @param person: The person with whom to associate the new
            L{EmailAddress}.

        @type email: C{unicode}
        @param email: The value to use for the I{address} attribute of the
            newly created L{EmailAddress}.  If C{''}, no L{EmailAddress} will
            be created.

        @return: C{None}
        """
        if email:
            address = self._existing(email)
            if address is not None:
                raise ValueError('There is already a person with that email '
                                 'address (%s): ' % (address.person.name,))
            return EmailAddress(store=self.store,
                                address=email,
                                person=person)


    def getContactItems(self, person):
        """
        Return all L{EmailAddress} instances associated with the given person.

        @type person: L{Person}
        """
        return person.store.query(
            EmailAddress,
            EmailAddress.person == person)


    def editContactItem(self, contact, email):
        """
        Change the email address of the given L{EmailAddress} to that specified
        by C{email}.

        @type email: C{unicode}
        @param email: The new value to use for the I{address} attribute of the
            L{EmailAddress}.

        @return: C{None}
        """
        address = self._existing(email)
        if address is not None and address is not contact:
            raise ValueError('There is already a person with that email '
                             'address (%s): ' % (address.person.name,))
        contact.address = email


    def getReadOnlyView(self, contact):
        """
        Return a L{ReadOnlyEmailView} for the given L{EmailAddress}.
        """
        return ReadOnlyEmailView(contact)



class ReadOnlyEmailView(Element):
    """
    Display an email address.

    @type email: L{EmailAddress}
    @ivar email: The email address which will be displayed.
    """
    docFactory = ThemedDocumentFactory(
        'person-contact-read-only-email-view', 'store')

    def __init__(self, email):
        self.email = email
        self.store = email.store


    def address(self, request, tag):
        """
        Add the value of the C{address} attribute of the wrapped
        L{EmailAddress} as a child to the given tag.
        """
        return tag[self.email.address]
    renderer(address)



class PeopleBenefactor(item.Item):
    implements(ixmantissa.IBenefactor)
    endowed = attributes.integer(default=0)
    powerupNames = ["xmantissa.people.AddPerson"]



class Person(item.Item):
    """
    Person Per"son (p[~e]r"s'n; 277), n.

        1. A character or part, as in a play; a specific kind or manifestation
        of individual character, whether in real life, or in literary or
        dramatic representation; an assumed character. [Archaic] [1913 Webster]

    This is Mantissa's simulation of a person, which has attached contact
    information.  It is highly pluggable, mostly via the L{Organizer} object.

    Do not create this item directly, as functionality of L{IOrganizerPlugin}
    powerups will be broken if you do.  Instead, use L{Organizer.createPerson}.
    """

    typeName = 'mantissa_person'
    schemaVersion = 3

    organizer = attributes.reference(
        doc="""
        The L{Organizer} to which this Person belongs.
        """)

    name = attributes.text(
        doc="""
        This name of this person.
        """, caseSensitive=False)

    created = attributes.timestamp(defaultFactory=extime.Time)

    vip = boolean(
        doc="""
        Flag indicating this L{Person} is very important.
        """, default=False, allowNone=False)


    def getDisplayName(self):
        return self.name


    def getEmailAddresses(self):
        """
        Return an iterator of all email addresses associated with this person.

        @return: an iterator of unicode strings in RFC2822 address format.
        """
        return self.store.query(
            EmailAddress,
            EmailAddress.person == self).getColumn('address')

    def getEmailAddress(self):
        """
        Return the default email address associated with this person.

        Note: this is effectively random right now if a person has more than
        one address.  It's just the first address returned.  This should be
        fixed in a future version.

        @return: a unicode string in RFC2822 address format.
        """
        for a in self.getEmailAddresses():
            return a


    def getMugshot(self):
        """
        Return the L{Mugshot} associated with this L{Person} or C{None} if
        there isn't one.
        """
        return self.store.findUnique(
            Mugshot, Mugshot.person == self, default=None)


    def registerExtract(self, extract, timestamp=None):
        """
        @param extract: some Item that implements L{inevow.IRenderer}
        """
        if timestamp is None:
            timestamp = extime.Time()

        return ExtractWrapper(store=self.store,
                              extract=extract,
                              timestamp=timestamp,
                              person=self)

    def getExtractWrappers(self, n):
        return self.store.query(ExtractWrapper,
                                ExtractWrapper.person == self,
                                sort=ExtractWrapper.timestamp.desc,
                                limit=n)

    def getContactInfoItems(self, itemType, valueColumn):
        """
        Find the values of all contact info items of the given type.

        @type itemType: L{MetaItem}
        @param itemType: The L{Item} subclass defining the contact
        info type to create.

        @type valueColumn: C{str}
        @param valueColumn: The name of the primary key attribute of
        the contact info type.

        @return: C{valueColumn} for each contact info item.
        @rtype: the type of C{valueColumn}
        """
        return self.store.query(
            itemType, itemType.person == self).getColumn(valueColumn)

    def deleteContactInfoItem(self, itemType, valueColumn, value):
        """
        Delete the contact info item with the given value.

        @type itemType: L{MetaItem}
        @param itemType: The L{Item} subclass defining the contact
        info type to create.

        @type valueColumn: C{str}
        @param valueColumn: The name of the primary key attribute of
        the contact info type.

        @param value: The value of C{valueColumn} to search for.  It
        should be of the appropriate type for that attribute.

        @return: C{None}
        """
        self.findContactInfoItem(
            itemType, valueColumn, value).deleteFromStore()

    def editContactInfoItem(self, itemType, valueColumn, oldValue, newValue):
        """
        Change the value of the contact info item with the given value
        to a new value.

        @type itemType: L{MetaItem}
        @param itemType: The L{Item} subclass defining the contact
        info type to create.

        @type valueColumn: C{str}
        @param valueColumn: The name of the primary key attribute of
        the contact info type.

        @param oldValue: The value of C{valueColumn} to search for.  It
        should be of the appropriate type for that attribute.

        @param newValue: The value of C{valueColumn} to set on the
        found item.  It should be of the appropriate type for that
        attribute

        @return: C{None}
        """
        setattr(
            self.findContactInfoItem(itemType, valueColumn, oldValue),
            valueColumn,
            newValue)

    def findContactInfoItem(self, itemType, valueColumn, value):
        """
        Find a contact info item of the given type with the given value.

        @type itemType: L{MetaItem}
        @param itemType: The L{Item} subclass defining the contact
        info type to create.

        @type valueColumn: C{str}
        @param valueColumn: The name of the primary key attribute of
        the contact info type.

        @param value: The value of C{valueColumn} to search for.  It
        should be of the appropriate type for that attribute.

        @return: An instance of C{itemType} with a matching
        C{valueColumn} which belongs to this person, or C{None} if
        there is not one.
        """
        return self.store.findFirst(
            itemType,
            attributes.AND(
                itemType.person == self,
                getattr(itemType, valueColumn) == value))

    def createContactInfoItem(self, itemType, valueColumn, value):
        """
        Create a new contact information item of the given type.

        @type itemType: L{MetaItem}
        @param itemType: The L{Item} subclass defining the contact
        info type to create.

        @type valueColumn: C{str}
        @param valueColumn: The name of the primary key attribute of
        the contact info type.

        @param value: A value to use for the C{valueColumn} attribute
        of the created item.  It should be of the appropriate type for
        that attribute.

        @return: C{None}
        """
        installOn(
            itemType(store=self.store,
                    person=self,
                    **{valueColumn: value}), self)

item.declareLegacyItem(
    Person.typeName,
    1,
    dict(organizer=attributes.reference(),
         name=attributes.text(caseSensitive=True),
         created=attributes.timestamp()))

registerAttributeCopyingUpgrader(Person, 1, 2)

item.declareLegacyItem(
    Person.typeName,
    2,
    dict(organizer=attributes.reference(),
         name=attributes.text(caseSensitive=True),
         created=attributes.timestamp(),
         vip=attributes.boolean(default=False, allowNone=False)))

registerAttributeCopyingUpgrader(Person, 2, 3)



class ExtractWrapper(item.Item):
    extract = attributes.reference(whenDeleted=attributes.reference.CASCADE)
    timestamp = attributes.timestamp(indexed=True)
    person = attributes.reference(reftype=Person,
                                  whenDeleted=attributes.reference.CASCADE)



def _stringifyKeys(d):
    """
    Return a copy of C{d} with C{str} keys.

    @type d: C{dict} with C{unicode} keys.
    @rtype: C{dict} with C{str} keys.
    """
    return dict((k.encode('ascii'), v)  for (k, v) in d.iteritems())



class Organizer(item.Item):
    """
    Oversee the creation, location, destruction, and modification of
    people in a particular set (eg, the set of people you know).
    """
    implements(ixmantissa.INavigableElement)

    typeName = 'mantissa_people'
    schemaVersion = 3

    _webTranslator = dependsOn(PrivateApplication)
    storeOwnerPerson = attributes.reference(
        doc="A L{Person} representing the owner of the store this organizer lives in",
        reftype=Person,
        whenDeleted=attributes.reference.DISALLOW)

    powerupInterfaces = (ixmantissa.INavigableElement,)


    def __init__(self, *a, **k):
        super(Organizer, self).__init__(*a, **k)
        if 'storeOwnerPerson' not in k:
            self.storeOwnerPerson = self._makeStoreOwnerPerson()


    def _makeStoreOwnerPerson(self):
        """
        Make a L{Person} representing the owner of the store that this
        L{Organizer} is installed in.

        @rtype: L{Person}
        """
        if self.store is None:
            return None
        userInfo = self.store.findFirst(signup.UserInfo)
        name = u''
        if userInfo is not None:
            name = userInfo.realName
        account = self.store.findUnique(LoginAccount,
                                        LoginAccount.avatars == self.store, None)
        ownerPerson = self.createPerson(name)
        if account is not None:
            for method in (self.store.query(
                    LoginMethod,
                    attributes.AND(LoginMethod.account == account,
                                   LoginMethod.internal == False))):
                self.createContactItem(
                    EmailContactType(self.store),
                    ownerPerson, dict(
                        email=method.localpart + u'@' + method.domain))
        return ownerPerson


    def getOrganizerPlugins(self):
        """
        Return an iterator of the installed L{IOrganizerPlugin} powerups.
        """
        return self.store.powerupsFor(IOrganizerPlugin)


    def getContactTypes(self):
        """
        Return an iterator of L{IContactType} providers available to this
        organizer's store.
        """
        yield VIPPersonContactType()
        yield EmailContactType(self.store)
        yield PostalContactType()
        yield PhoneNumberContactType()
        yield NotesContactType()
        for plugin in self.getOrganizerPlugins():
            getContactTypes = getattr(plugin, 'getContactTypes', None)
            if getContactTypes is not None:
                for contactType in plugin.getContactTypes():
                    yield contactType
            else:
                warn(
                    "IOrganizerPlugin now has the getContactTypes method, %s "
                    "did not implement it" % (plugin.__class__,),
                    category=PendingDeprecationWarning)


    def getContactCreationParameters(self):
        """
        Yield a L{Parameter} for each L{IContactType} known.

        Each yielded object can be used with a L{LiveForm} to create a new
        instance of a particular L{IContactType}.
        """
        for contactType in self.getContactTypes():
            if contactType.allowMultipleContactItems:
                descriptiveIdentifier = _descriptiveIdentifier(contactType)
                yield liveform.ListChangeParameter(
                    contactType.uniqueIdentifier(),
                    contactType.getParameters(None),
                    defaults=[],
                    modelObjects=[],
                    modelObjectDescription=descriptiveIdentifier)
            else:
                yield liveform.FormParameter(
                    contactType.uniqueIdentifier(),
                    liveform.LiveForm(
                        lambda **k: k,
                        contactType.getParameters(None)))


    def _parametersToDefaults(self, parameters):
        """
        Extract the defaults from C{parameters}, constructing a dictionary
        mapping parameter names to default values, suitable for passing to
        L{ListChangeParameter}.

        @type parameters: C{list} of L{liveform.Parameter} or
        L{liveform.ChoiceParameter}.

        @rtype: C{dict}
        """
        defaults = {}
        for p in parameters:
            if isinstance(p, liveform.ChoiceParameter):
                selected = []
                for choice in p.choices:
                    if choice.selected:
                        selected.append(choice.value)
                defaults[p.name] = selected
            else:
                defaults[p.name] = p.default
        return defaults


    def getContactEditorialParameters(self, person):
        """
        Yield L{LiveForm} parameters to edit each contact item of each contact
        type for the given person.

        @type person: L{Person}
        @return: An iterable of two-tuples.  The first element of each tuple
            is an L{IContactType} provider.  The third element of each tuple
            is the L{LiveForm} parameter object for that contact item.
        """
        for contactType in self.getContactTypes():
            contactItems = list(contactType.getContactItems(person))
            if contactType.allowMultipleContactItems:
                defaults = []
                modelObjects = []
                for contactItem in contactItems:
                    defaultedParameters = contactType.getParameters(contactItem)
                    if defaultedParameters is None:
                        continue
                    defaults.append(self._parametersToDefaults(
                        defaultedParameters))
                    modelObjects.append(contactItem)
                descriptiveIdentifier = _descriptiveIdentifier(contactType)
                param = liveform.ListChangeParameter(
                    contactType.uniqueIdentifier(),
                    contactType.getParameters(None),
                    defaults=defaults,
                    modelObjects=modelObjects,
                    modelObjectDescription=descriptiveIdentifier)
            else:
                (contactItem,) = contactItems
                param = liveform.FormParameter(
                    contactType.uniqueIdentifier(),
                    liveform.LiveForm(
                        lambda **k: k,
                        contactType.getParameters(contactItem)))
            yield (contactType, param)


    _NO_VIP = object()

    def createPerson(self, nickname, vip=_NO_VIP):
        """
        Create a new L{Person} with the given name in this organizer.

        @type nickname: C{unicode}
        @param nickname: The value for the new person's C{name} attribute.

        @type vip: C{bool}
        @param vip: Value to set the created person's C{vip} attribute to
        (deprecated).

        @rtype: L{Person}
        """
        for person in (self.store.query(
                Person, attributes.AND(
                    Person.name == nickname,
                    Person.organizer == self))):
            raise ValueError("Person with name %r exists already." % (nickname,))
        person = Person(
            store=self.store,
            created=extime.Time(),
            organizer=self,
            name=nickname)

        if vip is not self._NO_VIP:
            warn(
                "Usage of Organizer.createPerson's 'vip' parameter"
                " is deprecated",
                category=DeprecationWarning)
            person.vip = vip

        self._callOnOrganizerPlugins('personCreated', person)
        return person


    def createContactItem(self, contactType, person, contactInfo):
        """
        Create a new contact item for the given person with the given contact
        type.  Broadcast a creation to all L{IOrganizerPlugin} powerups.

        @type contactType: L{IContactType}
        @param contactType: The contact type which will be used to create the
            contact item.

        @type person: L{Person}
        @param person: The person with whom the contact item will be
            associated.

        @type contactInfo: C{dict}
        @param contactInfo: The contact information to use to create the
            contact item.

        @return: The contact item, as created by the given contact type.
        """
        contactItem = contactType.createContactItem(
            person, **_stringifyKeys(contactInfo))
        if contactItem is not None:
            self._callOnOrganizerPlugins('contactItemCreated', contactItem)
        return contactItem


    def editContactItem(self, contactType, contactItem, contactInfo):
        """
        Edit the given contact item with the given contact type.  Broadcast
        the edit to all L{IOrganizerPlugin} powerups.

        @type contactType: L{IContactType}
        @param contactType: The contact type which will be used to edit the
            contact item.

        @param contactItem: The contact item to edit.

        @type contactInfo: C{dict}
        @param contactInfo: The contact information to use to edit the
            contact item.

        @return: C{None}
        """
        contactType.editContactItem(
            contactItem, **_stringifyKeys(contactInfo))
        self._callOnOrganizerPlugins('contactItemEdited', contactItem)


    def _callOnOrganizerPlugins(self, methodName, *args):
        """
        Call a method on all L{IOrganizerPlugin} powerups on C{self.store}, or
        emit a deprecation warning for each one which does not implement that
        method.
        """
        for observer in self.getOrganizerPlugins():
            method = getattr(observer, methodName, None)
            if method is not None:
                method(*args)
            else:
                warn(
                    "IOrganizerPlugin now has the %s method, %s "
                    "did not implement it" % (methodName, observer.__class__,),
                    category=PendingDeprecationWarning)


    def editPerson(self, person, nickname, edits):
        """
        Change the name and contact information associated with the given
        L{Person}.

        @type person: L{Person}
        @param person: The person which will be modified.

        @type nickname: C{unicode}
        @param nickname: The new value for L{Person.name}

        @type edits: C{list}
        @param edits: list of tuples of L{IContactType} providers and
        corresponding L{ListChanges} objects or dictionaries of parameter
        values.
        """
        for existing in self.store.query(Person, Person.name == nickname):
            if existing is person:
                continue
            raise ValueError(
                "A person with the name %r exists already." % (nickname,))
        oldname = person.name
        person.name = nickname
        self._callOnOrganizerPlugins('personNameChanged', person, oldname)
        for contactType, submission in edits:
            if contactType.allowMultipleContactItems:
                for edit in submission.edit:
                    self.editContactItem(
                        contactType, edit.object, edit.values)
                for create in submission.create:
                    create.setter(
                        self.createContactItem(
                            contactType, person, create.values))
                for delete in submission.delete:
                    delete.deleteFromStore()
            else:
                (contactItem,) = contactType.getContactItems(person)
                self.editContactItem(
                    contactType, contactItem, submission)


    def deletePerson(self, person):
        """
        Delete the given person from the store.
        """
        person.deleteFromStore()


    def personByName(self, name):
        """
        Retrieve the L{Person} item for the given Q2Q address,
        creating it first if necessary.

        @type name: C{unicode}
        """
        return self.store.findOrCreate(Person, organizer=self, name=name)


    def personByEmailAddress(self, address):
        """
        Retrieve the L{Person} item for the given email address
        (or return None if no such person exists)

        @type name: C{unicode}
        """
        email = self.store.findUnique(EmailAddress,
                                      EmailAddress.address == address,
                                      default=None)
        if email is not None:
            return email.person


    def peoplePlugins(self, person):
        return (
            p.personalize(person)
            for p
            in self.getOrganizerPlugins())


    def linkToPerson(self, person):
        """
        @param person: L{Person} instance
        @return: string url at which C{person} will be rendered
        """
        return (self._webTranslator.linkTo(self.storeID) +
                '/' + self._webTranslator.toWebID(person))


    def urlForViewState(self, person, viewState):
        """
        Return a url for L{OrganizerFragment} which will display C{person} in
        state C{viewState}.

        @type person: L{Person}
        @type viewState: L{ORGANIZER_VIEW_STATES} constant.

        @rtype: L{url.URL}
        """
        # ideally there would be a more general mechanism for encoding state
        # like this in a url, rather than ad-hoc query arguments for each
        # fragment which needs to do it.
        organizerURL = self._webTranslator.linkTo(self.storeID)
        return url.URL(
            netloc='', scheme='',
            pathsegs=organizerURL.split('/')[1:],
            querysegs=(('initial-person', person.name),
                       ('initial-state', viewState)))


    # INavigableElement
    def getTabs(self):
        """
        Implement L{INavigableElement.getTabs} to return a single tab,
        'People', that points to this item.
        """
        ourURL = self._webTranslator.linkTo(self.storeID)
        return [webnav.Tab('People', self.storeID, 0.5, authoritative=True)]



def organizer1to2(old):
    o = old.upgradeVersion(old.typeName, 1, 2)
    o._webTranslator = old.store.findOrCreate(PrivateApplication)
    return o

registerUpgrader(organizer1to2, Organizer.typeName, 1, 2)



item.declareLegacyItem(Organizer.typeName, 2,
    dict(_webTranslator=attributes.reference()))



registerAttributeCopyingUpgrader(Organizer, 2, 3)



class VIPColumn(UnsortableColumn):
    def getType(self):
        return 'boolean'



class PersonScrollingFragment(ScrollingElement):
    """
    Scrolling element which displays L{Person} objects and allows actions to
    be taken on them.

    @type organizer: L{Organizer}
    """
    jsClass = u'Mantissa.People.PersonScroller'

    def __init__(self, organizer, baseConstraint, defaultSortColumn,
            webTranslator):
        ScrollingElement.__init__(
            self,
            organizer.store,
            Person,
            baseConstraint,
            [VIPColumn(Person.vip, 'vip'),
             Person.name],
            defaultSortColumn=defaultSortColumn,
            webTranslator=webTranslator)
        self.organizer = organizer


    def getInitialArguments(self):
        """
        Include L{organizer}'s C{storeOwnerPerson}'s name.
        """
        return (ScrollingElement.getInitialArguments(self)
                    + [self.organizer.storeOwnerPerson.name])



class PersonSummaryView(Element):
    """
    Fragment which renders a business card-like summary of a L{Person}: their
    mugshot, vip status, and name.

    @type person: L{Person}
    @ivar person: The person to summarize.
    """
    docFactory = ThemedDocumentFactory('person-summary', 'store')

    def __init__(self, person):
        self.person = person
        self.organizer = person.organizer
        self.store = person.store


    def mugshotURL(self, req, tag):
        """
        Render the URL of L{person}'s mugshot, or the URL of a placeholder
        mugshot if they don't have one set.
        """
        return self.organizer.linkToPerson(self.person) + '/mugshot/smaller'
    renderer(mugshotURL)


    def personName(self, req, tag):
        """
        Render the display name of L{person}.
        """
        return self.person.getDisplayName()
    renderer(personName)


    def vipStatus(self, req, tag):
        """
        Return C{tag} if L{person} is a VIP, otherwise return the empty
        string.
        """
        if self.person.vip:
            return tag
        return ''
    renderer(vipStatus)



class ReadOnlyContactInfoView(Element):
    """
    Fragment which renders a read-only version of a person's contact
    information.

    @ivar person: A person.
    @type person: L{Person}
    """
    docFactory = ThemedDocumentFactory(
        'person-read-only-contact-info', 'store')

    def __init__(self, person):
        self.person = person
        self.organizer = person.organizer
        self.store = person.store
        Element.__init__(self)


    def personSummary(self, request, tag):
        """
        Render a L{PersonSummaryView} for L{person}.
        """
        return PersonSummaryView(self.person)
    renderer(personSummary)


    def contactInfo(self, request, tag):
        """
        Render the result of calling L{IContactType.getReadOnlyView} on the
        corresponding L{IContactType} for each piece of contact info
        associated with L{person}.
        """
        for contactType in self.organizer.getContactTypes():
            for contactItem in contactType.getContactItems(self.person):
                yield contactType.getReadOnlyView(contactItem)
    renderer(contactInfo)


    def peoplePlugins(self, request, tag):
        """
        Render the result of adapting each item returned from
        L{Organizer.peoplePlugins} to L{IPersonFragment}.
        """
        for peoplePlugin in self.organizer.peoplePlugins(self.person):
            yield IPersonFragment(peoplePlugin)
    renderer(peoplePlugins)



class ORGANIZER_VIEW_STATES:
    """
    Some constants describing possible initial states of L{OrganizerFragment}.

    @ivar EDIT: The state which involves editing a person.

    @ivar ALL_STATES: A sequence of all valid initial states.
    """
    EDIT = u'edit'

    ALL_STATES = (EDIT,)



class OrganizerFragment(athena.LiveFragment):
    """
    Address book view.  The initial state of this fragment can be extracted
    from the query parameters in its url, if present.  The two parameters it
    looks for are: I{initial-person} (the name of the L{Person} to select
    initially in the scrolltable) and I{initial-state} (a
    L{ORGANIZER_VIEW_STATES} constant describing what to do with the person).
    Both query arguments must be present if either is.

    @type organizer: L{Organizer}
    @ivar organizer: The organizer for which this is a view.

    @ivar initialPerson: The person to load initially.  Defaults to C{None}.
    @type initialPerson: L{Person} or C{NoneType}

    @ivar initialState: The initial state of the organizer view.  Defaults to
    C{None}.
    @type initialState: L{ORGANIZER_VIEW_STATES} or C{NoneType}
    """
    docFactory = ThemedDocumentFactory('people-organizer', 'store')
    fragmentName = None
    live = 'athena'
    title = 'People'
    jsClass = u'Mantissa.People.Organizer'

    def __init__(self, organizer, initialPerson=None, initialState=None):
        athena.LiveFragment.__init__(self)
        self.organizer = organizer
        self.initialPerson = initialPerson
        self.initialState = initialState

        self.store = organizer.store
        self.wt = organizer._webTranslator


    def beforeRender(self, ctx):
        """
        Implement this hook to initialize the L{initialPerson} and
        L{initialState} slots with information from the request url's query
        args.
        """
        # see the comment in Organizer.urlForViewState which suggests an
        # alternate implementation of this kind of functionality.
        request = inevow.IRequest(ctx)
        if 'initial-person' not in request.args:
            return
        initialPersonName = request.args['initial-person'][0]
        initialPerson = self.store.findFirst(
            Person, Person.name == initialPersonName.decode('ascii'))
        if initialPerson is None:
            return
        initialState = request.args['initial-state'][0]
        if initialState not in ORGANIZER_VIEW_STATES.ALL_STATES:
            return
        self.initialPerson = initialPerson
        self.initialState = initialState.decode('ascii')


    def getInitialArguments(self):
        """
        Include L{organizer}'s C{storeOwnerPerson}'s name, and the name of
        L{initialPerson} and the value of L{initialState}, if they are set.
        """
        initialArguments = (self.organizer.storeOwnerPerson.name,)
        if self.initialPerson is not None:
            initialArguments += (self.initialPerson.name, self.initialState)
        return initialArguments


    def head(self):
        """
        Do nothing.
        """
        return None


    def getAddPerson(self):
        """
        Return an L{AddPersonFragment} which is a child of this fragment and
        which will add a person to C{self.organizer}.
        """
        fragment = AddPersonFragment(self.organizer)
        fragment.setFragmentParent(self)
        return fragment
    expose(getAddPerson)


    def getEditPerson(self, name):
        """
        Get an L{EditPersonView} for editing the person named C{name}.

        @param name: A person name.
        @type name: C{unicode}

        @rtype: L{EditPersonView}
        """
        view = EditPersonView(self.organizer.personByName(name))
        view.setFragmentParent(self)
        return view
    expose(getEditPerson)


    def deletePerson(self, name):
        """
        Delete the person named C{name}

        @param name: A person name.
        @type name: C{unicode}
        """
        self.organizer.deletePerson(self.organizer.personByName(name))
    expose(deletePerson)


    def render_peopleTable(self, ctx, data):
        """
        Return a L{PersonScrollingFragment} which will display the L{Person}
        items in the wrapped organizer.
        """
        f = PersonScrollingFragment(
                self.organizer,
                None,
                Person.name,
                self.wt)
        f.setFragmentParent(self)
        f.docFactory = webtheme.getLoader(f.fragmentName)
        return f


    def getContactInfoWidget(self, name):
        """
        Return the L{ReadOnlyContactInfoView} for the person named
        C{name}.

        @type name: C{unicode}
        @param name: A value which corresponds to the I{name} attribute of an
        extant L{Person}.

        @type: L{ReadOnlyContactInfoView}
        """
        fragment = ReadOnlyContactInfoView(
            self.organizer.personByName(name))
        return fragment
    expose(getContactInfoWidget)

components.registerAdapter(OrganizerFragment, Organizer, ixmantissa.INavigableFragment)



class EditPersonView(LiveElement):
    """
    Render a view for editing the contact information for a L{Person}.

    @ivar person: L{Person} which can be edited.

    @ivar contactTypes: A mapping from parameter names to the L{IContactTypes}
        whose items the parameters are editing.
    """
    docFactory = ThemedDocumentFactory('edit-person', 'store')
    fragmentName = 'edit-person'
    jsClass = u'Mantissa.People.EditPerson'

    def __init__(self, person):
        athena.LiveElement.__init__(self)
        self.person = person
        self.store = person.store
        self.organizer = person.organizer
        self.contactTypes = {}


    def editContactItems(self, nickname, **edits):
        """
        Update the information on the contact items associated with the wrapped
        L{Person}.

        @type nickname: C{unicode}
        @param nickname: New value to use for the I{name} attribute of the
            L{Person}.

        @param **edits: mapping from contact type identifiers to
            ListChanges instances.
        """
        submissions = []
        for paramName, submission in edits.iteritems():
            contactType = self.contactTypes[paramName]
            submissions.append((contactType, submission))
        self.person.store.transact(
            self.organizer.editPerson,
            self.person, nickname, submissions)


    def makeEditorialLiveForm(self):
        """
        Make a L{LiveForm} for editing the contact information of the wrapped
        L{Person}.
        """
        parameters = [
            liveform.Parameter(
                'nickname', liveform.TEXT_INPUT,
                _normalizeWhitespace, 'Name',
                default=self.person.name)]
        for contact in self.organizer.getContactEditorialParameters(self.person):
            type, param = contact
            parameters.append(param)
            self.contactTypes[param.name] = type
        form = liveform.LiveForm(
            self.editContactItems, parameters, u'Save')
        form.compact()
        form.jsClass = u'Mantissa.People.EditPersonForm'
        form.setFragmentParent(self)
        return form


    def mugshotFormURL(self, request, tag):
        """
        Render a URL for L{MugshotUploadForm}.
        """
        return self.organizer.linkToPerson(self.person) + '/mugshotUploadForm'
    renderer(mugshotFormURL)


    def editorialContactForms(self, request, tag):
        """
        Add a L{LiveForm} for editing the contact information of the wrapped
        L{Person} to the given tag and return it.
        """
        return tag[self.makeEditorialLiveForm()]
    renderer(editorialContactForms)



class RealName(item.Item):
    """
    This is a legacy item left over from a previous schema.  Do not create it.
    """
    typeName = 'mantissa_organizer_addressbook_realname'
    schemaVersion = 2

    empty = attributes.reference()


item.declareLegacyItem(
    RealName.typeName, 1,
    dict(person=attributes.reference(
            doc="""
            allowNone=False,
            whenDeleted=attributes.reference.CASCADE,
            reftype=Person
            """),
         first=attributes.text(),
         last=attributes.text(indexed=True)))

registerDeletionUpgrader(RealName, 1, 2)



class EmailAddress(item.Item):
    """
    An email address contact info item associated with a L{Person}.

    Do not create this item directly, as functionality of L{IOrganizerPlugin}
    powerups will be broken if you do.  Instead, use
    L{Organizer.createContactItem} with L{EmailContactType}.
    """
    typeName = 'mantissa_organizer_addressbook_emailaddress'
    schemaVersion = 3

    address = attributes.text(allowNone=False)
    person = attributes.reference(
        allowNone=False,
        whenDeleted=attributes.reference.CASCADE,
        reftype=Person)
    label = attributes.text(
        """
        This is a label for the role of the email address, usually something like
        "home", "work", "school".
        """,
        allowNone=False,
        default=u'')

setIconURLForContactInfoType(EmailAddress, '/Mantissa/images/EmailAddress-icon.png')

def emailAddress1to2(old):
    return old.upgradeVersion('mantissa_organizer_addressbook_emailaddress',
                              1, 2,
                              address=old.address,
                              person=old.person)

registerUpgrader(emailAddress1to2,
                 'mantissa_organizer_addressbook_emailaddress',
                 1, 2)

item.declareLegacyItem(EmailAddress.typeName, 2, dict(
                  address = attributes.text(allowNone=False),
                  person = attributes.reference(allowNone=False)))

registerAttributeCopyingUpgrader(EmailAddress, 2, 3)


class PhoneNumber(item.Item):
    """
    A contact information item representing a L{Person}'s phone number.

    Do not create this item directly, as functionality of L{IOrganizerPlugin}
    powerups will be broken if you do.  Instead, use
    L{Organizer.createContactItem} with L{PhoneNumberContactType}.
    """
    typeName = 'mantissa_organizer_addressbook_phonenumber'
    schemaVersion = 3

    number = attributes.text(allowNone=False)
    person = attributes.reference(allowNone=False)
    label = attributes.text(
        """
        This is a label for the role of the phone number.
        """,
        allowNone=False,
        default=u'',)


    class LABELS:
        """
        Constants to use for the value of the L{label} attribute, describing
        the type of the telephone number.

        @ivar HOME: This is a home phone number.
        @type HOME: C{unicode}

        @ivar WORK: This is a work phone number.
        @type WORK: C{unicode}

        @ivar MOBILE: This is a mobile phone number.
        @type MOBILE: C{unicode}

        @ivar HOME_FAX: This is the 80's and someone has a fax machine in
        their house.
        @type HOME_FAX: C{unicode}

        @ivar WORK_FAX: This is the 80's and someone has a fax machine in
        their office.
        @type WORK_FAX: C{unicode}

        @ivar PAGER: This is the 80's and L{person} is a drug dealer.
        @type PAGER: C{unicode}

        @ivar ALL_LABELS: A sequence of all of the label constants.
        @type ALL_LABELS: C{list}
        """
        HOME = u'Home'
        WORK = u'Work'
        MOBILE = u'Mobile'
        HOME_FAX = u'Home Fax'
        WORK_FAX = u'Work Fax'
        PAGER = u'Pager'


        ALL_LABELS = [HOME, WORK, MOBILE, HOME_FAX, WORK_FAX, PAGER]



setIconURLForContactInfoType(PhoneNumber, '/Mantissa/images/PhoneNumber-icon.png')

def phoneNumber1to2(old):
    return old.upgradeVersion('mantissa_organizer_addressbook_phonenumber',
                              1, 2,
                              number=old.number,
                              person=old.person)

item.declareLegacyItem(PhoneNumber.typeName, 2, dict(
                  number = attributes.text(allowNone=False),
                  person = attributes.reference(allowNone=False)))

registerUpgrader(phoneNumber1to2,
                 'mantissa_organizer_addressbook_phonenumber',
                 1, 2)

registerAttributeCopyingUpgrader(PhoneNumber, 2, 3)



class PhoneNumberContactType(BaseContactType):
    """
    Contact type plugin which allows telephone numbers to be associated with
    people.
    """
    implements(IContactType)

    def getParameters(self, phoneNumber):
        """
        Return a C{list} of two liveform parameters, one for editing
        C{phoneNumber}'s I{number} attribute, and one for editing its I{label}
        attribute.

        @type phoneNumber: L{PhoneNumber} or C{NoneType}
        @param phoneNumber: If not C{None}, an existing contact item from
        which to get the parameter's default values.

        @rtype: C{list}
        """
        defaultNumber = u''
        defaultLabel = PhoneNumber.LABELS.HOME
        if phoneNumber is not None:
            defaultNumber = phoneNumber.number
            defaultLabel = phoneNumber.label
        labelChoiceParameter = liveform.ChoiceParameter(
            'label',
            [liveform.Option(label, label, label == defaultLabel)
                for label in PhoneNumber.LABELS.ALL_LABELS],
            'Number Type')
        return [
            labelChoiceParameter,
            liveform.Parameter(
                'number',
                liveform.TEXT_INPUT,
                unicode,
                'Phone Number',
                default=defaultNumber)]


    def descriptiveIdentifier(self):
        """
        Return 'Phone Number'
        """
        return u'Phone Number'


    def createContactItem(self, person, label, number):
        """
        Create a L{PhoneNumber} item for C{number}, associated with C{person}.

        @type person: L{Person}

        @param label: The value to use for the I{label} attribute of the new
        L{PhoneNumber} item.
        @type label: C{unicode}

        @param number: The value to use for the I{number} attribute of the new
        L{PhoneNumber} item.  If C{''}, no item will be created.
        @type number: C{unicode}

        @rtype: L{PhoneNumber} or C{NoneType}
        """
        if number:
            return PhoneNumber(
                store=person.store, person=person, label=label, number=number)


    def editContactItem(self, contact, label, number):
        """
        Change the I{number} attribute of C{contact} to C{number}, and the
        I{label} attribute to C{label}.

        @type contact: L{PhoneNumber}

        @type label: C{unicode}

        @type number: C{unicode}

        @return: C{None}
        """
        contact.label = label
        contact.number = number


    def getContactItems(self, person):
        """
        Return an iterable of L{PhoneNumber} items that are associated with
        C{person}.

        @type person: L{Person}
        """
        return person.store.query(
            PhoneNumber, PhoneNumber.person == person)


    def getReadOnlyView(self, contact):
        """
        Return a L{ReadOnlyPhoneNumberView} for the given L{PhoneNumber}.
        """
        return ReadOnlyPhoneNumberView(contact)



class ReadOnlyPhoneNumberView(Element):
    """
    Read-only view for L{PhoneNumber}.

    @type phoneNumber: L{PhoneNumber}
    """
    docFactory = ThemedDocumentFactory(
        'person-contact-read-only-phone-number-view', 'store')

    def __init__(self, phoneNumber):
        self.phoneNumber = phoneNumber
        self.store = phoneNumber.store


    def number(self, request, tag):
        """
        Add the value of L{phoneNumber}'s I{number} attribute to C{tag}.
        """
        return tag[self.phoneNumber.number]
    renderer(number)


    def label(self, request, tag):
        """
        Add the value of L{phoneNumber}'s I{label} attribute to C{tag}.
        """
        return tag[self.phoneNumber.label]
    renderer(label)



class PostalAddress(item.Item):
    typeName = 'mantissa_organizer_addressbook_postaladdress'

    address = attributes.text(allowNone=False)
    person = attributes.reference(
        allowNone=False,
        whenDeleted=attributes.reference.CASCADE,
        reftype=Person)

setIconURLForContactInfoType(PostalAddress, '/Mantissa/images/PostalAddress-icon.png')



class PostalContactType(BaseContactType):
    """
    Contact type plugin which allows a person to have a snail-mail address.
    """
    implements(IContactType)

    def getParameters(self, postalAddress):
        """
        Return a C{list} of one L{LiveForm} parameter for editing a
        L{PostalAddress}.

        @type postalAddress: L{PostalAddress} or C{NoneType}

        @param postalAddress: If not C{None}, an existing contact item from
            which to get the postal address default value.

        @rtype: C{list}
        @return: The parameters necessary for specifying a postal address.
        """
        address = u''
        if postalAddress is not None:
            address = postalAddress.address
        return [
            liveform.Parameter('address', liveform.TEXT_INPUT,
                               unicode, 'Postal Address', default=address)]


    def descriptiveIdentifier(self):
        """
        Return 'Postal Address'
        """
        return u'Postal Address'


    def createContactItem(self, person, address):
        """
        Create a new L{PostalAddress} associated with the given person based on
        the given postal address.

        @type person: L{Person}
        @param person: The person with whom to associate the new
            L{EmailAddress}.

        @type address: C{unicode}
        @param address: The value to use for the I{address} attribute of the
            newly created L{PostalAddress}.  If C{''}, no L{PostalAddress} will
            be created.

        @rtype: L{PostalAddress} or C{NoneType}
        """
        if address:
            return PostalAddress(
                store=person.store, person=person, address=address)


    def editContactItem(self, contact, address):
        """
        Change the postal address of the given L{PostalAddress} to that
        specified by C{address}.

        @type contact: L{PostalAddress}
        @param contact: The existing contact item to modify.

        @type address: C{unicode}
        @param address: The new value to use for the I{address} attribute of
            the L{PostalAddress}.

        @return: C{None}
        """
        contact.address = address


    def getContactItems(self, person):
        """
        Return a C{list} of the L{PostalAddress} items associated with the
        given person.

        @type person: L{Person}
        """
        return person.store.query(PostalAddress, PostalAddress.person == person)


    def getReadOnlyView(self, contact):
        """
        Return a L{ReadOnlyPostalAddressView} for the given L{PostalAddress}.
        """
        return ReadOnlyPostalAddressView(contact)



class ReadOnlyPostalAddressView(Element):
    """
    Display a postal address.

    @type _address: L{PostalAddress}
    @ivar _address: The postal address which will be displayed.
    """
    docFactory = ThemedDocumentFactory(
        'person-contact-read-only-postal-address-view', 'store')

    def __init__(self, address):
        self._address = address
        self.store = address.store


    def address(self, request, tag):
        """
        Add the wrapped L{PostalAddress} item's C{address} attribute as a child
        of the given tag.
        """
        return tag[self._address.address]
    renderer(address)



class Notes(item.Item):
    typeName = 'mantissa_organizer_addressbook_notes'

    notes = attributes.text(allowNone=False)
    person = attributes.reference(allowNone=False)

setIconURLForContactInfoType(Notes, '/Mantissa/images/Notes-icon.png')



class NotesContactType(BaseContactType):
    """
    Contact type plugin which allows a person to be annotated with a free-form
    textual note.
    """
    implements(IContactType)
    allowMultipleContactItems = False

    def getParameters(self, notes):
        """
        Return a C{list} of one L{LiveForm} parameter for editing a
        L{Notes}.

        @type notes: L{Notes} or C{NoneType}
        @param notes: If not C{None}, an existing contact item from
            which to get the parameter's default value.

        @rtype: C{list}
        """
        defaultNotes = u''
        if notes is not None:
            defaultNotes = notes.notes
        return [
            liveform.Parameter('notes', liveform.TEXTAREA_INPUT,
                               unicode, 'Notes', default=defaultNotes)]


    def descriptiveIdentifier(self):
        """
        Return 'Notes'
        """
        return u'Notes'


    def createContactItem(self, person, notes):
        """
        Create a new L{Notes} associated with the given person based on the
        given string.

        @type person: L{Person}
        @param person: The person with whom to associate the new L{Notes}.

        @type notes: C{unicode}
        @param notes: The value to use for the I{notes} attribute of the newly
        created L{Notes}.  If C{''}, no L{Notes} will be created.

        @rtype: L{Notes} or C{NoneType}
        """
        if notes:
            return Notes(
                store=person.store, person=person, notes=notes)


    def editContactItem(self, contact, notes):
        """
        Set the I{notes} attribute of C{contact} to the value of the C{notes}
        parameter.

        @type contact: L{Notes}
        @param contact: The existing contact item to modify.

        @type notes: C{unicode}
        @param notes: The new value to use for the I{notes} attribute of
            the L{Notes}.

        @return: C{None}
        """
        contact.notes = notes


    def getContactItems(self, person):
        """
        Return a C{list} of the L{Notes} items associated with the given
        person.  If none exist, create one, wrap it in a list and return it.

        @type person: L{Person}
        """
        notes = list(person.store.query(Notes, Notes.person == person))
        if not notes:
            return [Notes(store=person.store,
                          person=person,
                          notes=u'')]
        return notes


    def getReadOnlyView(self, contact):
        """
        Return a L{ReadOnlyNotesView} for the given L{Notes}.
        """
        return ReadOnlyNotesView(contact)



class ReadOnlyNotesView(Element):
    """
    Display notes for a person.

    @type _notes: L{Notes}
    """
    docFactory = ThemedDocumentFactory(
        'person-contact-read-only-notes-view', 'store')

    def __init__(self, notes):
        self._notes = notes
        self.store = notes.store


    def notes(self, request, tag):
        """
        Add the value of the I{notes} attribute of the wrapped L{Notes} as a
        child to the given tag.
        """
        return tag[self._notes.notes]
    renderer(notes)



class AddPerson(item.Item):
    implements(ixmantissa.INavigableElement)

    typeName = 'mantissa_add_person'
    schemaVersion = 2

    powerupInterfaces = (ixmantissa.INavigableElement,)
    organizer = dependsOn(Organizer)

    def getTabs(self):
        return []



def addPerson1to2(old):
    ap = old.upgradeVersion(old.typeName, 1, 2)
    ap.organizer = old.store.findOrCreate(Organizer)
    return ap

registerUpgrader(addPerson1to2, AddPerson.typeName, 1, 2)



class AddPersonFragment(athena.LiveFragment):
    """
    View class for L{AddPerson}, presenting a user interface for creating a new
    L{Person}.

    @ivar organizer: The L{Organizer} instance which will be used to add the
        person.
    """
    docFactory = ThemedDocumentFactory('add-person', 'store')

    jsClass = u'Mantissa.People.AddPerson'

    def __init__(self, organizer):
        athena.LiveFragment.__init__(self)
        self.organizer = organizer
        self.store = organizer.store


    def head(self):
        """
        Supply not content to the head area of the page.
        """
        return None


    _baseParameters = [
        liveform.Parameter('nickname', liveform.TEXT_INPUT,
                           _normalizeWhitespace, 'Name')]

    def _addPersonParameters(self):
        """
        Return some fixed fields for the person creation form as well as any
        fields from L{IOrganizerPlugin} powerups.
        """
        parameters = self._baseParameters[:]
        parameters.extend(self.organizer.getContactCreationParameters())
        return parameters


    def render_addPersonForm(self, ctx, data):
        """
        Create and return a L{liveform.LiveForm} for creating a new L{Person}.
        """
        addPersonForm = liveform.LiveForm(
            self.addPerson,
            self._addPersonParameters(),
            description='Add Person')
        addPersonForm.compact()
        addPersonForm.jsClass = u'Mantissa.People.AddPersonForm'
        addPersonForm.setFragmentParent(self)
        return addPersonForm


    def _addPerson(self, nickname, **allContactInfo):
        """
        Implementation of L{Person} creation.

        This method must be called in a transaction.

        @type nickname: C{unicode}
        @param nickname: The value for the I{name} attribute of the created
            L{Person}.

        @param **allContactInfo: Mapping of contact type IDs to L{ListChanges}
        objects or dictionaries of values.
        """
        organizer = self.organizer
        person = organizer.createPerson(nickname)

        # XXX This has the potential for breakage, if a new contact type is
        # returned by this call which was not returned by the call used to
        # generate the form, or vice versa.  I'll happily fix this the very
        # instant a button is present upon a web page which can provoke
        # this behavior. -exarkun
        contactTypes = dict((t.uniqueIdentifier(), t) for t in organizer.getContactTypes())
        for (contactTypeName, submission) in allContactInfo.iteritems():
            contactType = contactTypes[contactTypeName]
            if contactType.allowMultipleContactItems:
                for create in submission.create:
                    create.setter(organizer.createContactItem(
                        contactType, person, create.values))
            else:
                organizer.createContactItem(
                    contactType, person, submission)
        return person


    def addPerson(self, nickname, **contactInfo):
        """
        Create a new L{Person} with the given C{nickname} and contact items.

        @type nickname: C{unicode}
        @param nickname: The value for the I{name} attribute of the created
            L{Person}.

        @return: C{None}

        @raise L{liveform.InputError}: When some aspect of person creation
        raises a L{ValueError}.
        """
        try:
            self.store.transact(
                self._addPerson, nickname, **contactInfo)
        except ValueError, e:
            raise liveform.InputError(unicode(e))
    expose(addPerson)



class PersonExtractFragment(TabularDataView):
    def render_navigation(self, ctx, data):
        return inevow.IQ(
                webtheme.getLoader('person-extracts')).onePattern('navigation')



class ExtractWrapperColumnView(ColumnViewBase):
    def stanFromValue(self, idx, item, value):
        return inevow.IRenderer(item.extract)



class MugshotUploadForm(rend.Page):
    """
    Resource which presents some UI for assocating a new mugshot with
    L{person}.

    @ivar person: The person whose mugshot is going to be changed.
    @type person: L{Person}

    @ivar cbGotImage: Function to call after a successful upload.  It will be
    passed the C{unicode} content-type of the uploaded image and a file
    containing the uploaded image.
    """
    docFactory = ThemedDocumentFactory('mugshot-upload-form', 'store')

    def __init__(self, person, cbGotMugshot):
        rend.Page.__init__(self)
        self.person = person
        self.organizer  = person.organizer
        self.store = person.store
        self.cbGotMugshot = cbGotMugshot


    def renderHTTP(self, ctx):
        """
        Extract the data from the I{uploaddata} field of the request and pass
        it to our callback.
        """
        req = inevow.IRequest(ctx)
        if req.method == 'POST':
            udata = req.fields['uploaddata']
            self.cbGotMugshot(udata.type.decode('ascii'), udata.file)
        return rend.Page.renderHTTP(self, ctx)


    def render_smallerMugshotURL(self, ctx, data):
        """
        Render the URL of a smaller version of L{person}'s mugshot.
        """
        return self.organizer.linkToPerson(self.person) + '/mugshot/smaller'



class Mugshot(item.Item):
    """
    An image that is associated with a person
    """
    schemaVersion = 3

    type = attributes.text(doc="""
    Content-type of image data
    """, allowNone=False)

    body = attributes.path(doc="""
    Path to image data
    """, allowNone=False)

    # at the moment we require an upgrader to change the size of either of the
    # mugshot thumbnails.  we might save ourselves some effort by generating
    # scaled versions on demand, and caching them.
    smallerBody = attributes.path(doc="""
    Path to smaller version of image data
    """, allowNone=False)

    person = attributes.reference(doc="""
    L{Person} this mugshot is of
    """, allowNone=False)

    size = 120
    smallerSize = 60

    def fromFile(cls, person, inputFile, format):
        """
        Create a L{Mugshot} item for C{person} out of the image data in
        C{inputFile}, or update C{person}'s existing L{Mugshot} item to
        reflect the new images.

        @param inputFile: An image of a person.
        @type inputFile: C{file}

        @param person: The person this mugshot is to be associated with.
        @type person: L{Person}

        @param format: The format of the data in C{inputFile}.
        @type format: C{unicode} (e.g. I{jpeg})
        @type input

        @rtype: L{Mugshot}
        """
        body = cls.makeThumbnail(inputFile, person, format, smaller=False)
        inputFile.seek(0)
        smallerBody = cls.makeThumbnail(
            inputFile, person, format, smaller=True)

        ctype = u'image/' + format

        self = person.store.findUnique(
            cls, cls.person == person, default=None)
        if self is None:
            self = cls(store=person.store,
                       person=person,
                       type=ctype,
                       body=body,
                       smallerBody=smallerBody)
        else:
            self.body = body
            self.smallerBody = smallerBody
            self.type = ctype
        return self
    fromFile = classmethod(fromFile)


    def makeThumbnail(cls, inputFile, person, format, smaller):
        """
        Make a thumbnail of a mugshot image and store it on disk.

        @param inputFile: The image to thumbnail.
        @type inputFile: C{file}

        @param person: The person this mugshot thumbnail is associated with.
        @type person: L{Person}

        @param format: The format of the data in C{inputFile}.
        @type format: C{str} (e.g. I{jpeg})

        @param smaller: Thumbnails are available in two sizes.  if C{smaller}
        is C{True}, then the thumbnail will be in the smaller of the two
        sizes.
        @type smaller: C{bool}

        @return: path to the thumbnail.
        @rtype: L{twisted.python.filepath.FilePath}
        """
        dirsegs = ['mugshots', str(person.storeID)]
        if smaller:
            dirsegs.insert(1, 'smaller')
            size = cls.smallerSize
        else:
            size = cls.size
        atomicOutputFile = person.store.newFile(*dirsegs)
        makeThumbnail(inputFile, atomicOutputFile, size, format)
        atomicOutputFile.close()
        return atomicOutputFile.finalpath
    makeThumbnail = classmethod(makeThumbnail)


def mugshot1to2(old):
    """
    Upgrader for L{Mugshot} from version 1 to version 2, which sets the
    C{smallerBody} attribute to the path of a smaller mugshot image.
    """
    smallerBody = Mugshot.makeThumbnail(old.body.open(),
                                        old.person,
                                        old.type.split('/')[1],
                                        smaller=True)

    return old.upgradeVersion(Mugshot.typeName, 1, 2,
                              person=old.person,
                              type=old.type,
                              body=old.body,
                              smallerBody=smallerBody)

registerUpgrader(mugshot1to2, Mugshot.typeName, 1, 2)



item.declareLegacyItem(
    Mugshot.typeName,
    2,
    dict(person=attributes.reference(),
         type=attributes.text(),
         body=attributes.path(),
         smallerBody=attributes.path()))



def mugshot2to3(old):
    """
    Upgrader for L{Mugshot} from version 2 to version 3, which re-thumbnails
    the mugshot to take into account the new value of L{Mugshot.smallerSize}.
    """
    new = old.upgradeVersion(Mugshot.typeName, 2, 3,
                             person=old.person,
                             type=old.type,
                             body=old.body,
                             smallerBody=old.smallerBody)
    new.smallerBody = new.makeThumbnail(
        new.body.open(), new.person, new.type[len('image/'):], smaller=True)
    return new

registerUpgrader(mugshot2to3, Mugshot.typeName, 2, 3)



class MugshotResource(rend.Page):
    """
    Web accessible resource that serves Mugshot images. Serves a smaller
    mugshot if the final path segment is "smaller"
    """
    smaller = False

    def __init__(self, mugshot):
        """
        @param mugshot: L{Mugshot}
        """
        self.mugshot = mugshot
        rend.Page.__init__(self)


    def locateChild(self, ctx, segments):
        if segments == ('smaller',):
            self.smaller = True
            return (self, ())
        return rend.NotFound


    def renderHTTP(self, ctx):
        if self.smaller:
            path = self.mugshot.smallerBody
        else:
            path = self.mugshot.body

        return static.File(path.path, str(self.mugshot.type))

_CONTACT_INFO_ITEM_TYPES = [(PhoneNumber, 'number'),
                            (EmailAddress, 'address'),
                            (PostalAddress, 'address'),
                            (Notes, 'notes')]



def addContactInfoType(itemType, settableAttribute):
    """
    Register a new contact info item type C{itemType}, with value
    attribute C{settableAttribute}

    @param itemType: an item type
    @type itemType: L{MetaItem}

    @param settableAttribute: the name of a settable attribute on
    C{itemType}
    @type settableAttribute: C{str}
    """
    _CONTACT_INFO_ITEM_TYPES.append((itemType, settableAttribute))


def contactInfoItemTypeFromClassName(className):
    """
    Find the registered contact info item type with the class name of
    C{className}

    @return: the class and the value attribute name
    @rtype: 2-C{tuple} of C{MetaItem} and C{str}
    """
    # maybe this should use quals or something
    for (cls, attr) in _CONTACT_INFO_ITEM_TYPES:
        if cls.__name__ == className:
            return (cls, attr)


def getPersonURL(person):
    """
    Return the address the view for this Person is available at.
    """
    return person.organizer.linkToPerson(person)


class ContactInfoFragment(ThemedFragment):
    """
    Renderer for contact information about a L{Person}.
    """
    fragmentName = 'contact-info'
    jsClass = u'Mantissa.People.ContactInfo'

    def __init__(self, person, docFactory=None):
        """
        Initialize this instance.

        @type person: L{Person}
        @param person: The person object about whom contact information will
        be rendered.

        @param docFactory: A optional nevow document loader which will be
        used if specified.
        """
        athena.LiveFragment.__init__(self, docFactory=docFactory)
        self.person = person

    def render_mugshotLink(self, ctx, data):
        self.mugshot = self.person.getMugshot()
        if self.mugshot is None:
            return '/Mantissa/images/mugshot-placeholder.png'
        return getPersonURL(self.person) + '/mugshot'

    def render_mugshotFormAction(self, ctx, data):
        return getPersonURL(self.person) + '/uploadMugshot'


    def editContactInfoItem(self, typeName, oldValue, newValue):
        (cls, attr) = contactInfoItemTypeFromClassName(typeName)
        self.person.editContactInfoItem(
            cls, attr, oldValue, newValue)
    expose(editContactInfoItem)

    def createContactInfoItem(self, typeName, value):
        """
        Create a new contact information item for the wrapped person.

        @type typeName: C{unicode}
        @param typeName: The class name of the contact information to
        create.

        @param value: The value to use for the value column for the type
        specified.

        @see Person.createContactInfoItem

        @return: A fragment which will display the newly added contact info
        item.
        """
        (cls, attr) = contactInfoItemTypeFromClassName(typeName)
        self.person.createContactInfoItem(cls, attr, value)
        p = inevow.IQ(self.docFactory).onePattern('contact-info-item')
        fragment = self.__class__(self.person, docFactory=stan(p.fillSlots('value', value)))
        fragment.setFragmentParent(self)
        return fragment
    expose(createContactInfoItem)

    def deleteContactInfoItem(self, typeName, value):
        (cls, attr) = contactInfoItemTypeFromClassName(typeName)
        self.person.deleteContactInfoItem(cls, attr, value)
    expose(deleteContactInfoItem)


    def _renderSection(self, itemType, items):
        """
        Render the given contact info items.

        @type itemType: L{MetaItem}
        @param itemType: The type of contact info items to be rendered.

        @type values: C{list} of C{unicode}
        @param values: The contact info items to be rendered.

        @return: A flattenable object representing the given contact
        information.
        """
        iq = inevow.IQ(self.docFactory)
        sectionPattern = iq.onePattern('contact-info-section')
        itemPattern = iq.patternGenerator('contact-info-item')

        iconPath = iconURLForContactInfoType(itemType)

        return dictFillSlots(sectionPattern,
                        {'type': itemType.__name__,
                        'icon-path': iconPath,
                        'items': (itemPattern.fillSlots('value', item)
                                    for item in items)})

    def render_contactInfoSummary(self, ctx, data):
        """
        Render each of the kinds of contact information for C{self.person}.
        """
        for (itemType, valueColumn) in _CONTACT_INFO_ITEM_TYPES:
            yield self._renderSection(
                itemType, self.person.getContactInfoItems(
                    itemType, valueColumn))



class PersonDetailFragment(athena.LiveFragment, rend.ChildLookupMixin):
    """
    Renderer for detailed information about a L{Person}.
    """
    fragmentName = 'person-detail'
    live = 'athena'

    def __init__(self, person):
        athena.LiveFragment.__init__(self, person)
        self.person = person
        self.organizer = person.organizer
        self.title = person.getDisplayName()
        self.email = person.getEmailAddress()
        if self.email is not None:
            self.title += ' (%s)' % (self.email,)

        self.personFragments = list(ixmantissa.IPersonFragment(p)
                                        for p in self.organizer.peoplePlugins(person))

    def head(self):
        return None

    def render_personName(self, ctx, data):
        return ctx.tag[self.person.getDisplayName()]


    def render_contactInfo(self, ctx, data):
        """
        Render contact information for C{self.person}.

        @rtype: L{ContactInfoFragment}
        """
        f = ContactInfoFragment(self.person)
        f.setFragmentParent(self)
        f.docFactory = webtheme.getLoader(f.fragmentName)
        return f


    def render_extracts(self, ctx, data):
        tdm = TabularDataModel(
                self.person.store,
                ExtractWrapper,
                (ExtractWrapper.timestamp,),
                itemsPerPage=10,
                defaultSortAscending=False)

        f = PersonExtractFragment(tdm, (ExtractWrapperColumnView('extract'),))
        f.docFactory = webtheme.getLoader(f.fragmentName)
        f.setFragmentParent(self)
        return f


    def render_organizerPlugins(self, ctx, data):
        pat = inevow.IQ(self.docFactory).patternGenerator('person-fragment')
        for f in self.personFragments:
            if hasattr(f, 'setFragmentParent'):
                f.setFragmentParent(self)
            yield dictFillSlots(pat,
                                dict(title=f.title,
                                     fragment=f))


    def _gotMugshotFile(self, ctype, infile):
        (majortype, minortype) = ctype.split('/')
        if majortype == 'image':
            Mugshot.fromFile(self.person, infile, minortype)


    def child_mugshotUploadForm(self, ctx):
        """
        Return a L{MugshotUploadForm}, which will render some UI for
        associating a new mugshot with this person.
        """
        return MugshotUploadForm(self.person, self._gotMugshotFile)


    def child_mugshot(self, ctx):
        """
        Return the resource displaying this Person's mugshot picture, or a
        placeholder mugshot.
        """
        mugshot = self.person.getMugshot()
        if mugshot is None:
            imageDir = FilePath(__file__).parent().child(
                'static').child('images')
            mugshot = Mugshot(
                type=u'image/png',
                body=imageDir.child('mugshot-placeholder.png'),
                smallerBody=imageDir.child(
                    'smaller-mugshot-placeholder.png'),
                person=self.person)
        return MugshotResource(mugshot)



components.registerAdapter(PersonDetailFragment, Person, ixmantissa.INavigableFragment)

class PersonFragment(rend.Fragment):
    def __init__(self, person, contactMethod=None):
        rend.Fragment.__init__(self, person,
                               webtheme.getLoader('person-fragment'))
        self.person = person
        self.contactMethod = contactMethod

    def render_person(self, ctx, data):
        detailURL = self.person.organizer.linkToPerson(self.person)

        mugshot = self.person.store.findUnique(Mugshot,
                                               Mugshot.person == self.person,
                                               default=None)
        if mugshot is None:
            mugshotURL = '/Mantissa/images/smaller-mugshot-placeholder.png'
        else:
            mugshotURL = detailURL + '/mugshot/smaller'

        name = self.person.getDisplayName()
        return dictFillSlots(ctx.tag, {'name': name,
                                       'detail-url': detailURL,
                                       'contact-method': self.contactMethod or name,
                                       'mugshot-url': mugshotURL})
