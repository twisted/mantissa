"""
Tests for L{xmantissa.websharing}
"""
from twisted.trial.unittest import TestCase

from nevow import inevow

from axiom.userbase import LoginMethod, LoginSystem
from axiom.store import Store
from axiom.dependency import installOn
from axiom.plugins.mantissacmd import Mantissa

from xmantissa import websharing, sharing, signup, offering, product

class WebSharingTestCase(TestCase):
    """
    Tests for L{xmantissa.websharing}
    """
    def test_linkTo(self):
        """
        Test that L{xmantissa.websharing.linkTo} generates a URL using the
        localpart of the account's internal L{axiom.userbase.LoginMethod}
        """
        s = Store(self.mktemp())
        ls = LoginSystem(store=s)
        installOn(ls, s)

        acct = ls.addAccount(
            u'right', u'host', u'', verified=True, internal=True)
        acct.addLoginMethod(
            u'wrong', u'host', internal=False, verified=False)

        share = sharing.shareItem(ls, shareID=u'loginsystem')
        self.assertEquals(
            websharing.linkTo(share, s),
            '/by/right/loginsystem')



class _UserIdentificationMixin:
    def setUp(self):
        self.siteStore = Store(self.mktemp())
        Mantissa().installSite(self.siteStore, '/')
        Mantissa().installAdmin(self.siteStore, 'admin@localhost', '')
        for off in offering.getOfferings():
            if off.name == 'mantissa':
                offering.installOffering(self.siteStore, off, {})
                break
        self.loginSystem = self.siteStore.findUnique(LoginSystem)
        self.adminStore = self.loginSystem.accountByAddress(
            u'admin', u'localhost').avatars.open()
        sc = self.adminStore.findUnique(signup.SignupConfiguration)
        self.signup = sc.createSignup(
            u'testuser@localhost',
            signup.UserInfoSignup,
            {'prefixURL': u''},
            product.Product(store=self.siteStore, types=[]),
            u'', u'')



class UserIdentificationTestCase(_UserIdentificationMixin, TestCase):
    """
    Tests for L{xmantissa.websharing._storeFromUsername}
    """
    def test_sameLocalpartAndUsername(self):
        """
        Test that L{xmantissa.websharing._storeFromUsername} doesn't get
        confused when the username it is passed is the same as the localpart
        of that user's email address
        """
        self.signup.createUser(
            u'', u'', u'username', u'localhost', u'', u'username@internet')
        self.assertIdentical(
            websharing._storeFromUsername(self.siteStore, u'username'),
            self.loginSystem.accountByAddress(
                u'username', u'localhost').avatars.open())


    def test_usernameMatchesOtherLocalpart(self):
        """
        Test that L{xmantissa.websharing._storeFromUsername} doesn't get
        confused when the username it is passed matches the localpart of
        another user's email address
        """
        self.signup.createUser(
            u'', u'', u'username', u'localhost', u'', u'notusername@internet')
        self.signup.createUser(
            u'', u'', u'notusername', u'localhost', u'', u'username@internet')
        self.assertIdentical(
            websharing._storeFromUsername(self.siteStore, u'username'),
            self.loginSystem.accountByAddress(
                u'username', u'localhost').avatars.open())


class UserIndexPageTestCase(_UserIdentificationMixin, TestCase):
    """
    Tests for L[xmantissa.websharing.UserIndexPage}
    """
    def test_locateChild(self):
        """
        Test that L{xmantissa.websharing.UserIndexPage.locateChild} returns a
        renderable resource and the remaining segments if the first segment
        matches a username
        """
        self.signup.createUser(
            u'', u'', u'username', u'localhost', u'', u'username@internet')
        index = websharing.UserIndexPage(self.loginSystem)
        (renderable, segments) = index.locateChild(
            None, ('username', 'x', 'y', 'z'))
        self.assertNotIdentical(inevow.IResource(renderable, None), None)
        self.assertEquals(segments, ('x', 'y', 'z'))
