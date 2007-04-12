from zope.interface import Interface, implements

from twisted.trial import unittest
from twisted.python.reflect import qual

from axiom import store, userbase, item, attributes
from axiom.dependency import dependsOn

from xmantissa import signup, offering, ixmantissa, people
from xmantissa.plugins import free_signup
from xmantissa.product import Product, Installation


class _SignupTestMixin:
    def setUp(self):
        self.dbdir = self.mktemp()
        self.store = store.Store(self.dbdir)
        self.ls = userbase.LoginSystem(store=self.store)
        self.admin = self.ls.addAccount(u'admin', u'localhost', None,
                                        internal=True, verified=True)
        self.substore = self.admin.avatars.open()
        self.sc = signup.SignupConfiguration(store=self.substore)


    def createFreeSignup(self, itemClass, url=u'signup', prompt=u'Sign Up!', types=None):
        """

        A utility method to ensure that the same arguments are always used to
        create signup mechanisms, since these are the arguments that are going
        to be coming from the admin form.

        """
        if types is None:
            types = []
        self.ftp = Product(store=self.store, types=types)
        return self.sc.createSignup(
            u'testuser@localhost',
            itemClass,
            {'prefixURL': url},
            self.ftp,
            u'Blank Email Template', prompt)


    def _installTestOffering(self):
        io = offering.InstalledOffering(
            store=self.store,
            offeringName=u"mantissa",
            application=None)



class SignupCreationTestCase(_SignupTestMixin, unittest.TestCase):
    def test_createFreeSignups(self):
        self._installTestOffering()

        self.createFreeSignup(free_signup.freeTicket.itemClass)
        self.createFreeSignup(
            free_signup.userInfo.itemClass, types=[qual(people.Organizer)])


    def test_usernameAvailability(self):
        """
        Test that the usernames which ought to be available are and that those
        which aren't are not:

        Only syntactically valid localparts are allowed.  Localparts which are
        already assigned are not allowed.

        Only domains which are actually served by this mantissa instance are
        allowed.
        """

        signup = self.createFreeSignup(
            free_signup.userInfo.itemClass, types=[qual(people.Organizer)])
        # Allowed: unused localpart, same domain as the administrator created
        # by setUp.
        self.failUnless(signup.usernameAvailable(u'alice', u'localhost')[0])

        # Not allowed: unused localpart, unknown domain.
        self.failIf(signup.usernameAvailable(u'alice', u'example.com')[0])

        # Not allowed: used localpart, same domain as the administrator created
        # by setUp.
        self.failIf(signup.usernameAvailable(u'admin', u'localhost')[0])
        self.assertEquals(signup.usernameAvailable(u'fjones', u'localhost'),
                          [True, u'Username already taken'])

        signup.createUser(
            firstName=u"Frank",
            lastName=u"Jones",
            username=u'fjones',
            domain=u'localhost',
            password=u'asdf',
            emailAddress=u'fj@crappy.example.com')

        self.assertEquals(signup.usernameAvailable(u'fjones', u'localhost'),
                          [False, u'Username already taken'])
        ss = self.ls.accountByAddress(u"fjones", u"localhost").avatars.open()
        self.assertEquals(ss.query(Installation).count(), 1)


    def test_userInfoSignupValidation2(self):
        """
        Ensure that invalid characters aren't allowed in usernames, that
        usernames are parsable as the local part of an email address and that
        usernames shorter than two characters are invalid.
        """
        signup = self.createFreeSignup(
            free_signup.userInfo.itemClass, types=[qual(people.Organizer)])
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
        signup = self.createFreeSignup(
            free_signup.userInfo.itemClass, types=[qual(people.Organizer)])
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
             free_signup.userInfo]):
            self.createFreeSignup(signupMechanismPlugin.itemClass,
                                  url=u'signup%d' % (i+1,),
                                  prompt=u"Sign Up %d" % (i+1,),
                                  types=[qual(people.Organizer)])
        x = list(signup._getPublicSignupInfo(self.store))
        x.sort()
        self.assertEquals(x, [(u'Sign Up 1', u'/signup1'),
                              (u'Sign Up 2', u'/signup2')])


class IFoo(Interface):
    """
    Dummy interface.
    """


class IBar(Interface):
    """
    Dummy interface.
    """


class IBaz(Interface):
    """
    Dummy interface.
    """


class BoringSignupMechanism(item.Item):
    """
    A trivial signup mechanism which depends on L{IBaz}.
    """
    implements(ixmantissa.ISignupMechanism)

    requiredPowerups = (IBaz,)
    powerupInterfaces = (ixmantissa.ISignupMechanism,)

    name = u'Boring'
    description = u'Boring'
    configuration = {}
    product = attributes.reference()
    prompt = attributes.text()
    prefixURL = attributes.text()
    booth = attributes.reference()
    emailTemplate = attributes.text()



class BazProvider(item.Item):
    """
    Trivial item which is a L{IBaz} powerup.
    """
    powerupInterfaces = (IBaz,)
    attr = attributes.integer()



class BarProvider(item.Item):
    """
    Trivial item which is a L{IBar} powerup, and depends on L{BazProvider}.
    """
    powerupInterfaces = (IBar,)
    baz = dependsOn(BazProvider)



class FooProvider(item.Item):
    """
    Trivial item which is a L{IFoo} powerup, and depends on L{BarProvider}.
    """
    powerupInterfaces = (IFoo,)
    bar = dependsOn(BarProvider)



class SignupProductDependencyTestCase(_SignupTestMixin, unittest.TestCase):
    """
    Tests for the functionality of L{signup.SignupConfiguration} which deals
    with L{xmantissa.ixmantissa.ISignupMechanism} that require their products
    to contain a particular set of powerups.
    """
    def _makeProduct(self, types):
        return Product(store=self.store, types=map(qual, types))


    def test_signupDependenciesMetDirectly(self):
        """
        Test that L{signup.SignupConfiguration.signupDependenciesMet} is
        satisfied when the product directly includes something which provides
        L{IFoo}.
        """
        self.failUnless(
            self.sc.signupDependenciesMet(
                BoringSignupMechanism,
                self._makeProduct([BazProvider])))


    def test_signupDependenciesMet(self):
        """
        Test that L{signup.SignupConfiguration.signupDependenciesMet} is
        satisfied when the product includes something which provides L{IFoo}.
        """
        self.failUnless(
            self.sc.signupDependenciesMet(
                BoringSignupMechanism,
                self._makeProduct([FooProvider])))


    def test_signupDependenciesMetEmpty(self):
        """
        Test that L{signup.SignupConfiguration.signupDependenciesMet} isn't
        satisfied when the product is empty.
        """
        self.failIf(
            self.sc.signupDependenciesMet(
                BoringSignupMechanism,
                self._makeProduct([])))


    def test_createSignupUnsatisfiedDeps(self):
        """
        Test that L{signup.SignupConfiguration.createSignup} throws a
        L{signup.IncompatibleProduct} when there are unsatisfied dependencies.
        """
        self.assertRaises(
            signup.IncompatibleProduct,
            lambda: self.createFreeSignup(BoringSignupMechanism))


    def test_createSignup(self):
        """
        Test L{signup.SignupConfiguration.createSignup}.
        """
        self.failUnless(
            isinstance(
                self.createFreeSignup(
                    BoringSignupMechanism,
                    types=[qual(FooProvider)]),
                BoringSignupMechanism))


    def test_userInfoSignup(self):
        """
        Test that L{signup.UserInfoSignup} correctly calls C{addRealName} on
        the I{me} person.
        """
        uiSignup = self.createFreeSignup(
            signup.UserInfoSignup, types=[qual(people.Organizer)])
        uiSignup.createUser(
            u'Foo', u'Bar', u'foobar', u'host', u'', u'foo@bar.com')
        ss = self.ls.accountByAddress(u'foobar', u'host').avatars.open()
        organizer = ixmantissa.IOrganizer(ss)
        self.assertEquals(
            organizer.ownerPerson.getEmailAddress(), 'foo@bar.com')
        self.assertEquals(
            organizer.ownerPerson.getDisplayName(), 'Foo Bar')
