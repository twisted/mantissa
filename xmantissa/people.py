# -*- test-case-name: xmantissa.test.test_people -*-

import re
from itertools import islice
from string import uppercase

from zope.interface import implements

from twisted.python import components

from nevow import rend, athena, inevow
from nevow.taglibrary import tabbedPane

from epsilon import extime

from axiom import item, attributes

from xmantissa import ixmantissa, webnav, webtheme, tdb, tdbview, liveform
from xmantissa.fragmentutils import dictFillSlots

class PeopleBenefactor(item.Item):
    implements(ixmantissa.IBenefactor)
    endowed = attributes.integer(default=0)

    def installOn(self, other):
        other.powerUp(self, ixmantissa.IBenefactor)

    def endow(self, ticket, avatar):
        avatar.findOrCreate(Organizer).installOn(avatar)
        avatar.findOrCreate(AddPerson).installOn(avatar)
        self.endowed += 1

    def revoke(self, ticket, avatar):
        for cls in (Organizer, AddPerson):
            item = avatar.findUnique(cls)
            avatar.powerDown(item, ixmantissa.INavigableElement)
            item.deleteFromStore()

        self.endowed -= 1

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


    def getDisplayName(self):
        # XXX figure out the default
        for rn in self.store.query(RealName, RealName.person == self):
            return rn.display
        return self.name

    def getEmailAddress(self):
        # XXX figure out the default address
        for email in self.store.query(EmailAddress, EmailAddress.person == self):
            return email.address

    def __init__(self, **kw):
        kw['created'] = extime.Time()
        super(Person, self).__init__(**kw)


class Organizer(item.Item, item.InstallableMixin):
    """
    Oversee the creation, location, destruction, and modification of
    people in a particular set (eg, the set of people you know).
    """
    implements(ixmantissa.INavigableElement)

    typeName = 'mantissa_people'
    schemaVersion = 1

    installedOn = attributes.reference()

    def installOn(self, other):
        super(Organizer, self).installOn(other)
        other.powerUp(self, ixmantissa.INavigableElement)

        # This is not how this should work
        #AddressBook(store=self.store).installOn(self)

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

    def people(self, where, **kw):
        return self.store.query(
            Person,
            attributes.AND(where, Person.organizer == self),
            **kw)

    def peoplePlugins(self, person):
        return (
            p.personalize(person)
            for p
            in self.powerupsFor(ixmantissa.IOrganizerPlugin))

    def getTabs(self):
        ourURL = ixmantissa.IWebTranslator(self.store).linkTo(self.storeID)
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

class EmailAddressColumnView(tdbview.ColumnViewBase):
    def stanFromValue(self, idx, item, value):
        email = item.getEmailAddress()
        if email is None:
            return 'No Email'
        return email

class PersonFragmentColumnView(tdbview.ColumnViewBase):
    def stanFromValue(self, idx, item, value):
        return PersonFragment(item)

class OrganizerFragment(athena.LiveFragment):
    fragmentName = 'people-organizer'
    live = 'athena'
    title = 'People'
    jsClass = 'Mantissa.People.Organizer'

    allowedMethods = iface = {'addPerson': True}
    prefs = None
    baseComparison = None

    def __init__(self, original):
        self.prefs = ixmantissa.IPreferenceAggregator(original.store)
        athena.LiveFragment.__init__(self, original)

    def _createPeopleTDB(self, baseComparison):
        # this is a property because we need to set the 'page'
        # attribute of the child fragment, but we dont have that
        # in __init__

        tdm = tdb.TabularDataModel(
                self.original.store,
                Person, [Person.name, Person.created],
                baseComparison=baseComparison,
                defaultSortColumn='name',
                itemsPerPage=self.prefs.getPreferenceValue('itemsPerPage'))

        views = (PersonFragmentColumnView('name'),
                 EmailAddressColumnView('Email Address'),
                 tdbview.DateColumnView('created'))

        peopleTDB = tdbview.TabularDataView(tdm, views)
        peopleTDB.page = self.page
        peopleTDB.docFactory = webtheme.getLoader(peopleTDB.fragmentName)
        return peopleTDB

    def _getBaseComparison(self, ctx):
        req = inevow.IRequest(ctx)
        (group,) = req.args.get('show-group', [None])
        if group is not None:
            clauses = list()
            for letter in group:
                q = attributes.AND(RealName.person == Person.storeID,
                                   RealName.last.like(u'%c%%' % letter))
                clauses.append(q)
            return attributes.OR(*clauses)

    def render_peopleTable(self, ctx, data):
        comparison = self._getBaseComparison(ctx)
        self.peopleTDB = self._createPeopleTDB(comparison)
        return ctx.tag[self.peopleTDB]

    def head(self):
        return None

components.registerAdapter(OrganizerFragment, Organizer, ixmantissa.INavigableFragment)

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

    allowedMethods = {"addName": None}
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

    def head(self):
        return None

components.registerAdapter(AddressBookFragment, _AddressBook, ixmantissa.INavigableFragment)

class RealName(item.Item):
    typeName = 'mantissa_organizer_addressbook_realname'
    schemaVersion = 1

    person = attributes.reference(allowNone=False)

    first = attributes.text()
    last = attributes.text()

    def _getDisplay(self):
        return ' '.join(filter(None, (self.first, self.last)))
    display = property(_getDisplay)

class EmailAddress(item.Item):
    typeName = 'mantissa_organizer_addressbook_emailaddress'
    schemaVersion = 1

    address = attributes.text(allowNone=False)
    person = attributes.reference(allowNone=False)
    type = attributes.text(allowNone=False) #default|home|business

class PhoneNumber(item.Item):
    typeName = 'mantissa_organizer_addressbook_phonenumber'
    schemaVersion = 1

    number = attributes.text(allowNone=False)
    person = attributes.reference(allowNone=False)
    type = attributes.text(allowNone=False) #default|home|business

class AddPerson(item.Item, item.InstallableMixin):
    implements(ixmantissa.INavigableElement)

    typeName = 'mantissa_add_person'
    schemaVersion = 1

    installedOn = attributes.reference()

    def installOn(self, other):
        super(AddPerson, self).installOn(other)
        other.powerUp(self, ixmantissa.INavigableElement)

    def getTabs(self):
        return [webnav.Tab('People', self.storeID, 0.0, children=[
                    webnav.Tab('Add Person', self.storeID, 0.2)],
                           authoritative=False)]

def _hasLengthOrNone(s):
    WHITESPACE = re.compile(r'\s{2.}')

    s = s.strip()
    s = WHITESPACE.sub(' ', s)
    if 0 == len(s):
        return None
    return s

class AddPersonFragment(athena.LiveFragment):
    fragmentName = 'add-person'
    live = 'athena'

    def render_addPersonForm(self, ctx, data):
        def makeParam(name, desc, coerce=_hasLengthOrNone):
            return liveform.Parameter(name, liveform.TEXT_INPUT, coerce, desc)

        addPersonForm = liveform.LiveForm(
            self.addPerson,
            (makeParam('firstname', 'First Name'),
             makeParam('lastname', 'Last Name'),
             makeParam('email', 'Email Address'),
             makeParam('nickname', 'Nickname')),
             description='Add Person')
        addPersonForm.docFactory = webtheme.getLoader('liveform-compact')
        addPersonForm.setFragmentParent(self)
        return addPersonForm

    def head(self):
        return None

    def makePerson(self, nickname):
        return Person(store=self.original.store,
                      created=extime.Time(),
                      organizer=self.original.store.findUnique(Organizer),
                      name=nickname)

    def addPerson(self, nickname, firstname, lastname, email):
        if not (nickname or firstname or lastname):
            raise ValueError('pleast supply nickname or first/last name')
        store = self.original.store
        if nickname is None:
            nickname = u''

        person = self.makePerson(nickname)

        if email:
            EmailAddress(store=store,
                         address=email,
                         person=person,
                         type=u'default')

        if firstname is not None or lastname is not None:
            RealName(store=store,
                     person=person,
                     first=firstname,
                     last=lastname)

        return u'Made A Person!'

components.registerAdapter(AddPersonFragment, AddPerson, ixmantissa.INavigableFragment)

class AddressBook(item.Item, item.InstallableMixin):
    implements(ixmantissa.IOrganizerPlugin)

    typeName = 'mantissa_organizer_addressbook'
    schemaVersion = 1

    installedOn = attributes.reference(doc="""
    The Organizer on which this is installed.
    """)

    def installOn(self, other):
        super(AddressBook, self).installOn(other)
        other.powerUp(self, ixmantissa.IOrganizerPlugin)

    def personalize(self, person):
        return self.store.findOrCreate(
            _AddressBook,
            person=person)

class ContactInfoFragment(athena.LiveFragment):
    iface = {}

    def __init__(self, person):
        super(ContactInfoFragment, self).__init__(person)
        self.person = person
        self.docFactory = webtheme.getLoader('person-contact-info')

    emailTypes = phoneTypes = (u'default', u'home', u'business')

    def render_contactInfo(self, ctx, data):
        s = self.person.store
        rn = s.findFirst(RealName, RealName.person == self.person)

        if rn is None:
            first = last = ''
        else:
            (first, last) = (rn.first, rn.last)

        def itemsByType(itemClass, types):
            d = dict((i.type, i) for i in s.query(itemClass, itemClass.person == self.person))
            d.update((type, None) for type in types if type not in d)
            return d

        self.emails = itemsByType(EmailAddress, self.emailTypes)
        self.phones = itemsByType(PhoneNumber, self.phoneTypes)

        def makeParam(name, desc, default, coerce=_hasLengthOrNone):
            return liveform.Parameter(name, liveform.TEXT_INPUT, coerce, desc, default)

        editPersonForm = liveform.LiveForm(
            self.editPerson,
            [makeParam('firstname', 'First Name', first),
             makeParam('lastname', 'Last Name', last),
             makeParam('nickname', 'Nickname', self.person.name)] +

            [makeParam(k + 'Email',
                       k.capitalize() + ' Email',
                       getattr(v, 'address', ''))

                for (k, v) in self.emails.iteritems()] +

            [makeParam(k + 'Phone',
                       k.capitalize() + ' Phone',
                       getattr(v, 'number', ''))

                for (k, v) in self.phones.iteritems()],

            description='Save')

        self.realname = rn

        editPersonForm.docFactory = webtheme.getLoader('liveform-compact')
        editPersonForm.setFragmentParent(self)
        return editPersonForm

    def editPerson(self, **k):
        getval = k.__getitem__

        if self.person.name != getval('nickname'):
            self.person.name = getval('nickname')

        firstname = getval('firstname')
        lastname  = getval('lastname')

        haveEither = firstname is not None or lastname is not None

        if haveEither:
            if self.realname is None:
                RealName(store=self.person.store,
                         person=self.person,
                         first=firstname,
                         last=lastname)
            elif (firstname != self.realname.first
                    or lastname != self.realname.last):
                if self.realname.first != firstname:
                    self.realname.first = firstname
                if self.realname.last != lastname:
                    self.realname.last = lastname

        for (typeMap, typeSuffix, attr) in ((self.emails, 'Email', EmailAddress.address),
                                            (self.phones, 'Phone', PhoneNumber.number)):
            for (_type, item) in typeMap.iteritems():
                newval = getval(_type + typeSuffix)
                if item is None:
                    if newval is not None:
                        attr.type(store=self.person.store,
                                  person=self.person,
                                  type=_type,
                                  **{attr.attrname: newval})
                elif newval is not None:
                    if getattr(item, attr.attrname) != newval:
                        setattr(item, attr.attrname, newval)
                else:
                    item.deleteFromStore()

        return u'Updated Person'

class PersonDetailFragment(athena.LiveFragment):
    fragmentName = 'person-detail'
    iface = {}
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
        return tabbedPane.tabbedPaneGlue.inlineCSS

    def render_personName(self, ctx, data):
        return ctx.tag[self.person.getDisplayName()]

    def render_contactInformationSummary(self, ctx, data):
        # FIXME like getEmailAddress() and getDisplayName(),
        # we need to allow the user to set defaults, so we
        # can show the default phone number for person X, 
        # instead of the first one we find in the store

        phone = self.original.store.findFirst(PhoneNumber,
                                              PhoneNumber.person == self.original)
        if phone is not None:
            phone = phone.number

        return dictFillSlots(ctx.tag,
                             dict(email=self.email or 'None',
                                  phone=phone or 'None'))


    def render_organizerPlugins(self, ctx, data):
        contactInfo = ContactInfoFragment(self.person)
        contactInfo.setFragmentParent(self)

        tabs = [('Contact Info', contactInfo)]
        for f in self.personFragments:
            if hasattr(f, 'setFragmentParent'):
                f.setFragmentParent(self)
            tabs.append((f.title, f))

        tpf = tabbedPane.TabbedPaneFragment(tabs)
        tpf.setFragmentParent(self)
        return tpf

components.registerAdapter(PersonDetailFragment, Person, ixmantissa.INavigableFragment)

class PersonFragment(rend.Fragment):
    def __init__(self, person, contactMethod=None):
        rend.Fragment.__init__(self, person,
                               webtheme.getLoader('person-fragment'))
        self.person = person
        self.contactMethod = contactMethod

    def render_person(self, ctx, data):
        detailURL = ixmantissa.IWebTranslator(self.person.store).linkTo(self.person.storeID)

        name = self.person.getDisplayName()
        return dictFillSlots(ctx.tag, {'name': name,
                                       'detail-url': detailURL,
                                       'contact-method': self.contactMethod or name})
