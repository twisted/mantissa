import sys

from nevow import loaders, tags
from nevow.livetrial.testcase import TestCase

from axiom.store import Store

from xmantissa import people, ixmantissa
from xmantissa.webtheme import getLoader
from xmantissa.webapp import PrivateApplication

class AddPersonTestBase(people.AddPersonFragment):
    jsClass = None

    def __init__(self):
        self.store = Store()
        self.original  = people.AddPerson(store=self.store)
        self.organizer = people.Organizer(store=self.store)

        super(AddPersonTestBase, self).__init__()


    def getWidgetDocument(self):
        return tags.invisible(render=tags.directive('addPersonForm'))


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
    jsClass = u'Mantissa.Test.NoNickOrFirstLastNames'

    def checkResult(self):
        self.assertEqual(self.exc_info[0], ValueError)
        for cls in (people.Person, people.EmailAddress):
            self.assertEqual(self.store.count(cls), 0)



class NoNickButFirstLastNames(AddPersonTestBase, TestCase):
    jsClass = u'Mantissa.Test.NoNickButFirstLastNames'

    def mangleDefaults(self, params):
        params['firstname'].default = u'FIRSTNAME'
        params['lastname'].default = u'LASTNAME'


    def checkResult(self):
        self.assertEqual(self.exc_info, None)

        p = self.store.findUnique(people.Person)
        self.assertEqual(p.name, '')
        self.assertEqual(p.organizer, self.organizer)

        rn = self.store.findUnique(people.RealName)
        self.assertEqual(rn.first, 'FIRSTNAME')
        self.assertEqual(rn.last, 'LASTNAME')
        self.assertEqual(rn.person, p)

        rn.deleteFromStore()
        p.deleteFromStore()

        self.assertEqual(self.store.count(people.EmailAddress), 0)



class OnlyNick(AddPersonTestBase, TestCase):
    jsClass = u'Mantissa.Test.OnlyNick'

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
    jsClass = u'Mantissa.Test.OnlyEmailAddress'

    def mangleDefaults(self, params):
        params['email'].default = u'bob@the.internet'


    def checkResult(self):
        self.assertEqual(self.exc_info[0], ValueError)

        for cls in (people.Person, people.RealName, people.EmailAddress):
            self.assertEqual(self.store.count(cls), 0)



class NickNameAndEmailAddress(AddPersonTestBase, TestCase):
    jsClass = u'Mantissa.Test.NickNameAndEmailAddress'

    def mangleDefaults(self, params):
        params['nickname'].default = u'NICK!!!'
        params['email'].default = u'a@b.c'


    def checkResult(self):
        self.assertEqual(self.exc_info, None)

        p = self.store.findUnique(people.Person)
        self.assertEqual(p.name, 'NICK!!!')
        self.assertEqual(p.organizer, self.organizer)

        e = self.store.findUnique(people.EmailAddress)
        self.assertEqual(e.address, 'a@b.c')
        self.assertEqual(e.person, p)

        e.deleteFromStore()
        p.deleteFromStore()

        self.assertEqual(self.store.count(people.RealName), 0)



class PersonDetailTestCase(TestCase):
    jsClass = u'Mantissa.Test.PersonDetail'

    def getWidgetDocument(self):
        s = Store()

        PrivateApplication(store=s).installOn(s)

        o = people.Organizer(store=s)
        o.installOn(s)

        p = people.Person(store=s,
                          name=u'The Foo Person',
                          organizer=o)

        people.EmailAddress(store=s, person=p, address=u'foo@skynet')
        people.PhoneNumber(store=s, person=p, number=u'434-5030')

        f = ixmantissa.INavigableFragment(p)
        f.docFactory = getLoader(f.fragmentName)
        f.setFragmentParent(self)
        return f
