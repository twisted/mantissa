
from zope.interface import implements

from twisted.trial.unittest import TestCase
from twisted.trial.util import suppress as SUPPRESS

from epsilon.structlike import record

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer, inmemory
from axiom.plugins.userbasecmd import Create
from axiom.plugins.mantissacmd import Mantissa
from axiom.dependency import installOn

from nevow import rend, context
from nevow.flat import flatten
from nevow.tags import title, div, span, h1, h2
from nevow.testutil import FakeRequest

from xmantissa import signup
from xmantissa.ixmantissa import INavigableElement
from xmantissa.website import WebSite
from xmantissa.webapp import PrivateApplication
from xmantissa.prefs import PreferenceAggregator
from xmantissa.webnav import Tab
from xmantissa.publicweb import (
    _getLoader, PublicAthenaLivePage, PublicNavAthenaLivePage, _OfferingsFragment)
from xmantissa import publicweb


class MockTheme(object):
    """
    Trivial implementation of L{ITemplateNameResolver} which returns document
    factories from an in-memory dictionary.
    @ivar docFactories: C{dict} mapping fragment names to document factory
        objects.
    """
    def __init__(self, docFactories):
        self.docFactories = docFactories


    def getDocFactory(self, fragmentName, default=None):
        """
        Return the document factory for the given name, or the default value if
        the given name is unknown.
        """
        return self.docFactories.get(fragmentName, default)



class StubNavigableElement(Item):
    """
    Navigation contributing powerup tests can use to verify the behavior of the
    navigation renderers.
    """
    powerupInterfaces = (INavigableElement,)
    implements(*powerupInterfaces)

    dummy = integer()
    tabs = inmemory(
        doc="""
        The object which will be returned by L{getTabs}.
        """)

    def getTabs(self):
        """
        Return whatever tabs object has been set.
        """
        return self.tabs



class TestPrivateGetLoader(TestCase):
    """
    Test case for the private _getLoader function.
    """
    def setUp(self):
        """
        Setup a store and theme for the test case.
        """
        self.store = Store()
        self.fragmentName = 'private-get-loader'
        self.docFactory = object()
        self.theme = MockTheme({self.fragmentName: self.docFactory})


    def test_loadersInstalledOfferings(self):
        """
        L{_getLoader} should return the document factory for the given template
        from the list of installed themes.
        """
        getInstalledThemes = {self.store: [self.theme]}.get
        docFactory = _getLoader(
            self.store, self.fragmentName, getInstalledThemes)
        self.assertIdentical(docFactory, self.docFactory)
        self.assertRaises(
            RuntimeError,
            _getLoader, self.store, 'unknown-template', getInstalledThemes)



class TestHonorInstalledThemes(TestCase):
    """
    Various classes should be using _getLoader to determine which theme to use
    based on a site store.
    """

    def setUp(self):
        """
        Replace _getLoader with a temporary method of this test case.
        """
        publicweb._getLoader = self.fakeGetLoader
        self.template = object()
        self.store = object()


    def tearDown(self):
        """
        Replace the original _getLoader.
        """
        publicweb._getLoader = _getLoader


    def fakeGetLoader(self, store, fragmentName):
        """
        Pretend to be the private _getLoader function for the duration of the
        test.
        """
        self.getLoaderStore = store
        self.getLoaderName = fragmentName
        return self.template


    def test_offeringsFragmentLoader(self):
        """
        L{_OfferingsFragment} should honor the installed themes list by using
        _getLoader.
        """
        original = record('store')(self.store)
        offeringsFragment = _OfferingsFragment(original)
        self.assertIdentical(self.getLoaderStore, self.store)
        self.assertEqual(self.getLoaderName, 'front-page')
        self.assertIdentical(offeringsFragment.docFactory, self.template)


    def test_loginPageLoader(self):
        """
        L{LoginPage} should honor the installed themes list by using
        _getLoader.
        """
        loginPage = publicweb.LoginPage(self.store)
        self.assertIdentical(self.getLoaderStore, self.store)
        self.assertEqual(self.getLoaderName, 'login')
        self.assertIdentical(loginPage.fragment, self.template)



class AuthenticatedNavigationTestMixin:
    """
    Mixin defining test methods for the authenticated navigation view.
    """
    def createPage(self):
        """
        Create a subclass of L{PublicPageMixin} to be used by tests.
        """
        raise NotImplementedError("%r did not implement createPage" % (self,))


    def test_authenticatedAuthenticateLinks(self):
        """
        The I{authenticateLinks} renderer should remove the tag it is passed
        from the output if it is called on a L{PublicPageMixin} being rendered
        for an authenticated user.
        """
        page = self.createPage(self.username)
        authenticateLinksPattern = div()
        ctx = context.WebContext(tag=authenticateLinksPattern)
        tag = page.render_authenticateLinks(ctx, None)
        self.assertEqual(tag, '')


    def test_authenticatedStartmenu(self):
        """
        The I{startmenu} renderer should add navigation elements to the tag it
        is passed if it is called on a L{PublicPageMixin} being rendered for an
        authenticated user.
        """
        navigable = StubNavigableElement(store=self.userStore)
        installOn(navigable, self.userStore)
        navigable.tabs = [Tab('foo', 123, 0, [Tab('bar', 432, 0)])]

        page = self.createPage(self.username)
        startMenuTag = div[
            h1(pattern='tab'),
            h2(pattern='subtabs')]

        ctx = context.WebContext(tag=startMenuTag)
        tag = page.render_startmenu(ctx, None)
        self.assertEqual(tag.tagName, 'div')
        self.assertEqual(tag.attributes, {})
        children = [child for child in tag.children if child.pattern is None]
        self.assertEqual(len(children), 0)
        # This structure seems overly complex.
        tabs = list(tag.slotData.pop('tabs'))
        self.assertEqual(len(tabs), 1)
        fooTab = tabs[0]
        self.assertEqual(fooTab.tagName, 'h1')
        self.assertEqual(fooTab.attributes, {})
        self.assertEqual(fooTab.children, [])
        self.assertEqual(fooTab.slotData['href'], self.privateApp.linkTo(123))
        self.assertEqual(fooTab.slotData['name'], 'foo')
        self.assertEqual(fooTab.slotData['kids'].tagName, 'h2')
        subtabs = list(fooTab.slotData['kids'].slotData['kids'])
        self.assertEqual(len(subtabs), 1)
        barTab = subtabs[0]
        self.assertEqual(barTab.tagName, 'h1')
        self.assertEqual(barTab.attributes, {})
        self.assertEqual(barTab.children, [])
        self.assertEqual(barTab.slotData['href'], self.privateApp.linkTo(432))
        self.assertEqual(barTab.slotData['name'], 'bar')
        self.assertEqual(barTab.slotData['kids'], '')


    def test_authenticatedSettingsLink(self):
        """
        The I{settingsLink} renderer should add the URL of the settings item to
        the tag it is passed if it is called on a L{PublicPageMixin} being
        rendered for an authenticated user.
        """
        page = self.createPage(self.username)
        settingsLinkPattern = div()
        ctx = context.WebContext(tag=settingsLinkPattern)
        tag = page.render_settingsLink(ctx, None)
        self.assertEqual(tag.tagName, 'div')
        self.assertEqual(tag.attributes, {})
        self.assertEqual(
            tag.children,
            [self.privateApp.linkTo(
                    self.userStore.findUnique(PreferenceAggregator).storeID)])


    def test_authenticatedLogout(self):
        """
        The I{logout} renderer should return the tag it is passed if it is
        called on a L{PublicPageMixin} being rendered for an authenticated
        user.
        """
        page = self.createPage(self.username)
        logoutPattern = div()
        ctx = context.WebContext(tag=logoutPattern)
        tag = page.render_logout(ctx, None)
        self.assertIdentical(logoutPattern, tag)


    def test_authenticatedApplicationNavigation(self):
        """
        The I{applicationNavigation} renderer should add primary navigation
        elements to the tag it is passed if it is called on a
        L{PublicPageMixin} being rendered for an authenticated user.
        """
        navigable = StubNavigableElement(store=self.userStore)
        installOn(navigable, self.userStore)
        navigable.tabs = [Tab('foo', 123, 0, [Tab('bar', 432, 0)])]
        request = FakeRequest()

        page = self.createPage(self.username)
        navigationPattern = div[
            span(id='app-tab', pattern='app-tab'),
            span(id='tab-contents', pattern='tab-contents')]
        ctx = context.WebContext(tag=navigationPattern)
        ctx.remember(request)
        tag = page.render_applicationNavigation(ctx, None)
        self.assertEqual(tag.tagName, 'div')
        self.assertEqual(tag.attributes, {})
        children = [child for child in tag.children if child.pattern is None]
        self.assertEqual(children, [])
        self.assertEqual(len(tag.slotData['tabs']), 1)
        fooTab = tag.slotData['tabs'][0]
        self.assertEqual(fooTab.attributes, {'id': 'app-tab'})
        self.assertEqual(fooTab.slotData['name'], 'foo')
        fooContent = fooTab.slotData['tab-contents']
        self.assertEqual(fooContent.attributes, {'id': 'tab-contents'})
        self.assertEqual(
            fooContent.slotData['href'], self.privateApp.linkTo(123))


    def test_title(self):
        """
        The I{title} renderer should add the wrapped fragment's title
        attribute, if any, or the default "Divmod".
        """
        page = self.createPage(self.username)
        titleTag = title()
        tag = page.render_title(context.WebContext(tag=titleTag), None)
        self.assertIdentical(tag, titleTag)
        flattened = flatten(tag)
        self.assertSubstring(flatten(getattr(page.fragment, 'title', 'Divmod')),
                             flattened)



class _PublicAthenaLivePageTestMixin(AuthenticatedNavigationTestMixin):
    """
    Mixin which defines test methods which exercise functionality provided by
    the various L{xmantissa.publicweb.PublicPageMixin} subclasses, like
    L{PublicAthenaLivePage} and L{PublicNavAthenaLivePage}.
    """
    userinfo = (u'testuser', u'example.com')
    username = u'@'.join(userinfo)

    signupURL = u'sign/up'
    signupPrompt = u'sign up now'

    def setUp(self):
        self.store = Store()
        installOn(WebSite(store=self.store), self.store)
        self.siteStore = Store(self.mktemp())

        def siteStoreTxn():
            Mantissa().installSite(self.siteStore, '/')
            ticketed = signup.FreeTicketSignup(
                store=self.siteStore, prefixURL=self.signupURL,
                prompt=self.signupPrompt)
            signup._SignupTracker(store=self.siteStore, signupItem=ticketed)

            return  Create().addAccount(
                self.siteStore, self.userinfo[0],
                self.userinfo[1], u'password').avatars.open()

        self.userStore = self.siteStore.transact(siteStoreTxn)

        def userStoreTxn():
            self.privateApp = PrivateApplication(store=self.userStore)
            installOn(self.privateApp, self.userStore)
        self.userStore.transact(userStoreTxn)


    def test_unauthenticatedAuthenticateLinks(self):
        """
        The I{authenticateLinks} renderer should add login and signup links to
        the tag it is passed, if it is called on a L{PublicPageMixin} being
        rendered for an unauthenticated user.
        """
        page = self.createPage(None)
        authenticateLinksPattern = div[span(pattern='signup-link')]
        ctx = context.WebContext(tag=authenticateLinksPattern)
        tag = page.render_authenticateLinks(ctx, None)
        self.assertEqual(tag.tagName, 'div')
        self.assertEqual(tag.attributes, {})
        children = [child for child in tag.children if child.pattern is None]
        self.assertEqual(len(children), 1)
        self.assertEqual(
            children[0].slotData,
            {'prompt': self.signupPrompt, 'url': '/' + self.signupURL})


    def test_unauthenticatedStartmenu(self):
        """
        The I{startmenu} renderer should remove the tag it is passed from the
        output if it is called on a L{PublicPageMixin} being rendered for an
        unauthenticated user.
        """
        page = self.createPage(None)
        startMenuTag = div()
        ctx = context.WebContext(tag=startMenuTag)
        tag = page.render_startmenu(ctx, None)
        self.assertEqual(tag, '')


    def test_unauthenticatedSettingsLink(self):
        """
        The I{settingsLink} renderer should remove the tag it is passed from
        the output if it is called on a L{PublicPageMixin} being rendered for
        an unauthenticated user.
        """
        page = self.createPage(None)
        settingsLinkPattern = div()
        ctx = context.WebContext(tag=settingsLinkPattern)
        tag = page.render_settingsLink(ctx, None)
        self.assertEqual(tag, '')


    def test_unauthenticatedLogout(self):
        """
        The I{logout} renderer should remove the tag it is passed from the
        output if it is called on a L{PublicPageMixin} being rendered for an
        authenticated user.
        """
        page = self.createPage(None)
        logoutPattern = div()
        ctx = context.WebContext(tag=logoutPattern)
        tag = page.render_logout(ctx, None)
        self.assertEqual(tag, '')


    def test_unauthenticatedApplicationNavigation(self):
        """
        The I{applicationNavigation} renderer should remove the tag it is
        passed from the output if it is called on a L{PublicPageMixin} being
        rendered for an unauthenticated user.
        """
        page = self.createPage(None)
        navigationPattern = div()
        ctx = context.WebContext(tag=navigationPattern)
        tag = page.render_applicationNavigation(ctx, None)
        self.assertEqual(tag, '')



class TestFragment(rend.Fragment):
    title = u'a test fragment'



class PublicAthenaLivePageTestCase(_PublicAthenaLivePageTestMixin, TestCase):
    """
    Tests for L{PublicAthenaLivePage}.
    """
    def createPage(self, forUser):
        return PublicAthenaLivePage(
            self.siteStore, TestFragment(), forUser=forUser)



class PublicNavAthenaLivePageTestCase(_PublicAthenaLivePageTestMixin, TestCase):
    """
    Tests for L{PublicNavAthenaLivePage}.
    """
    suppress = [SUPPRESS(category=DeprecationWarning)]

    def createPage(self, forUser):
        return PublicNavAthenaLivePage(
            self.siteStore, TestFragment(), forUser=forUser)
