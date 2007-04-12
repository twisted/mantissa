"""
Tests for L{xmantissa.websharing} and L{xmantissa.publicweb}.
"""
from zope.interface import Interface, Attribute, implements

from twisted.python.components import registerAdapter

from twisted.trial.unittest import TestCase

from nevow import inevow
from nevow.athena import LiveElement
from nevow.testutil import FakeRequest

from axiom.item import Item
from axiom.attributes import integer
from axiom.store import Store
from axiom.userbase import LoginSystem
from axiom.dependency import installOn
from axiom.plugins.mantissacmd import Mantissa

from xmantissa import (websharing, sharing, signup, offering, product,
                       ixmantissa, website)

class WebSharingTestCase(TestCase):
    """
    Tests for L{xmantissa.websharing.linkTo}
    """
    def setUp(self):
        """
        Set up some state.
        """
        self.s = Store(self.mktemp())
        self.ls = LoginSystem(store=self.s)
        installOn(self.ls, self.s)
        acct = self.ls.addAccount(
            u'right', u'host', u'', verified=True, internal=True)
        acct.addLoginMethod(
            u'wrong', u'host', internal=False, verified=False)
        self.share = sharing.shareItem(self.ls, shareID=u'loginsystem')


    def test_linkToShare(self):
        """
        Test that L{xmantissa.websharing.linkTo} generates a URL using the
        localpart of the account's internal L{axiom.userbase.LoginMethod}
        """
        self._verifyPath(websharing.linkTo(self.share))


    def _verifyPath(self, linkPath):
        """
        Verify that the given path matches the test's expectations.
        """
        self.failUnless(isinstance(linkPath, str),
                        "linkTo should return a str, not %r" %
                        (type(linkPath)))
        self.assertEquals(linkPath, '/users/right/loginsystem')


    def test_linkToProxy(self):
        """
        Test that L{xmantissa.websharing.linkTo} generates an URL that I can
        link to.
        """
        self._verifyPath(
            websharing.linkTo(sharing.getShare(self.s, sharing.getEveryoneRole(
                        self.s), u'loginsystem')))



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


class IShareable(Interface):
    """
    Dummy interface for Shareable.
    """
    magicValue = Attribute(
        """
        A magical value.
        """)


class Shareable(Item):
    """
    This is a dummy class that may be shared.
    """
    implements(IShareable)

    magicValue = integer()



class ShareableView(LiveElement):
    """
    Nothing to see here, move along.
    """
    implements(ixmantissa.INavigableFragment,
               ixmantissa.ICustomizable)

    def __init__(self, shareable):
        """
        adapt a shareable to INavigableFragment
        """
        super(ShareableView, self).__init__()
        self.shareable = shareable

    def showMagicValue(self):
        """
        retrieve the magic value from my model
        """
        return self.shareable.magicValue


    # XXX: Everything below in this class should not be required.  It's here to
    # satisfy implicit requirements in SharingIndex.locateChild, but there
    # should be test coverage ensuring that it is not required and that
    # customizeFor is only invoked if you provide the ICustomizable interface.

    def customizeFor(self, user):
        """
        customize me by returning myself
        """
        return self

    fragmentName = None


registerAdapter(ShareableView, IShareable,
                ixmantissa.INavigableFragment)


class UserIndexPageTestCase(_UserIdentificationMixin, TestCase):
    """
    Tests for L[xmantissa.websharing.UserIndexPage}
    """
    def setUp(self):
        """
        Create an additional user for UserIndexPage, and share a single item with a
        shareID of the empty string.
        """
        _UserIdentificationMixin.setUp(self)
        self.magicValue = 123412341234
        newUser = self.signup.createUser(
            u'', u'', u'username', u'localhost', u'',
            u'username@internet')
        self.userStore = websharing._storeFromUsername(
            self.siteStore, u'username')
        self.shareable = Shareable(store=self.userStore,
                                   magicValue=self.magicValue)
        self.share = sharing.shareItem(self.shareable, shareID=u'')
        self.website = website.WebSite(store=self.siteStore)


    def test_locateChild(self):
        """
        Test that L{xmantissa.websharing.UserIndexPage.locateChild} returns a
        renderable resource and the remaining segments if the first segment
        matches a username
        """
        index = websharing.UserIndexPage(self.loginSystem)
        (renderable, segments) = index.locateChild(
            None, ('username', 'x', 'y', 'z'))
        self.assertNotIdentical(inevow.IResource(renderable, None), None)
        self.assertEquals(segments, ('x', 'y', 'z'))


    def test_userURL(self):
        """
        Verify that the /users/username URL will return the root page for the user
        specified.
        """
        self._verifySegmentsMatch(('users', 'username', ''))


    def _verifySegmentsMatch(self, segments):
        """
        Verify that the given tuple of segments can be used to retrieve a public
        view for this test's share.
        """
        resource = self.website
        request = FakeRequest()
        while segments:
            resource, segments = resource.locateChild(request, segments)
        self.assertEquals(resource.fragment.showMagicValue(), self.magicValue)


    def test_linkToMatchesUserURL(self):
        """
        Test that L{xmantissa.websharing.linkTo} generates a URL using the
        localpart of the account's internal L{axiom.userbase.LoginMethod}
        """
        pathString = websharing.linkTo(self.share)
        self.assertEquals(pathString[0], "/") # sanity check
        segments = tuple(pathString[1:].split("/"))
        self._verifySegmentsMatch(segments)
