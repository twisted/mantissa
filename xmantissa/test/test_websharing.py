"""
Tests for L{xmantissa.websharing} and L{xmantissa.publicweb}.
"""
from zope.interface import Interface, Attribute, implements

from twisted.python.components import registerAdapter

from twisted.trial.unittest import TestCase

from nevow import inevow, rend
from nevow.athena import LiveElement
from nevow.testutil import FakeRequest

from axiom.item import Item
from axiom.attributes import integer, text
from axiom.store import Store
from axiom.userbase import LoginSystem
from axiom.dependency import installOn
from axiom.plugins.mantissacmd import Mantissa

from xmantissa import (websharing, sharing, signup, offering, product,
                       ixmantissa, website)



class _TemplateNameResolver(Item):
    """
    An L{ixmantissa.ITemplateNameResolver} with an implementation of
    L{getDocFactory} which doesn't require the presence any disk templates.
    """
    powerupInterfaces = (ixmantissa.ITemplateNameResolver,)

    magicTemplateName = text(doc="""
    L{magicDocFactoryValue} will be returned by L{getDocFactory} if it is passed
    this string as the first argument.""")

    magicDocFactoryValue = text(doc="""
    The string value to be returned from L{getDocFactory} when the name it is
    passed matches L{magicTemplateName}."""
    # if anything starts to care too much about what the docFactory is, we
    # won't be able to get away with just using a string.
    )

    # ITemplateNameResolver
    def getDocFactory(self, name, default=None):
        """
        If C{name} matches L{self.magicTemplateName}, return
        L{self.magicTemplateName}, otherwise return C{default}.
        """
        if name == self.magicTemplateName:
            return self.magicDocFactoryValue
        return default



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


    fragmentName = Attribute(
        """
        The value that the corresponing L{ShareableView} should use for its
        C{fragmentName} attribute.
        """)



class Shareable(Item):
    """
    This is a dummy class that may be shared.
    """
    implements(IShareable)

    magicValue = integer()
    fragmentName = text()



class ShareableView(LiveElement):
    """
    Nothing to see here, move along.

    @ivar customizedFor: The username we were customized for, or C{None}.
    """
    implements(ixmantissa.INavigableFragment,
               ixmantissa.ICustomizable)

    customizedFor = None

    def __init__(self, shareable):
        """
        adapt a shareable to INavigableFragment
        """
        super(ShareableView, self).__init__()
        self.shareable = shareable
        self.fragmentName = self.shareable.fragmentName


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
        Customize me by returning myself, and storing the username we were
        customized for as L{self.customizedFor}.
        """
        self.customizedFor = user
        return self



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
        self.share = sharing.shareItem(
            self.shareable, shareID=u'ashare')
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
        websharing.addDefaultShareID(self.userStore, u'ashare', 0)
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
        websharing.addDefaultShareID(self.userStore, u'ashare', 0)
        pathString = websharing.linkTo(self.share)
        self.assertEquals(pathString[0], "/") # sanity check
        segments = tuple(pathString[1:].split("/"))
        self._verifySegmentsMatch(segments)


    def test_emptySegmentNoDefault(self):
        """
        Verify that we get L{rend.NotFound} from
        L{websharing.SharingIndex.locateChild} if there is no default share ID
        and we access the empty child.
        """
        sharingIndex = websharing.SharingIndex(self.userStore)
        result = sharingIndex.locateChild(None, ('',))
        self.assertIdentical(result, rend.NotFound)


    def test_emptySegmentWithDefault(self):
        """
        Verify that we get the right resource and segments from
        L{websharing.SharingIndex.locateChild} if there is a default share ID
        and we access the empty child.
        """
        websharing.addDefaultShareID(self.userStore, u'ashare', 0)
        sharingIndex = websharing.SharingIndex(self.userStore)
        SEGMENTS = ('', 'foo', 'bar')
        (res, segments) = sharingIndex.locateChild(None, SEGMENTS)
        self.assertEqual(
            res.fragment.showMagicValue(), self.magicValue)
        self.assertEqual(segments, SEGMENTS[1:])


    def test_invalidShareIDNoDefault(self):
        """
        Verify that we get L{rend.NotFound} from
        L{websharing.SharingIndex.locateChild} if there is no default share ID
        and we access an invalid segment.
        """
        sharingIndex = websharing.SharingIndex(self.userStore)
        result = sharingIndex.locateChild(None, ('foo',))
        self.assertIdentical(result, rend.NotFound)


    def test_validShareID(self):
        """
        Verify that we get the right resource and segments from
        L{websharing.SharingIndex.locateChild} if we access a valid share ID.
        """
        websharing.addDefaultShareID(self.userStore, u'', 0)

        otherShareable = Shareable(store=self.userStore,
                                   magicValue=self.magicValue + 3)
        otherShare = sharing.shareItem(otherShareable, shareID=u'foo')

        sharingIndex = websharing.SharingIndex(self.userStore)
        SEGMENTS = ('foo', 'bar')
        (res, segments) = sharingIndex.locateChild(None, SEGMENTS)
        self.assertEqual(
            res.fragment.showMagicValue(), self.magicValue + 3)
        self.assertEqual(segments, SEGMENTS[1:])


    def test_shareFragmentType(self):
        """
        Verify that the wrapped fragment returned from
        L{websharing.SharingIndex._makeShareResource} is of the same type as
        the L{ixmantissa.INavigableFragment} adapter for the share it is
        passed.
        """
        sharingIndex = websharing.SharingIndex(self.userStore)
        res = sharingIndex._makeShareResource(self.shareable)
        self.failUnless(isinstance(res.fragment, ShareableView))


    def test_customizedShareFragment(self):
        """
        Verify that the wrapped fragment returned from
        L{websharing.SharingIndex._makeShareResource} has been customized for
        the avatar name the sharing index was passed.
        """
        sharingIndex = websharing.SharingIndex(self.userStore, u'bill@net')
        res = sharingIndex._makeShareResource(self.shareable)
        self.assertEqual(res.fragment.customizedFor, u'bill@net')


    def test_shareResourceStore(self):
        """
        Verify that the resource returned from
        L{websharing.SharingIndex._makeShareResource} is passed the site
        store.
        """
        sharingIndex = websharing.SharingIndex(self.userStore)
        res = sharingIndex._makeShareResource(self.shareable)
        self.assertIdentical(res.store, self.siteStore)


    def test_shareResourceUsername(self):
        """
        Verify that the resource returned from
        L{websharing.SharingIndex._makeShareResource} is passed the same
        username that was passed to the L{websharing.SharingIndex}
        constructor.
        """
        sharingIndex = websharing.SharingIndex(self.userStore, u'bill@net')
        res = sharingIndex._makeShareResource(self.shareable)
        self.assertEqual(res.username, u'bill@net')


    def test_shareResourceNoUsername(self):
        """
        Verify that the resource returned from
        L{websharing.SharingIndex._makeShareResource} is passed C{None} when
        C{None} was the username passed to the L{websharing.SharingIndex}
        constructor.
        """
        sharingIndex = websharing.SharingIndex(self.userStore, None)
        res = sharingIndex._makeShareResource(self.shareable)
        self.assertIdentical(res.username, None)


    def test_shareFragmentDocFactory(self):
        """
        Verify that L{websharing.SharingIndex._makeShareResource} calls
        L{ITemplateNameResolver.getDocFactory} with the C{fragmentName}
        attribute of the share's fragment and assigns the result to the
        C{docFactory} attribute.

        XXX: PrivateApplication is not an ITemplateNameResolver, but is an
        IWebTranslator, and it implements getDocFactory.  Because of that, we
        will get looked up under IWebTranslator, which is why we power it up.
        This is a bug.
        """
        MAGIC_TEMPLATE_NAME = u'magic-template'
        MAGIC_DOC_FACTORY = u'magic-doc-factory'
        tnr = _TemplateNameResolver(
            store=self.userStore,
            magicTemplateName=MAGIC_TEMPLATE_NAME,
            magicDocFactoryValue=MAGIC_DOC_FACTORY)
        installOn(tnr, self.userStore)
        self.userStore.powerUp(tnr, ixmantissa.IWebTranslator)

        self.shareable.fragmentName = MAGIC_TEMPLATE_NAME
        sharingIndex = websharing.SharingIndex(self.userStore, None)
        res = sharingIndex._makeShareResource(self.shareable)
        self.assertEqual(res.fragment.docFactory, MAGIC_DOC_FACTORY)


    def test_shareFragmentNoDocFactory(self):
        """
        Verify that L{websharing.SharingIndex._makeShareResource} does not set
        a C{docFactory} attribute on the share's fragment if the
        C{fragmentName} attribute is None
        """
        sharingIndex = websharing.SharingIndex(self.userStore, None)
        res = sharingIndex._makeShareResource(self.shareable)
        self.assertIdentical(res.fragment.docFactory, None)




class DefaultShareIDTestCase(TestCase):
    """
    Tests for L{websharing.addDefaultShareID} and L{websharing.getDefaultShareID}.
    """
    def test_createsItem(self):
        """
        Verify that L{websharing.addDefaultShareID} creates a
        L{websharing._DefaultShareID} item.
        """
        store = Store()
        websharing.addDefaultShareID(store, u'share id', -22)
        item = store.findUnique(websharing._DefaultShareID)
        self.assertEqual(item.shareID, u'share id')
        self.assertEqual(item.priority, -22)


    def test_findShareID(self):
        """
        Verify that L{websharing.getDefaultShareID} reads the share ID set by a
        L{websharing.addDefaultShareID} call.
        """
        store = Store()
        websharing.addDefaultShareID(store, u'share id', 0)
        self.assertEqual(websharing.getDefaultShareID(store), u'share id')


    def test_findHighestPriorityShareID(self):
        """
        Verify that L{websharing.getDefaultShareID} reads the highest-priority
        share ID set by L{websharing.addDefaultShareID}.
        """
        store = Store()
        websharing.addDefaultShareID(store, u'share id!', 24)
        websharing.addDefaultShareID(store, u'share id',  25)
        websharing.addDefaultShareID(store, u'share id.', -1)
        self.assertEqual(websharing.getDefaultShareID(store), u'share id')


    def test_findsNoItem(self):
        """
        Verify that L{websharing.getDefaultShareID} returns C{u''} if there is
        no default share ID.
        """
        self.assertEqual(websharing.getDefaultShareID(Store()), u'')
