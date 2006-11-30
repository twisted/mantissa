
import random, itertools

from twisted.trial import unittest

from axiom import store, userbase, item, attributes

from xmantissa import signup, offering, provisioning
from xmantissa.plugins import adminoff, free_signup
from xmantissa.product import Product, Installation



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
        self.ftp = Product(store=self.store, types=[])
        return self.sc.createSignup(
            u'testuser@localhost',
            itemClass,
            {'prefixURL': url},
            self.ftp,
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
        self.assertEquals(signup.usernameAvailable(u'fjones', u'localhost.localdomain'),
                          [True, u'Username already taken'])

        signup.createUser(
            firstName=u"Frank",
            lastName=u"Jones",
            username=u'fjones',
            domain=u'localhost.localdomain',
            password=u'asdf',
            emailAddress=u'fj@crappy.example.com')

        self.assertEquals(signup.usernameAvailable(u'fjones', u'localhost.localdomain'),
                          [False, u'Username already taken'])
        ss = self.ls.accountByAddress(u"fjones", u"localhost.localdomain").avatars.open()
        self.assertEquals(ss.query(Installation).count(), 1)


    def testUserInfoSignupValidation2(self):
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

