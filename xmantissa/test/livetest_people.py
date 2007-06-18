import sys

from nevow import tags
from nevow.livetrial.testcase import TestCase

from axiom.store import Store
from axiom.dependency import installOn

from xmantissa import people, ixmantissa
from xmantissa.liveform import FORM_INPUT
from xmantissa.webtheme import getLoader
from xmantissa.webapp import PrivateApplication

class AddPersonTestBase(people.AddPersonFragment):
    jsClass = None

    def __init__(self):
        self.store = Store()
        organizer = people.Organizer(store=self.store)
        installOn(organizer, self.store)
        people.AddPersonFragment.__init__(self, organizer)


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

        # XXX This is a pretty terrible hack.  The client-side of these tests
        # just submit the form.  In order for the assertions to succeed, that
        # means the form needs to be rendered with some values in it already.
        # There's no actual API for putting values into the form here, though.
        # So instead, we'll grovel over all the parameters and try to change
        # them to reflect what we want.  Since this relies on there being no
        # conflictingly named parameters anywhere in the form and since it
        # relies on the parameters being traversable in order to find them all,
        # this is rather fragile.  The tests should most likely just put values
        # in on the client or something along those lines (it's not really
        # clear what the intent of these tests are, anyway, so it's not clear
        # what alternate approach would satisfy that intent).
        params = []
        remaining = liveform.parameters[:]
        while remaining:
            p = remaining.pop()
            if p.type == FORM_INPUT:
                remaining.extend(p.coercer.parameters)
            else:
                params.append((p.name, p))
        self.mangleDefaults(dict(params))
        return liveform



class OnlyNick(AddPersonTestBase, TestCase):
    jsClass = u'Mantissa.Test.OnlyNick'

    def mangleDefaults(self, params):
        params['nickname'].default = u'everybody'


    def checkResult(self):
        self.assertEqual(self.exc_info, None)

        p = self.store.findUnique(people.Person)
        self.assertEqual(p.name, 'everybody')
        self.assertIdentical(p.organizer, self.organizer)
        p.deleteFromStore()

        self.assertEqual(self.store.count(people.EmailAddress), 0)
        self.assertEqual(self.store.count(people.RealName), 0)



class NickNameAndEmailAddress(AddPersonTestBase, TestCase):
    jsClass = u'Mantissa.Test.NickNameAndEmailAddress'

    def mangleDefaults(self, params):
        params['nickname'].default = u'NICK!!!'
        params['email'].default = u'a@b.c'


    def checkResult(self):
        self.assertEqual(self.exc_info, None)

        p = self.store.findUnique(people.Person)
        self.assertEqual(p.name, 'NICK!!!')
        self.assertIdentical(p.organizer, self.organizer)

        e = self.store.findUnique(people.EmailAddress)
        self.assertEqual(e.address, 'a@b.c')
        self.assertEqual(e.person, p)

        e.deleteFromStore()
        p.deleteFromStore()

        self.assertEqual(self.store.count(people.RealName), 0)



class ContactInfoTestCase(TestCase):
    jsClass = u'Mantissa.Test.ContactInfo'

    def getWidgetDocument(self):
        s = Store()

        installOn(PrivateApplication(store=s), s)

        o = people.Organizer(store=s)
        installOn(o, s)

        p = people.Person(store=s,
                          name=u'The Foo Person',
                          organizer=o)

        people.EmailAddress(store=s, person=p, address=u'foo@skynet')
        people.PhoneNumber(store=s, person=p, number=u'434-5030')

        f = ixmantissa.INavigableFragment(p)
        f.docFactory = getLoader(f.fragmentName)
        f.setFragmentParent(self)
        return f
