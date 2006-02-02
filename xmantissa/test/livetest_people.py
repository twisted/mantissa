from nevow import loaders, tags
from nevow.livetrial.testcase import TestCase

from axiom.store import Store
from axiom import attributes

from xmantissa import people

class ContactInfoTestBase(people.ContactInfoFragment):
    jsClass = u'Mantissa.Test.People'

    def __init__(self):
        self.store = Store()
        super(ContactInfoTestBase, self).__init__(self.makePerson())

        self.docFactory = loaders.stan(
            tags.div(_class='test-unrun',
                    render=tags.directive('liveFragment'))[
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
                            default=False)
        return self.person

    def mangleDefaults(self, params):
        params['defaultEmail'].default = u'bob.default@divmod.com'
        otherEmailParam = params['otherEmails']

        for i in xrange(otherEmailParam.count):
            if len(otherEmailParam.defaults[i]) == 0:
                otherEmailParam.defaults[i] = u'bob%s@divmod.com' % (i,)
        self.expectedAddresses = otherEmailParam.defaults

    def checkResult(self):
        default = self.store.findUnique(people.EmailAddress,
                                attributes.AND(people.EmailAddress.person == self.person,
                                               people.EmailAddress.default == True))

        self.assertEqual(default.address, 'bob.default@divmod.com')

        others = self.store.query(people.EmailAddress,
                            attributes.AND(people.EmailAddress.person == self.person,
                                           people.EmailAddress.default == False)).getColumn('address')

        self.assertEqual(sorted(others), sorted(self.expectedAddresses))

class EditRealName(ContactInfoTestBase, TestCase):

    def mangleDefaults(self, params):
        params['firstname'].default = u'Bob'
        params['lastname'].default = u'The Slob'

    def checkResult(self):
        rn = self.store.findUnique(people.RealName,
                                   people.RealName.person == self.person)

        self.assertEqual(rn.first + ' ' + rn.last, 'Bob The Slob')

class EditNickname(ContactInfoTestBase, TestCase):

    def mangleDefaults(self, params):
        params['nickname'].default = u'Bobby'

    def checkResult(self):
        self.assertEqual(self.person.name, 'Bobby')


class EditPhoneNumber(ContactInfoTestBase, TestCase):

    def mangleDefaults(self, params):
        params['defaultPhone'].default = u'555-1212'
        params['otherPhones'].defaults[:2] = (u'555-2323', '555-6767')


    def checkResult(self):
        default = self.store.findUnique(people.PhoneNumber,
                                attributes.AND(people.PhoneNumber.person == self.person,
                                               people.PhoneNumber.default == True))

        self.assertEqual(default.number, '555-1212')

        others = self.store.query(people.PhoneNumber,
                            attributes.AND(people.PhoneNumber.person == self.person,
                                           people.PhoneNumber.default == False)).getColumn('number')

        self.assertEqual(sorted(others), ['555-2323', '555-6767'])
