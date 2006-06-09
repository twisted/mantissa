# -*- test-case-name: xmantissa.test.test_people -*-

import re
from itertools import islice
from string import uppercase

from zope.interface import implements

from twisted.python import components

from nevow import rend, athena, inevow, static, url
from nevow.flat import flatten

from epsilon import extime

from axiom import item, attributes
from axiom.upgrade import registerUpgrader

from xmantissa import ixmantissa, webnav, webtheme, liveform
from xmantissa.tdbview import TabularDataView, ColumnViewBase
from xmantissa.tdb import TabularDataModel
from xmantissa.scrolltable import ScrollingFragment, UnsortableColumn
from xmantissa.fragmentutils import dictFillSlots

from PIL import Image

def makeThumbnail(infile, outfile, thumbSize=200, format='jpeg'):
    image = Image.open(infile)
    (width, height) = image.size
    scale = float(thumbSize) / max(max(width, height), thumbSize)
    image.resize((int(width * scale),
                  int(height * scale)), Image.ANTIALIAS).save(outfile, format)

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

    def __init__(self, **kw):
        kw['created'] = extime.Time()
        super(Person, self).__init__(**kw)

    def getDisplayName(self):
        # XXX figure out the default
        for rn in self.store.query(RealName, RealName.person == self):
            return rn.display
        return self.name

    def getEmailAddress(self):
        # XXX figure out the default address
        for email in self.store.query(EmailAddress, EmailAddress.person == self):
            return email.address

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

class ExtractWrapper(item.Item):
    extract = attributes.reference(whenDeleted=attributes.reference.CASCADE)
    timestamp = attributes.timestamp(indexed=True)
    person = attributes.reference(reftype=Person,
                                  whenDeleted=attributes.reference.CASCADE)

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

class PersonNameColumn(UnsortableColumn):
    def extractValue(self, model, item):
        return item.getDisplayName()

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
        f = ScrollingFragment(
                self.original.store,
                Person,
                baseComparison,
                [PersonNameColumn(None, 'name'), Person.created],
                defaultSortColumn=Person.name)

        f.setFragmentParent(self)
        f.docFactory = webtheme.getLoader(f.fragmentName)
        return f

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
    schemaVersion = 2

    address = attributes.text(allowNone=False)
    person = attributes.reference(allowNone=False)

def emailAddress1to2(old):
    return old.upgradeVersion('mantissa_organizer_addressbook_emailaddress',
                              1, 2,
                              address=old.address,
                              person=old.person)

registerUpgrader(emailAddress1to2,
                 'mantissa_organizer_addressbook_emailaddress',
                 1, 2)

class PhoneNumber(item.Item):
    typeName = 'mantissa_organizer_addressbook_phonenumber'
    schemaVersion = 2

    number = attributes.text(allowNone=False)
    person = attributes.reference(allowNone=False)

def phoneNumber1to2(old):
    return old.upgradeVersion('mantissa_organizer_addressbook_phonenumber',
                              1, 2,
                              number=old.number,
                              person=old.person)

registerUpgrader(phoneNumber1to2,
                 'mantissa_organizer_addressbook_phonenumber',
                 1, 2)

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
                         person=person)

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
    type = attributes.text(allowNone=False) # content type
    body = attributes.path(allowNone=False) # path to image data

    person  = attributes.reference(allowNone=False)

class PersonDetailFragment(athena.LiveFragment, rend.ChildLookupMixin):
    fragmentName = 'person-detail'
    live = 'athena'
    jsClass = 'Mantissa.People.PersonDetail'

    iface = allowedMethods = {'createContactInfoItem': True,
                              'editContactInfoItem': True,
                              'deleteContactInfoItem': True}

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

        self.myURL = ixmantissa.IWebTranslator(person.store).linkTo(person.storeID)

    def _gotMugshotFile(self, ctype, infile):
        (majortype, minortype) = ctype.split('/')
        if majortype != 'image':
            return

        outfile = self.person.store.newFile('mugshots', str(self.person.storeID))
        makeThumbnail(infile, outfile, format=minortype)
        outfile.close()

        ctype = unicode(ctype, 'ascii')
        mugshot = self.person.store.findUnique(
                        Mugshot, Mugshot.person == self.person, default=None)

        if mugshot is None:
            Mugshot(store=self.person.store,
                    person=self.person,
                    type=ctype,
                    body=outfile.finalpath)
        else:
            mugshot.type = ctype
            mugshot.body = outfile.finalpath

    def child_uploadMugshot(self, ctx):
        return MugshotUploadPage(self._gotMugshotFile, self.myURL)

    def child_mugshot(self, ctx):
        mugshot = self.person.store.findUnique(Mugshot, Mugshot.person == self.person)
        return static.File(mugshot.body.path, str(mugshot.type))

    def render_mugshotLink(self, ctx, data):
        self.mugshot = self.person.store.findUnique(
                            Mugshot, Mugshot.person == self.person, default=None)
        if self.mugshot is None:
            return '/Mantissa/images/mugshot-placeholder.png'
        return self.myURL + '/mugshot'

    def render_mugshotFormAction(self, ctx, data):
        return self.myURL + '/uploadMugshot'

    def editContactInfoItem(self, typeName, oldValue, newValue):
        for (cls, attr) in self.contactInfoItemTypes:
            if typeName == cls.__name__:
                item = self.person.store.findFirst(cls,
                            attributes.AND(
                                getattr(cls, attr) == oldValue,
                                cls.person == self.person))
                setattr(item, attr, newValue)
                break

    def createContactInfoItem(self, typeName, value):
        for (cls, attr) in self.contactInfoItemTypes:
            if typeName == cls.__name__:
                cls(person=self.person,
                    store=self.person.store,
                    **{attr: value})
                p = inevow.IQ(self.docFactory).onePattern('contact-info-item')
                return unicode(flatten(p.fillSlots('value', value)), 'utf-8')

    def deleteContactInfoItem(self, typeName, value):
        for (cls, attr) in self.contactInfoItemTypes:
            if typeName == cls.__name__:
                self.person.store.findFirst(cls,
                        attributes.AND(
                            getattr(cls, attr) == value,
                            cls.person == self.person)).deleteFromStore()
                break

    def head(self):
        return None

    def render_personName(self, ctx, data):
        return ctx.tag[self.person.getDisplayName()]

    contactInfoItemTypes = ((PhoneNumber, 'number'),
                            (EmailAddress, 'address'))

    def render_contactInfoSummary(self, ctx, data):
        iq = inevow.IQ(self.docFactory)
        itemPattern = iq.patternGenerator('contact-info-item')
        sectionPattern = iq.patternGenerator('contact-info-section')
        sections = []

        return ctx.tag.fillSlots('sections',
            (dictFillSlots(sectionPattern,
                           {'type': itemType.__name__,
                            'icon-path': '/Mantissa/images/' + itemType.__name__ + '-icon.png',
                            'items': (itemPattern.fillSlots('value', value)
                                         for value in self.person.store.query(
                                             itemType, itemType.person == self.person).getColumn(valueColumn))})
                for (itemType, valueColumn) in self.contactInfoItemTypes))

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
        detailURL = ixmantissa.IWebTranslator(self.person.store).linkTo(self.person.storeID)

        name = self.person.getDisplayName()
        return dictFillSlots(ctx.tag, {'name': name,
                                       'detail-url': detailURL,
                                       'contact-method': self.contactMethod or name})
