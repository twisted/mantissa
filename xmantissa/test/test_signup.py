
import random, itertools

from twisted.trial import unittest

from axiom import store, userbase, item, attributes

from xmantissa import signup, offering, provisioning
from xmantissa.plugins import adminoff, free_signup


class TestDependent(object):
    def __init__(self, name, dependencies):
        self.name = name
        self.deps = dependencies

    def dependencies(self):
        return iter(self.deps)

    def __repr__(self):
        return 'D<' + self.name + '>'

class DependencyOrderTestCase(unittest.TestCase):
    def testOrdering(self):
        a = TestDependent('a', [])
        b = TestDependent('b', [a])
        c = TestDependent('c', [a, b])
        d = TestDependent('d', [])
        e = TestDependent('e', [d, c])
        f = TestDependent('f', [c, d])
        g = TestDependent('g', [f])

        L = [a, b, c, d, e, f, g]

        for i in xrange(10):
            random.shuffle(L)
            inputList = L[:]
            order = signup.dependencyOrdered(L)
            for element in a, b, c, d, e, f, g:
                for dependency in element.deps:
                    self.failUnless(
                        order.index(element) > order.index(dependency),
                        "%r came before %r in %r (input was %r)" %
                        (element, dependency,
                         order, inputList))

class FakeTestBenefactor(item.Item):
    typeName = 'test_fake_test_benefactor'
    schemaVersion = 1

    endowed = attributes.integer(default=0)
    deprived = attributes.integer(default=0)
    counter = attributes.inmemory()

    def endow(self, ticket, avatar):
        self.endowed = self.counter()


    def deprive(self, ticket, avatar):
        self.deprived = self.counter()



class MultiBenefactorTestCase(unittest.TestCase):
    def setUp(self):
        self.s = store.Store()
        self.mb = signup.Multifactor(store=self.s)
        self.counter = itertools.count(1).next
        self.ftb = FakeTestBenefactor(store=self.s, counter=self.counter)
        self.ftb2 = FakeTestBenefactor(store=self.s, counter=self.counter)


    def testOrdering(self):
        self.mb.add(self.ftb)
        self.mb.add(self.ftb2)

        self.assertEquals(
            list(self.mb.benefactors('ascending')),
            [self.ftb, self.ftb2])

        self.assertEquals(
            list(self.mb.benefactors('descending')),
            [self.ftb2, self.ftb])


    def testAdding(self):
        self.mb.add(self.ftb)
        self.mb.add(self.ftb2)

        self.mb.endow(None, None) # Hopefully no one ever cares about the
                                  # ticket or the avatar here.
        self.assertEquals(self.ftb.endowed, 1)
        self.assertEquals(self.ftb2.endowed, 2)


    def testDeprivation(self):
        self.mb.add(self.ftb)
        self.mb.add(self.ftb2)

        self.mb.deprive(None, None) # Hopefully no one ever cares about the
                                    # ticket or the avatar here.
        self.assertEquals(self.ftb.deprived, 2)
        self.assertEquals(self.ftb2.deprived, 1)



class SignupCreationTestCase(unittest.TestCase):
    def setUp(self):
        self.dbdir = self.mktemp()
        self.store = store.Store(self.dbdir)
        self.ls = userbase.LoginSystem(store=self.store)
        self.admin = self.ls.addAccount(u'admin', u'localhost', None,
                                        internal=True, verified=True)
        self.substore = self.admin.avatars.open()
        self.sc = signup.SignupConfiguration(store=self.substore)

    def _installTestOffering(self):
        io = offering.InstalledOffering(
            store=self.store,
            offeringName=u"mantissa",
            application=None)

    def createFreeSignup(self, itemClass, url=u'signup', prompt=u'Sign Up!'):
        """

        A utility method to ensure that the same arguments are always used to
        create signup mechanisms, since these are the arguments that are going
        to be coming from the admin form.

        """
        self.ftb = FakeTestBenefactor(store=self.store,
                                      counter=itertools.count(1).next)
        return self.sc.createSignup(
            u'testuser@localhost',
            itemClass,
            {'prefixURL': url},
            {adminoff.adminOffering.benefactorFactories[0]: {},
             provisioning.BenefactorFactory(u'blah', u'blah',
                                            lambda **kw: self.ftb): {}},
            u'Blank Email Template', prompt)

    def testCreateFreeSignups(self):
        self._installTestOffering()

        for signupMechanismPlugin in [free_signup.freeTicket,
                                      free_signup.freeTicketPassword,
                                      free_signup.userInfo]:
            self.createFreeSignup(signupMechanismPlugin.itemClass)


    def test_usernameAvailability(self):
        """
        Test that the usernames which ought to be available are and that those
        which aren't are not:

        Only syntactically valid localparts are allowed.  Localparts which are
        already assigned are not allowed.

        Only domains which are actually served by this mantissa instance are
        allowed.
        """
        signup = self.createFreeSignup(free_signup.userInfo.itemClass)

        # Allowed: unused localpart, same domain as the administrator created
        # by setUp.
        self.failUnless(signup.usernameAvailable(u'alice', u'localhost')[0])

        # Not allowed: unused localpart, unknown domain.
        self.failIf(signup.usernameAvailable(u'alice', u'example.com')[0])

        # Not allowed: used localpart, same domain as the administrator created
        # by setUp.
        self.failIf(signup.usernameAvailable(u'admin', u'localhost')[0])



    def testUserInfoSignupCreation(self):
        signup = self.createFreeSignup(free_signup.userInfo.itemClass)
        self.assertEquals(signup.usernameAvailable(u'fjones', u'localhost'),
                          [True, u'Username already taken'])

        self.assertEquals(self.ftb.endowed, 0)

        signup.createUser(
            firstName=u"Frank",
            lastName=u"Jones",
            username=u'fjones',
            domain=u'localhost',
            password=u'asdf',
            emailAddress=u'fj@crappy.example.com')

        self.assertEquals(signup.usernameAvailable(u'fjones', u'localhost'),
                          [False, u'Username already taken'])

        self.assertEquals(self.ftb.endowed, 1)


    def testUserInfoSignupValidation(self):
        """
        Ensure that invalid characters aren't allowed in usernames, that
        usernames are parsable as the local part of an email address and that
        usernames shorter than two characters are invalid.
        """
        signup = self.createFreeSignup(free_signup.userInfo.itemClass)
        self.assertEquals(signup.usernameAvailable(u'foo bar', u'localhost'),
                          [False, u"Username contains invalid character: ' '"])
        self.assertEquals(signup.usernameAvailable(u'foo@bar', u'localhost'),
                          [False, u"Username contains invalid character: '@'"])
        # '~' is not expressly forbidden by the validator in usernameAvailable,
        # yet it is rejected by parseAddress (in xmantissa.smtp).
        self.assertEquals(signup.usernameAvailable(u'fo~o', u'127.0.0.1'),
                          [False, u"Username fails to parse"])
        self.assertEquals(signup.usernameAvailable(u'f', u'localhost'),
                          [False, u"Username too short"])


    def test_userInfoLoginMethods(self):
        """
        Check that C{createUser} creates only two L{LoginMethod}s on the
        account.
        """
        username, domain = u'fjones', u'divmod.com'
        signup = self.createFreeSignup(free_signup.userInfo.itemClass)
        signup.createUser(u'Frank', u'Jones', username, domain, u'asdf',
                          u'fj@example.com')
        account = self.ls.accountByAddress(username, domain)
        query = list(
            self.store.query(userbase.LoginMethod,
                             userbase.LoginMethod.account == account,
                             sort=userbase.LoginMethod.internal.ascending))
        self.assertEquals(len(query), 2)
        self.assertEquals(query[0].internal, False)
        self.assertEquals(query[0].verified, False)
        self.assertEquals(query[0].localpart, u'fj')
        self.assertEquals(query[0].domain, u'example.com')
        self.assertEquals(query[1].internal, True)
        self.assertEquals(query[1].verified, True)
        self.assertEquals(query[1].localpart, username)
        self.assertEquals(query[1].domain, domain)


    def test_freeSignupsList(self):
        """
        Test that if we produce 3 different publicly accessible signups, we get
        information about all of them back.
        """
        for i, signupMechanismPlugin in enumerate(
            [free_signup.freeTicket,
             free_signup.freeTicketPassword,
             free_signup.userInfo]):
            self.createFreeSignup(signupMechanismPlugin.itemClass,
                                  url=u'signup%d' % (i+1,),
                                  prompt=u"Sign Up %d" % (i+1,))
        x = list(signup._getPublicSignupInfo(self.store))
        x.sort()
        self.assertEquals(x, [(u'Sign Up 1', u'/signup1'),
                              (u'Sign Up 2', u'/signup2'),
                              (u'Sign Up 3', u'/signup3')])
