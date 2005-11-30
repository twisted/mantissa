# -*- test-case-name: xmantissa.test.test_people -*-

from zope.interface import Interface, implements

from twisted.python import components

from nevow import rend, athena

from epsilon import extime

from vertex import q2q

from axiom import item, attributes

from xmantissa import ixmantissa, webnav, webtheme, webapp

class Person(item.Item):
    typeName = 'mantissa_person'
    schemaVersion = 1

    organizer = attributes.reference(
        "The L{Organizer} to which this Person belongs.")
    name = attributes.text(
        "This name of this person.")
    created = attributes.timestamp()

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
        AddressBook(store=self.store).installOn(self)

    def personByName(self, name):
        """
        Retrieve the L{Person} item for the given Q2Q address,
        creating it first if necessary.

        @type name: C{unicode}
        """
        return self.store.findOrCreate(Person, organizer=self, name=name)

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
        return [webnav.Tab('People', self.storeID, 0.5, authoritative=True)]

class OrganizerFragment(athena.LiveFragment):
    fragmentName = 'people-organizer'
    live = 'athena'
    title = 'People'
    allowedMethods = iface = {'personByName': True}

    def head(self):
        return ()

    def _simplify(self, person):
        wt = webapp.IWebTranslator(person.store)
        return {
            u'name': person.name,
            u'created': unicode(person.created.asISO8601TimeAndDate(), 'ascii'),
            u'storeID': person.storeID,
            u'detail-href': unicode(wt.linkTo(person.storeID), 'ascii')}

    def getPeople(self):
        return (self._simplify(p) for p in self.original.people())

    def personByName(self, name):
        p = self.original.personByName(name)
        return self._simplify(p)

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
    docFactory = webtheme.getLoader('address-book')

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


components.registerAdapter(AddressBookFragment, _AddressBook, ixmantissa.IPersonFragment)

class RealName(item.Item):
    typeName = 'mantissa_organizer_addressbook_realname'
    schemaVersion = 1

    person = attributes.reference()

    first = attributes.text()
    last = attributes.text()

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

class PersonFragment(rend.Fragment):
    fragmentName = 'person-detail'
    live = 'athena'
    iface = {}

    def __init__(self, person):
        rend.Fragment.__init__(self)
        self.person = person
        self.organizer = person.organizer
        self.title = person.name

    def head(self):
        return ()

    def render_personName(self, ctx, data):
        return ctx.tag[self.person.name]

    def render_organizerPlugins(self, ctx, data):
        fragments = []
        for p in self.organizer.peoplePlugins(self.person):
            f = ixmantissa.IPersonFragment(p)
            f.page = self.page
            fragments.append(f)
        return ctx.tag[fragments]

components.registerAdapter(PersonFragment, Person, ixmantissa.INavigableFragment)
