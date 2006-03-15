import sys

from nevow import loaders, tags
from nevow.livetrial.testcase import TestCase

from axiom.store import Store
from axiom import attributes

from xmantissa import people

class AddPersonTestBase(people.AddPersonFragment):
    jsClass = u'Mantissa.Test.People'

    def __init__(self):
        self.store = Store()
        self.original  = people.AddPerson(store=self.store)
        self.organizer = people.Organizer(store=self.store)

        super(AddPersonTestBase, self).__init__()

        self.docFactory = loaders.stan(
                tags.div(render=tags.directive('liveTest'))[
                    tags.invisible(render=tags.directive('addPersonForm'))])

    def mangleDefaults(self, params):
        pass

    def checkResult(self):
        pass

    def addPerson(self, *a, **k):
        try:
            super(AddPersonTestBase, self).addPerson(*a, **k)
        except:
            self.exc_info = sys.exc_info()
        else:
            self.exc_info = None

        self.checkResult()

    def render_addPersonForm(self, ctx, data):
        liveform = super(AddPersonTestBase, self).render_addPersonForm(ctx, data)
        params = dict((p.name, p) for p in liveform.parameters)
        self.mangleDefaults(params)
        return liveform

class NoNickOrFirstLastNames(AddPersonTestBase, TestCase):
    def checkResult(self):
        self.assertEqual(self.exc_info[0], ValueError)
        for cls in (people.Person, people.EmailAddress):
            self.assertEqual(self.store.count(cls), 0)

class NoNickButFirstLastNames(AddPersonTestBase, TestCase):
    def mangleDefaults(self, params):
        params['firstname'].default = u'FIRSTNAME'
        params['lastname'].default = u'LASTNAME'

    def checkResult(self):
        self.assertEqual(self.exc_info, None)

        p = self.store.findUnique(people.Person)
        self.assertEqual(p.name, '')
        self.assertEqual(p.organizer, self.organizer)
        p.deleteFromStore()

        rn = self.store.findUnique(people.RealName)
        self.assertEqual(rn.first, 'FIRSTNAME')
        self.assertEqual(rn.last, 'LASTNAME')
        self.assertEqual(rn.person, p)
        rn.deleteFromStore()
        self.assertEqual(self.store.count(people.EmailAddress), 0)

class OnlyNick(AddPersonTestBase, TestCase):
    def mangleDefaults(self, params):
        params['nickname'].default = u'everybody'

    def checkResult(self):
        self.assertEqual(self.exc_info, None)

        p = self.store.findUnique(people.Person)
        self.assertEqual(p.name, 'everybody')
        self.assertEqual(p.organizer, self.organizer)
        p.deleteFromStore()

        self.assertEqual(self.store.count(people.EmailAddress), 0)
        self.assertEqual(self.store.count(people.RealName), 0)

class OnlyEmailAddress(AddPersonTestBase, TestCase):
    def mangleDefaults(self, params):
        params['email'].default = u'bob@the.internet'

    def checkResult(self):
        self.assertEqual(self.exc_info[0], ValueError)

        for cls in (people.Person, people.RealName, people.EmailAddress):
            self.assertEqual(self.store.count(cls), 0)

class NickNameAndEmailAddress(AddPersonTestBase, TestCase):
    def mangleDefaults(self, params):
        params['nickname'].default = u'NICK!!!'
        params['email'].default = u'a@b.c'

    def checkResult(self):
        self.assertEqual(self.exc_info, None)

        p = self.store.findUnique(people.Person)
        self.assertEqual(p.name, 'NICK!!!')
        self.assertEqual(p.organizer, self.organizer)
        p.deleteFromStore()

        e = self.store.findUnique(people.EmailAddress)
        self.assertEqual(e.address, 'a@b.c')
        self.assertEqual(e.person, p)
        self.assertEqual(e.type, 'default')
        e.deleteFromStore()

        self.assertEqual(self.store.count(people.RealName), 0)

class ContactInfoTestBase(people.ContactInfoFragment):
    jsClass = u'Mantissa.Test.People'

    def __init__(self):
        self.store = Store()
        super(ContactInfoTestBase, self).__init__(self.makePerson())

        self.docFactory = loaders.stan(
            tags.div(render=tags.directive('liveTest'))[
                tags.invisible(render=tags.directive('contactInfo'))])

    # override this
    def makePerson(self):
        self.person = people.Person(name=u'Bob', store=self.store)
        return self.person

    # and this
    def mangleDefaults(self, params):
        pass

    # and this.  this will get called after editPerson,
    # so fail the test here if appropriate
    def checkResult(self):
        pass

    def editPerson(self, *a, **k):
        super(ContactInfoTestBase, self).editPerson(*a, **k)
        self.checkResult()

    def render_contactInfo(self, ctx, data):
        liveform = super(ContactInfoTestBase, self).render_contactInfo(ctx, data)
        params = dict((p.name, p) for p in liveform.parameters)
        self.mangleDefaults(params)
        return liveform

class EditEmails(ContactInfoTestBase, TestCase):

    def makePerson(self):
        super(EditEmails, self).makePerson()

        people.EmailAddress(person=self.person,
                            store=self.store,
                            address=u'bob@divmod.com',
                            type=u'default')
        people.EmailAddress(person=self.person,
                            store=self.store,
                            address=u'bob.business@divmod.com',
                            type=u'business')
        return self.person

    def mangleDefaults(self, params):
        params['defaultEmail'].default = u'bob.default@divmod.com'
        params['homeEmail'].default = u'bob.home@divmod.com'
        params['businessEmail'].default = u''

    def checkResult(self):
        EA = people.EmailAddress
        def assertAddrEquals(_type, addr, delete=True):
            ea = self.store.findUnique(EA,
                                       attributes.AND(EA.person == self.person,
                                                      EA.type == _type))
            self.assertEqual(ea.address, addr)
            if delete:
                ea.deleteFromStore()

        assertAddrEquals(u'default', u'bob.default@divmod.com', False)
        assertAddrEquals(u'home', u'bob.home@divmod.com')

class EditRealName(ContactInfoTestBase, TestCase):

    def mangleDefaults(self, params):
        params['firstname'].default = u'Bob'
        params['lastname'].default = u'The Slob'

    def checkResult(self):
        rn = self.store.findUnique(people.RealName,
                                   people.RealName.person == self.person)

        self.assertEqual(rn.display, 'Bob The Slob')
        rn.deleteFromStore()

class EditNickname(ContactInfoTestBase, TestCase):

    def mangleDefaults(self, params):
        params['nickname'].default = u'Bobby'

    def checkResult(self):
        self.assertEqual(self.person.name, 'Bobby')


class EditPhoneNumber(ContactInfoTestBase, TestCase):

    def mangleDefaults(self, params):
        params['defaultPhone'].default = u'555-1212'
        params['businessPhone'].default = u'555-2323'

    def checkResult(self):
        PN = people.PhoneNumber
        def assertNumberEquals(_type, addr):
            pn = self.store.findUnique(PN,
                                       attributes.AND(PN.person == self.person,
                                                      PN.type == _type))
            self.assertEqual(pn.number, addr)
            pn.deleteFromStore()

        assertNumberEquals(u'default', '555-1212')
        assertNumberEquals(u'business', '555-2323')

        self.assertEqual(self.store.count(PN), 0)
