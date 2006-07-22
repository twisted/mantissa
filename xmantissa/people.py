# -*- test-case-name: xmantissa.test.test_people -*-

import re
from itertools import islice
from string import uppercase

from zope.interface import implements

from twisted.python import components

from nevow import rend, athena, inevow, static, url, tags
from nevow.flat import flatten
from nevow.athena import expose

from epsilon import extime, descriptor

from axiom import item, attributes
from axiom.upgrade import registerUpgrader

from xmantissa import ixmantissa, webnav, webtheme, liveform
from xmantissa.tdbview import TabularDataView, ColumnViewBase
from xmantissa.tdb import TabularDataModel
from xmantissa.scrolltable import ScrollingFragment, UnsortableColumn
from xmantissa.fragmentutils import dictFillSlots

try:
    from PIL import Image
except ImportError:
    Image = None

def makeThumbnail(infile, outfile, thumbSize, format='jpeg'):
    assert Image is not None, 'you need PIL installed if you want to thumbnail things'
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

    def registerExtract(self, extract, etype, timestamp=None):
        """
        @param extract: some Item that implements L{inevow.IRenderer}
        """
        if timestamp is None:
            timestamp = extime.Time()

        return ExtractWrapper(store=self.store,
                              extract=extract,
                              extractType=etype,
                              timestamp=timestamp,
                              person=self)

    def getExtractWrappers(self, etype, n):
        return self.store.query(ExtractWrapper,
                                attributes.AND(
                                    ExtractWrapper.person == self,
                                    ExtractWrapper.extractType == etype),
                                sort=ExtractWrapper.timestamp.desc,
                                limit=n)

    def getUniqueExtractTypes(self):
        query = self.store.query(ExtractWrapper,
                                 ExtractWrapper.person == self)
        return query.getColumn('extractType').distinct()

class ExtractWrapper(item.Item):
    extract = attributes.reference(
                whenDeleted=attributes.reference.CASCADE)
    extractType = attributes.text(indexed=True)
    timestamp = attributes.timestamp(indexed=True)
    person = attributes.reference(
                reftype=Person,
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
    _webTranslator = attributes.inmemory()

    def activate(self):
        self._webTranslator = None

    class webTranslator(descriptor.attribute):
        def get(self):
            if self._webTranslator is None:
                self._webTranslator = ixmantissa.IWebTranslator(self.store)
            return self._webTranslator

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

    def linkToPerson(self, person):
        """
        @param person: L{Person} instance
        @return: string url at which C{person} will be rendered
        """
        return (self.webTranslator.linkTo(self.storeID) +
                '/' + self.webTranslator.toWebID(person))

    def getTabs(self):
        ourURL = self.webTranslator.linkTo(self.storeID)
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

class OrganizerFragment(athena.LiveFragment, rend.ChildLookupMixin):
    fragmentName = 'people-organizer'
    live = 'athena'
    title = 'People'
    jsClass = 'Mantissa.People.Organizer'

    def __init__(self, original):
        self.wt = original.webTranslator
        athena.LiveFragment.__init__(self, original)

    def _createPeopleScrollTable(self, baseComparison):
        f = ScrollingFragment(
                self.original.store,
                Person,
                baseComparison,
                [PersonNameColumn(None, 'name'), Person.created],
                defaultSortColumn=Person.name)
        # use linkToPerson() to make item links so that rows point to
        # a version of the person URL that'll highlight the people tab
        f.linkToItem = lambda item: unicode(self.original.linkToPerson(item), 'ascii')
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
        return self._createPeopleScrollTable(comparison)

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
    expose(addPerson)

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

class PersonDetailFragment(athena.LiveFragment, rend.ChildLookupMixin):
    fragmentName = 'person-detail'
    live = 'athena'
    jsClass = 'Mantissa.People.PersonDetail'

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

        self.myURL = self.organizer.linkToPerson(person)

    def _gotMugshotFile(self, ctype, infile):
        (majortype, minortype) = ctype.split('/')

        if majortype == 'image':
            Mugshot.fromFile(self.person, infile, unicode(minortype, 'ascii'))

    def child_uploadMugshot(self, ctx):
        return MugshotUploadPage(self._gotMugshotFile, self.myURL)

    def child_mugshot(self, ctx):
        return MugshotResource(
                    self.person.store.findUnique(
                        Mugshot, Mugshot.person == self.person))

    def render_mugshotLink(self, ctx, data):
        self.mugshot = self.person.store.findUnique(
                            Mugshot, Mugshot.person == self.person, default=None)
        if self.mugshot is None:
            return '/Mantissa/images/mugshot-placeholder.png'
        return self.myURL + '/mugshot'

    def render_mugshotFormAction(self, ctx, data):
        return self.myURL + '/uploadMugshot'

    def render_extractChiclets(self, ctx, data):
        pattern = inevow.IQ(self.docFactory).patternGenerator('extract-chiclet')
        for etype in self.person.getUniqueExtractTypes():
            yield pattern.fillSlots('type', etype)

    def getExtractPod(self, etype):
        iq = inevow.IQ(self.docFactory)
        extractRowPattern = iq.patternGenerator('extract-row')
        items = self.person.getExtractWrappers(etype, 5)

        p = dictFillSlots(
             iq.onePattern('person-fragment'),
                dict(title=etype,
                     fragment=(extractRowPattern.fillSlots(
                                'extract', inevow.IRenderer(i.extract))
                                for i in items)))
        return unicode(flatten(p), 'utf-8')

    expose(getExtractPod)

    def editContactInfoItem(self, typeName, oldValue, newValue):
        for (cls, attr) in self.contactInfoItemTypes:
            if typeName == cls.__name__:
                item = self.person.store.findFirst(cls,
                            attributes.AND(
                                getattr(cls, attr) == oldValue,
                                cls.person == self.person))
                setattr(item, attr, newValue)
                break
    expose(editContactInfoItem)

    def createContactInfoItem(self, typeName, value):
        for (cls, attr) in self.contactInfoItemTypes:
            if typeName == cls.__name__:
                cls(person=self.person,
                    store=self.person.store,
                    **{attr: value})
                p = inevow.IQ(self.docFactory).onePattern('contact-info-item')
                return unicode(flatten(p.fillSlots('value', value)), 'utf-8')
    expose(createContactInfoItem)

    def deleteContactInfoItem(self, typeName, value):
        for (cls, attr) in self.contactInfoItemTypes:
            if typeName == cls.__name__:
                self.person.store.findFirst(cls,
                        attributes.AND(
                            getattr(cls, attr) == value,
                            cls.person == self.person)).deleteFromStore()
                break
    expose(deleteContactInfoItem)

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
                ExtractWrapper.person == self.person,
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
