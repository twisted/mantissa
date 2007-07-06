# -*- test-case-name: xmantissa.test.test_people -*-

import re
from itertools import islice
from string import uppercase
from warnings import warn

try:
    from PIL import Image
except ImportError:
    Image = None

from zope.interface import implements

from twisted.python import components
from twisted.python.reflect import qual

from nevow import rend, athena, inevow, static, url
from nevow.athena import expose
from nevow.loaders import stan
from nevow.page import renderer

from epsilon import extime

from axiom import item, attributes
from axiom.dependency import dependsOn, installOn
from axiom.attributes import AND
from axiom.upgrade import registerUpgrader, registerAttributeCopyingUpgrader


from xmantissa import ixmantissa, webnav, webtheme, liveform
from xmantissa.liveform import FORM_INPUT, Parameter
from xmantissa.ixmantissa import IOrganizerPlugin, IContactType
from xmantissa.webapp import PrivateApplication
from xmantissa.tdbview import TabularDataView, ColumnViewBase
from xmantissa.tdb import TabularDataModel
from xmantissa.scrolltable import ScrollingFragment, UnsortableColumn
from xmantissa.fragmentutils import dictFillSlots
from xmantissa.webtheme import ThemedFragment, ThemedElement

def makeThumbnail(infile, outfile, thumbSize, format='jpeg'):
    assert Image is not None, 'you need PIL installed if you want to thumbnail things'
    image = Image.open(infile)
    (width, height) = image.size
    scale = float(thumbSize) / max(max(width, height), thumbSize)
    image.resize((int(width * scale),
                  int(height * scale)), Image.ANTIALIAS).save(outfile, format)

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



class BaseContactType(object):
    """
    Base class for L{IContactType} implementations which provides useful
    default behavior.
    """
    def uniqueIdentifier(self):
        """
        Uniquely identify this contact type.
        """
        return qual(self.__class__).decode('ascii')


    def getParameters(self, contact):
        """
        Return a list of L{liveform.Parameter} objects to be used by
        L{getCreationForm} to create a L{liveform.LiveForm}.

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


    def getCreationForm(self):
        """
        Create a L{liveform.LiveForm} for creating this kind of contact item using the
        parameters returned by L{getParameters}.
        """
        return liveform.LiveForm(self.coerce, self.getParameters(None))


    def getEditorialForm(self, contact):
        """
        Create a L{liveform.LiveForm} for editing an instance of this kind of
        contact item using the parameters returned by L{getParameters}.
        """
        return liveform.LiveForm(self.coerce, self.getParameters(contact))



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



class NameContactType(BaseContactType):
    """
    Contact type plugin which allows a person to have a name.
    """
    implements(IContactType)

    def getParameters(self, realName):
        """
        Return a C{list} of two L{LiveForm} parameters for editing the first
        and last name of a L{RealName}.

        @type realName: L{RealName}
        @param realName: If not C{None}, an existing contact item from which to
            get the default values for the first and last name parameters.

        @rtype: C{list}
        @return: The parameters necessary for specifying a person's real name.
        """
        if realName is not None:
            first = realName.first
            last = realName.last
        else:
            first = u''
            last = u''
        return [
            liveform.Parameter('firstname', liveform.TEXT_INPUT,
                               _normalizeWhitespace, 'First Name',
                               default=first),
            liveform.Parameter('lastname', liveform.TEXT_INPUT,
                               _normalizeWhitespace, 'Last Name',
                               default=last)]


    def createContactItem(self, person, firstname, lastname):
        """
        Create a new L{RealName} associated with the given person based on the
        given parameters.

        @type person: L{Person}
        @param person: The person with whom to associate the new L{RealName}.

        @type firstname: C{unicode}
        @param firstname: The value to use for the I{first} attribute of the
            created L{RealName}.

        @type lastname: C{unicode}
        @param lastname: The value to use for the I{last} attribute of the
            created L{RealName}.

        @return: C{None}
        """
        if firstname or lastname:
            return RealName(store=person.store,
                            person=person,
                            first=firstname,
                            last=lastname)


    def getContactItems(self, person):
        """
        Return all L{RealName} instances associated with the given person.

        @type person: L{Person}
        @return: An iterable of L{RealName} instances.
        """
        return person.store.query(
            RealName,
            RealName.person == person)


    def editContactItem(self, contact, firstname, lastname):
        """
        Change the first and last name of the given L{RealName} to the values
        specified by C{parameters}.

        @type contact: L{RealName}

        @type firstname: C{unicode}
        @param firstname: The value to use for the I{first} attribute of the
            created L{RealName}.

        @type lastname: C{unicode}
        @param lastname: The value to use for the I{last} attribute of the
            created L{RealName}.

        @return: C{None}
        """
        contact.first = firstname
        contact.last = lastname



class PeopleBenefactor(item.Item):
    implements(ixmantissa.IBenefactor)
    endowed = attributes.integer(default=0)
    powerupNames = ["xmantissa.people.AddPerson"]



class Person(item.Item):
    typeName = 'mantissa_person'
    schemaVersion = 1

    organizer = attributes.reference(
        "The L{Organizer} to which this Person belongs.")
    # we don't really use Person.name for anything -
    # it seems like a bit of a strange thing to have
    # in addition to a RealName
    name = attributes.text(
        "This name of this person.")
    created = attributes.timestamp()

    def __init__(self, **kw):
        kw['created'] = extime.Time()
        super(Person, self).__init__(**kw)

    def getDisplayName(self):
        # XXX figure out the default
        for rn in self.store.query(RealName, RealName.person == self):
            return rn.display
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

class ExtractWrapper(item.Item):
    extract = attributes.reference(whenDeleted=attributes.reference.CASCADE)
    timestamp = attributes.timestamp(indexed=True)
    person = attributes.reference(reftype=Person,
                                  whenDeleted=attributes.reference.CASCADE)



class Organizer(item.Item):
    """
    Oversee the creation, location, destruction, and modification of
    people in a particular set (eg, the set of people you know).
    """
    implements(ixmantissa.INavigableElement)

    typeName = 'mantissa_people'
    schemaVersion = 2

    _webTranslator = dependsOn(PrivateApplication)

    powerupInterfaces = (ixmantissa.INavigableElement,)


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
        yield NameContactType()
        yield EmailContactType(self.store)
        yield PostalContactType()
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
            yield Parameter(
                contactType.uniqueIdentifier(),
                FORM_INPUT,
                contactType.getCreationForm())


    def getContactEditorialParameters(self, person):
        """
        Yield L{LiveForm} parameters to edit each contact item of each contact
        type for the given person.

        @type person: L{Person}
        @return: An iterable of three-tuples.  The first element of each tuple
            is an L{IContactType} provider.  The second element of each tuple
            is a contact item which was created by that L{IContactType}
            provider.  The third element of each tuple is the L{LiveForm}
            parameter object for that copntact item.
        """
        counter = 0
        for contactType in self.getContactTypes():
            contactItems = contactType.getContactItems(person)
            for contactItem in contactItems:
                yield (contactType, contactItem, Parameter(
                        str(counter),
                        FORM_INPUT,
                        contactType.getEditorialForm(contactItem)))
                counter += 1


    def createPerson(self, nickname):
        """
        Create a new L{Person} with the given name in this organizer.

        @type nickname: C{unicode}
        @param nickname: The value for the new person's C{name} attribute.

        @rtype: L{Person}
        """
        person = Person(
            store=self.store,
            created=extime.Time(),
            organizer=self,
            name=nickname)
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
            person, **dict([
                    (k.encode('ascii'), v)
                    for (k, v)
                    in contactInfo.iteritems()]))
        if contactItem is not None:
            self._callOnOrganizerPlugins('contactItemCreated', contactItem)


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


    def lastNamesBetweenComparison(self, begin, end):
        """
        Return an IComparison which will restrict a query for Person items to
        those with last names which compare greater than or equal to begin and
        less than end.
        """
        return AND(
            RealName.person == Person.storeID,
            RealName.last >= begin,
            RealName.last < end)


    def lastNameOrder(self):
        """
        Return an IAttribute to sort people by their last name.
        """
        return RealName.last


    def peoplePlugins(self, person):
        return (
            p.personalize(person)
            for p
            in self.powerupsFor(ixmantissa.IOrganizerPlugin))

    def linkToPerson(self, person):
        """
        @param person: L{Person} instance
        @return: string url at which C{person} will be rendered
        """
        return (self._webTranslator.linkTo(self.storeID) +
                '/' + self._webTranslator.toWebID(person))

    def getTabs(self):
        ourURL = self._webTranslator.linkTo(self.storeID)
        children = [webnav.Tab('All', self.storeID, 0.1)]

        letters = iter(uppercase)
        while True:
            chars = ''.join(islice(letters, 3))
            if 0 == len(chars):
                break

            linkURL = ourURL + '?show-group=' + chars
            children.append(webnav.Tab(chars, None, 0.0, linkURL=linkURL))

        return [webnav.Tab('People', self.storeID, 0.5,
                           authoritative=True, children=children)]

def organizer1to2(old):
    o = old.upgradeVersion(old.typeName, 1, 2)
    o._webTranslator = old.store.findOrCreate(PrivateApplication)
    return o

registerUpgrader(organizer1to2, Organizer.typeName, 1, 2)

class PersonNameColumn(UnsortableColumn):
    def extractValue(self, model, item):
        return item.getDisplayName()


class PersonScrollingFragment(ScrollingFragment):
    """
    Scrolling fragment which displays L{Person} objects and allows actions to
    be taken on them.

    @ivar _performAction: A function of two arguments which will be invoked
        with an action name and a L{Person} to handle actions from the client.
        Its return value will be sent back as the result of the action.
    """
    jsClass = u'Mantissa.People.PersonScroller'

    def __init__(self, store, baseConstraint, defaultSortColumn,
                 webTranslator, performAction):
        ScrollingFragment.__init__(
            self,
            store,
            Person,
            baseConstraint,
            [PersonNameColumn(None, 'name')],
            defaultSortColumn=defaultSortColumn,
            webTranslator=webTranslator)
        self._performAction = performAction


    def performAction(self, actionName, rowIdentifier):
        """
        Dispatch the given action to C{self._performAction}.
        """
        return self._performAction(
            actionName,
            self.itemFromLink(rowIdentifier))
    expose(performAction)



class OrganizerFragment(athena.LiveFragment, rend.ChildLookupMixin):
    """
    @type organizer: L{Organizer}
    @ivar organizer: The organizer for which this is a view.
    """
    fragmentName = 'people-organizer'
    live = 'athena'
    title = 'People'
    jsClass = u'Mantissa.People.Organizer'

    def __init__(self, organizer):
        self.organizer = organizer
        self.wt = organizer._webTranslator
        athena.LiveFragment.__init__(self)


    def _createPeopleScrollTable(self, baseComparison, sort):
        """
        Make a L{PersonScrollingFragment} as a child of this fragment, load its
        docFactory, and return it.
        """
        f = PersonScrollingFragment(
                self.organizer.store,
                baseComparison,
                sort,
                self.wt,
                self.performAction)
        f.setFragmentParent(self)
        f.docFactory = webtheme.getLoader(f.fragmentName)
        return f


    def _getBaseComparison(self, ctx):
        req = inevow.IRequest(ctx)
        group = req.args.get('show-group', [''])[0].decode('ascii', 'replace')
        if group:
            # We assume the only groups being shown consist of consecutive
            # letters.  If someone gives us something else, too bad for them.
            return self.organizer.lastNamesBetweenComparison(
                group[0],
                unichr(ord(group[-1]) + 1))
        return RealName.person == Person.storeID


    def getAddPerson(self):
        """
        Return an L{AddPersonFragment} which is a child of this fragment and
        which will add a person to C{self.organizer}.
        """
        fragment = AddPersonFragment(self.organizer)
        fragment.setFragmentParent(self)
        return fragment
    expose(getAddPerson)


    def render_peopleTable(self, ctx, data):
        """
        Return a L{PersonScrollingFragment} which will display the L{Person}
        items in the wrapped organizer.
        """
        comparison = self._getBaseComparison(ctx)
        sort = self.organizer.lastNameOrder()
        return self._createPeopleScrollTable(comparison, sort)


    def head(self):
        return None


    def performAction(self, actionName, person):
        """
        Do something with an item by dispatching to a method suitable for the
        action with the given name.

        @type person: L{Person}
        """
        return getattr(self, 'action_' + actionName)(person)


    def action_edit(self, person):
        """
        Create a form which can be used to edit the given person.
        """
        view = EditPersonView(person)
        view.setFragmentParent(self)
        return view


    def action_delete(self, person):
        """
        Delete the given person.
        """
        self.organizer.deletePerson(person)

components.registerAdapter(OrganizerFragment, Organizer, ixmantissa.INavigableFragment)



class EditPersonView(ThemedElement):
    """
    Render a view for editing the contact information for a L{Person}.

    @ivar person: L{Person} which can be edited.

    @ivar contactItems: A mapping from parameter names to the contact items
        those parameters will edit.
    """
    fragmentName = 'edit-person'

    def __init__(self, person):
        athena.LiveElement.__init__(self)
        self.person = person
        self.contactItems = {}


    def editContactItems(self, nickname, **edits):
        """
        Update the information on the contact items associated with the wrapped
        L{Person}.

        @type nickname: C{unicode}
        @param nickname: New value to use for the I{name} attribute of the
            L{Person}.

        @param **edits: A mapping of parameter names to edit information from
            that parameter.
        """
        def editPerson():
            self.person.name = nickname
            for paramName, contactInfo in edits.iteritems():
                contactType, contactItem = self.contactItems.pop(paramName)
                contactInfo = dict([
                        (k.encode('ascii'), v)
                        for (k, v)
                        in contactInfo.iteritems()])
                contactType.editContactItem(contactItem, **contactInfo)
        self.person.store.transact(editPerson)


    def editorialContactForms(self, request, tag):
        """
        Add an L{LiveForm} for editing the contact information of the wrapped
        L{Person} to the given tag and return it.
        """
        organizer = self.person.organizer
        parameters = [
            liveform.Parameter(
                'nickname', liveform.TEXT_INPUT,
                _normalizeWhitespace, 'Nickname',
                default=self.person.name)]
        for contact in organizer.getContactEditorialParameters(self.person):
            type, item, param = contact
            parameters.append(param)
            self.contactItems[param.name] = (type, item)
        form = liveform.LiveForm(self.editContactItems, parameters)
        form.jsClass = u'Mantissa.People.EditPersonForm'
        form.setFragmentParent(self)
        return tag[form]
    renderer(editorialContactForms)



class _AddressBook(item.Item):
    typeName = 'mantissa_organizer_personalized_addressbook'
    schemaVersion = 1

    person = attributes.reference(doc="""
    A reference to the Mantissa Person Item to which this pertains.
    """)

    displayName = attributes.text(doc="""
    Short string displayed in the user interface whenever a name for
    this person is called for.
    """)

class AddressBookFragment(athena.LiveFragment):
    def __init__(self, original):
        athena.LiveFragment.__init__(self, original)
        self.docFactory = webtheme.getLoader('address-book')

    def data_names(self, ctx, data):
        ab = self.original
        s = ab.store
        return (
            {"first-name": p.first, "last-name": p.last}
            for p
            in s.query(RealName, RealName.person == ab.person))

    def addName(self, name):
        parts = name.rsplit(None, 1)
        if len(parts) == 1:
            first, last = u'', parts[0]
        else:
            first, last = parts
        RealName(
            store=self.original.store,
            person=self.original.person,
            first=first,
            last=last)
    expose(addName)


    def head(self):
        return None

components.registerAdapter(AddressBookFragment, _AddressBook, ixmantissa.INavigableFragment)

class RealName(item.Item):
    typeName = 'mantissa_organizer_addressbook_realname'
    schemaVersion = 1

    person = attributes.reference(
        allowNone=False,
        whenDeleted=attributes.reference.CASCADE,
        reftype=Person)

    first = attributes.text()
    last = attributes.text(indexed=True)

    def _getDisplay(self):
        return u' '.join(filter(None, (self.first, self.last)))
    display = property(_getDisplay)



class EmailAddress(item.Item):
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
    typeName = 'mantissa_organizer_addressbook_phonenumber'
    schemaVersion = 3

    number = attributes.text(allowNone=False)
    person = attributes.reference(allowNone=False)
    label = attributes.text(
        """
        This is a label for the role of the phone number, usually something like
        "home", "office", "mobile".
        """,
        allowNone=False,
        default=u'',)

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
    def getParameters(self, postalAddress):
        """
        Return a C{list} of one L{LiveForm} parameter for editing a
        L{PostalAddress}.

        @type postalAddress: L{PostalAddress} or C{NoneType}

        @param emailAddress: If not C{None}, an existing contact item from
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
            be created.  create.

        @return: C{None}
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


class Notes(item.Item):
    typeName = 'mantissa_organizer_addressbook_notes'

    notes = attributes.text(allowNone=False)
    person = attributes.reference(allowNone=False)

setIconURLForContactInfoType(Notes, '/Mantissa/images/Notes-icon.png')



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



class AddPersonFragment(ThemedFragment):
    """
    View class for L{AddPerson}, presenting a user interface for creating a new
    L{Person}.

    @ivar organizer: The L{Organizer} instance which will be used to add the
        person.
    """
    fragmentName = 'add-person'
    live = 'athena'

    def __init__(self, organizer):
        athena.LiveFragment.__init__(self)
        self.organizer = organizer


    def head(self):
        """
        Supply not content to the head area of the page.
        """
        return None


    def _addPersonParameters(self):
        """
        Return some fixed fields for the person creation form as well as any
        fields from L{IOrganizerPlugin} powerups.
        """
        parameters = [liveform.Parameter('nickname', liveform.TEXT_INPUT,
                                         _normalizeWhitespace, 'Nickname')]
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
        addPersonForm.docFactory = webtheme.getLoader('liveform-compact')
        addPersonForm.setFragmentParent(self)
        return addPersonForm


    def _addPerson(self, nickname, **allContactInfo):
        organizer = self.organizer
        person = organizer.createPerson(nickname)

        # XXX This has the potential for breakage, if a new contact type is
        # returned by this call which was not returned by the call used to
        # generate the form, or vice versa.  I'll happily fix this the very
        # instant a button is present upon a web page which can provoke
        # this behavior. -exarkun
        for contactType in organizer.getContactTypes():
            contactInfo = allContactInfo[contactType.uniqueIdentifier()]
            organizer.createContactItem(contactType, person, contactInfo)
        return person


    def addPerson(self, nickname, **contactInfo):
        self.organizer.store.transact(self._addPerson, nickname, **contactInfo)
        return u'Made A Person!'
    expose(addPerson)



class AddressBook(item.Item):
    implements(ixmantissa.IOrganizerPlugin)

    typeName = 'mantissa_organizer_addressbook'
    schemaVersion = 1

    installedOn = attributes.reference(doc="""
    The Organizer on which this is installed.
    """)

    powerupInterfaces = (ixmantissa.IOrganizerPlugin,)

    def personalize(self, person):
        return self.store.findOrCreate(
            _AddressBook,
            person=person)

class PersonExtractFragment(TabularDataView):
    def render_navigation(self, ctx, data):
        return inevow.IQ(
                webtheme.getLoader('person-extracts')).onePattern('navigation')

class ExtractWrapperColumnView(ColumnViewBase):
    def stanFromValue(self, idx, item, value):
        return inevow.IRenderer(item.extract)

class MugshotUploadPage(rend.Page):
    def __init__(self, cbGotFile, redirectTo):
        self._cbGotFile = cbGotFile
        self._redirectTo = redirectTo
        rend.Page.__init__(self)

    def renderHTTP(self, ctx):
        req = inevow.IRequest(ctx)
        if req.method == 'POST':
            udata = req.fields['uploaddata']
            self._cbGotFile(udata.type, udata.file)
            req.redirect(url.URL.fromString(self._redirectTo))
            return ''
        else:
            return rend.Page.renderHTTP(self, ctx)

class Mugshot(item.Item):
    """
    An image that is associated with a person
    """
    schemaVersion = 2

    type = attributes.text(doc="""
    Content-type of image data
    """, allowNone=False)

    body = attributes.path(doc="""
    Path to image data
    """, allowNone=False)

    smallerBody = attributes.path(doc="""
    Path to smaller version of image data
    """, allowNone=False)

    person = attributes.reference(doc="""
    L{Person} this mugshot is of
    """, allowNone=False)

    size = 120
    smallerSize = 22

    def fromFile(cls, person, infile, format):
        """
        Create a Mugshot item from an image file.

        @param person: L{Person} instance (who the mugshot is of)
        @param infile: C{file} (where the image data is)
        @param format: C{unicode} (what format the image data is in)

        @return: L{Mugshot} instance, in the same store as C{person}
        """

        inst = person.store.findUnique(cls, cls.person == person, default=None)

        body = cls.makeThumbnail(infile, person, format)
        infile.seek(0)
        smallerBody = cls.makeThumbnail(infile, person, format, smaller=True)

        ctype = 'image/' + format

        if inst is None:
            inst = cls(store=person.store,
                       person=person,
                       type=ctype,
                       body=body,
                       smallerBody=smallerBody)
        else:
            inst.body = body
            inst.smallerBody = smallerBody
            inst.type = ctype

        return inst
    fromFile = classmethod(fromFile)

    def makeThumbnail(cls, infile, person, ctype, smaller=False):
        """
        Make a thumbnail of an image and store it on disk.

        @param infile: C{file} (where the image data is)
        @param person: L{Person} instance (who is this image of)
        @param ctype: content-type of data in C{infile}
        @param smaller: thumbnails are available in two sizes.
                        if C{smaller} is true, then the thumbnail
                        will be in the smaller of the two sizes.

        @return: filesystem path of the new thumbnail
        """


        dirsegs = ['mugshots', str(person.storeID)]

        if smaller:
            dirsegs.insert(1, 'smaller')
            size = cls.smallerSize
        else:
            size = cls.size

        outfile = person.store.newFile(*dirsegs)
        makeThumbnail(infile, outfile, size, ctype)
        outfile.close()
        return outfile.finalpath
    makeThumbnail = classmethod(makeThumbnail)


def mugshot1to2(old):
    smallerBody = Mugshot.makeThumbnail(old.body.open(),
                                        old.person,
                                        old.type.split('/')[1],
                                        smaller=True)

    return old.upgradeVersion(Mugshot.typeName, 1, 2,
                              type=old.type,
                              body=old.body,
                              person=old.person,
                              smallerBody=smallerBody)


registerUpgrader(mugshot1to2, Mugshot.typeName, 1, 2)

class MugshotResource(rend.Page):
    """
    Web accessible resource that serves Mugshot images. Serves
    a smaller mugshot if the final path segment is "smaller"
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



class ContactInfoFragment(athena.LiveFragment, rend.ChildLookupMixin):
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

    def _gotMugshotFile(self, ctype, infile):
        (majortype, minortype) = ctype.split('/')

        if majortype == 'image':
            Mugshot.fromFile(self.person, infile, unicode(minortype, 'ascii'))

    def child_uploadMugshot(self, ctx):
        return MugshotUploadPage(self._gotMugshotFile, self.getMyURL())

    def child_mugshot(self, ctx):
        return MugshotResource(
                    self.person.store.findUnique(
                        Mugshot, Mugshot.person == self.person))

    def render_mugshotLink(self, ctx, data):
        self.mugshot = self.person.store.findUnique(
                            Mugshot, Mugshot.person == self.person, default=None)
        if self.mugshot is None:
            return '/Mantissa/images/mugshot-placeholder.png'
        return self.getMyURL() + '/mugshot'

    def render_mugshotFormAction(self, ctx, data):
        return self.getMyURL() + '/uploadMugshot'

    def getMyURL(self):
        return self.person.organizer.linkToPerson(self.person)

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
