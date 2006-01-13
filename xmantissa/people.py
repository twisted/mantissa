# -*- test-case-name: xmantissa.test.test_people -*-

import re
from operator import attrgetter
from itertools import islice
from string import uppercase

from zope.interface import implements

from twisted.python import components

from nevow import rend, athena, tags, inevow
from nevow.taglibrary import tabbedPane

from epsilon import extime

from axiom import item, attributes

from xmantissa import ixmantissa, webnav, webtheme, tdb, tdbview, liveform
from xmantissa.fragmentutils import dictFillSlots, PatternDictionary

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
    page = None

    def stanFromValue(self, idx, item, value):
        pf = PersonFragment(item)
        pf.page = self.page
        return pf

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

        personFragmentColumnView = PersonFragmentColumnView('name')
        personFragmentColumnView.page = self.page

        views = (personFragmentColumnView,
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

    person = attributes.reference()

    first = attributes.text()
    last = attributes.text()

    def _getDisplay(self):
        parts = (self.first, self.last)
        return ' '.join(filter(None, parts))
    display = property(_getDisplay)

class EmailAddress(item.Item):
    typeName = 'mantissa_organizer_addressbook_emailaddress'
    schemaVersion = 1

    address = attributes.text()
    person = attributes.reference()

class PhoneNumber(item.Item):
    typeName = 'mantissa_organizer_addressbook_phonenumber'
    schemaVersion = 1

    number = attributes.text()
    person = attributes.reference()

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

class AddPersonFragment(athena.LiveFragment):
    fragmentName = 'add-person'
    live = 'athena'

    def render_addPersonForm(self, ctx, data):
        WHITESPACE = re.compile(r'\s{2.}')

        def hasLengthOrNone(s):
            s = s.strip()
            s = WHITESPACE.sub(' ', s)
            if 0 == len(s):
                return None
            return s

        def kindOfAPhoneNumber(s):
            s = hasLengthOrNone(s)
            if s is not None:
                return s.replace('-', '').replace('.', '')

        def makeParam(name, desc, coerce=hasLengthOrNone):
            return liveform.Parameter(name, liveform.TEXT_INPUT, hasLengthOrNone, desc)

        addPersonForm = liveform.LiveForm(
            self.addPerson,
            (makeParam('nickname', 'Nickname'),
             makeParam('firstname', 'First Name'),
             makeParam('lastname', 'Last Name'),
             makeParam('email', 'Email Address'),
             makeParam('phone', 'Phone Number', kindOfAPhoneNumber)),
             description='Add Person')
        addPersonForm.docFactory = webtheme.getLoader('liveform-compact')
        addPersonForm.setFragmentParent(self)
        return addPersonForm

    def head(self):
        return None

    def addPerson(self, nickname, firstname, lastname, email, phone):
        if not (nickname or firstname or lastname):
            raise ValueError('pleast supply nickname or first/last name')
        if phone is not None and not phone.isdigit():
            raise ValueError('that doesnt look like a phone number')
        store = self.original.store
        if (nickname is not None
                and 1 == store.count(Person, Person.name==nickname, limit=1)):
            raise ValueError('nickname already taken')

        person = Person(store=store,
                        created=extime.Time(),
                        organizer=store.findUnique(Organizer),
                        name=nickname)
        if email:
            EmailAddress(store=store,
                         address=email,
                         person=person)

        if firstname is not None or lastname is not None:
            RealName(store=store,
                     person=person,
                     first=firstname,
                     last=lastname)

        if phone is not None:
            PhoneNumber(store=store,
                        person=person,
                        number=phone)

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

class PersonDetailFragment(athena.LiveFragment):
    fragmentName = 'person-detail'
    iface = {}
    live = 'athena'

    def __init__(self, person):
        athena.LiveFragment.__init__(self, person)
        self.person = person
        self.organizer = person.organizer
        self.title = person.getDisplayName()
        email = person.getEmailAddress()
        if email is not None:
            self.title += ' (%s)' % (email,)

        self.personFragments = list(ixmantissa.IPersonFragment(p)
                                        for p in self.organizer.peoplePlugins(person))

    def head(self):
        return tabbedPane.tabbedPaneGlue.inlineGlue

    def render_personName(self, ctx, data):
        return ctx.tag[self.person.getDisplayName()]

    def data_organizerPlugins(self, ctx, data):
        tabs = list()
        for f in self.personFragments:
            if hasattr(f, 'setFragmentParent'):
                f.setFragmentParent(self)
            tabs.append((f.title, f))

        return tabbedPane.tabbedPane(ctx, dict(pages=tabs))

components.registerAdapter(PersonDetailFragment, Person, ixmantissa.INavigableFragment)

class PersonFragment(athena.LiveFragment):
    jsClass = 'Mantissa.People.InlinePerson'
    iface = {}

    def __init__(self, person, contactMethod=None):
        rend.Fragment.__init__(self, person,
                               webtheme.getLoader('person-fragment'))
        self.person = person
        self.contactMethod = contactMethod
        self.patterns = PatternDictionary(self.docFactory)
        self.actions = list(person.powerupsFor(ixmantissa.IPersonAction))

    def render_person(self, ctx, data):
        detailURL = ixmantissa.IWebTranslator(self.person.store).linkTo(self.person.storeID)
        if self.contactMethod is None:
            cm = ''
        else:
            cm = self.patterns['contact-method'].fillSlots('name', self.contactMethod)

        if 0 < len(self.actions):
            actions = dictFillSlots(self.patterns['actions'],
                                    {'actions': list(a.toLinkStan() for a in self.actions),
                                     'name': self.person.name,
                                     'email': self.person.getEmailAddress()})
        else:
            actions = ''

        return dictFillSlots(ctx.tag, {'name': self.person.getDisplayName(),
                                       'detail-url': detailURL,
                                       'contact-method': cm,
                                       'actions': actions})
