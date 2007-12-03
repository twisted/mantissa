
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

from nevow import rend, context, inevow
from nevow.flat import flatten
from nevow.tags import title, div, span, h1, h2
from nevow.testutil import FakeRequest

from xmantissa.ixmantissa import INavigableElement
from xmantissa import signup
from xmantissa.website import WebSite
from xmantissa.webapp import PrivateApplication
from xmantissa.prefs import PreferenceAggregator
from xmantissa.webnav import Tab
from xmantissa.offering import InstalledOffering
from xmantissa.publicweb import (
    PublicAthenaLivePage, PublicNavAthenaLivePage, _OfferingsFragment)
from xmantissa import publicweb
from xmantissa.signup import PasswordResetResource


class FakeTheme(object):
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



class FakeNavigableElement(Item):
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



class FakeStore(object):
    """
    A trivial store with attributes needed for mocking stores used by various
    tests.
    """
    def __init__(self, test):
        """
        Create a FakeStore with a test to report errors to.
        """
        self.test = test        # test
        self.themes = [self]    # offering
        self.name = 'faketest'  # offering
        self.priority = 100000000 # offering


    def getDocFactory(self, fragmentName, default=None):
        """
        Retrieve a fake doc factory.
        """
        if fragmentName == 'shell':
            # ignore shell template requests, they're not the code we're testing.
            return
        self.test.getLoaderStore = self
        self.test.getLoaderName = fragmentName
        return self.test.template


    def findUnique(self, *a, **k):
        """
        Stubbed to confuse L{PasswordResetResource}
        """


    def query(self, installedOffering):
        """
        Extremely limited query that only does what we expect: return a list of
        'self' (I can double as a fake Installedoffering too)! as an installed
        offering, with the base theme.
        """
        self.test.assertEqual(installedOffering, InstalledOffering)
        return [self]


    def getOffering(self):
        """
        Return me, since the only thing these tests expect of an offering is
        the 'themes' attribute...
        """
        return self



class TestHonorInstalledThemes(TestCase):
    """
    Various classes should be using template resolvers to determine which theme
    to use based on a site store.
    """

    def setUp(self):
        """
        Set some attributes required for the tests.
        """
        self.template = object()
        self.store = FakeStore(self)


    def test_offeringsFragmentLoader(self):
        """
        L{_OfferingsFragment} should honor the installed themes list.
        """
        original = record('store')(self.store)
        offeringsFragment = _OfferingsFragment(original)
        self.assertIdentical(self.getLoaderStore, self.store)
        self.assertEqual(self.getLoaderName, 'front-page')
        self.assertIdentical(offeringsFragment.docFactory, self.template)


    def test_loginPageLoader(self):
        """
        L{LoginPage} should honor the installed themes list.
        """
        loginPage = publicweb.LoginPage(self.store)
        self.assertIdentical(self.getLoaderStore, self.store)
        self.assertEqual(self.getLoaderName, 'login')
        self.assertIdentical(loginPage.fragment, self.template)


    def test_passwordResetLoader(self):
        """
        L{LoginPage} should honor the installed themes list.
        """
        resetPage = PasswordResetResource(self.store)
        self.assertIdentical(self.getLoaderStore, self.store)
        self.assertEqual(self.getLoaderName, 'reset')
        self.assertIdentical(resetPage.fragment, self.template)



class AuthenticatedNavigationTestMixin:
    """
    Mixin defining test methods for the authenticated navigation view.
    """
    userinfo = (u'testuser', u'example.com')
    username = u'@'.join(userinfo)

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
        navigable = FakeNavigableElement(store=self.userStore)
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
        navigable = FakeNavigableElement(store=self.userStore)
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


    def test_noUsername(self):
        """
        The I{username} renderer should remove its node from the output when
        presented with a None username.
        """
        page = self.createPage(None)
        result = page.render_username(None, None)
        self.assertEqual(result, "")


    def usernameRenderingTest(self, username, hostHeader, expectedUsername):
        """
        Verify that the username will be rendered appropriately given the host
        of the HTTP request.

        @param username: the user's full login identifier.
        @param hostHeader: the value of the 'host' header.
        @param expectedUsername: the expected value of the rendered username.
        """
        page = self.createPage(username)
        userTag = span()
        req = FakeRequest()
        req.setHeader('Host', hostHeader)
        ctx = context.WebContext(tag=userTag)
        ctx.remember(req, inevow.IRequest)
        tag = page.render_username(ctx, None)
        self.assertEqual(tag.tagName, 'span')
        self.assertEqual(tag.children, [expectedUsername])


    def test_localUsername(self):
        """
        The I{username} renderer should render just the username when the
        username domain is the same as the HTTP request's domain. otherwise it
        should render the full username complete with domain.
        """
        domainUser = self.username.split('@')[0]
        return self.usernameRenderingTest(
            self.username, 'example.com', domainUser)


    def test_remoteUsername(self):
        """
        The I{username} renderer should render username with the domain when
        the username domain is different than the HTTP request's domain.
        """
        return self.usernameRenderingTest(
            self.username, 'not-example.com', self.username)


    def test_usernameWithHostPort(self):
        """
        The I{username} renderer should respect ports in the host headers.
        """
        domainUser = self.username.split('@')[0]
        return self.usernameRenderingTest(
            self.username, 'example.com:8080', domainUser)


    def test_prefixedDomainUsername(self):
        """
        The I{username} renderer should render just the username in the case
        where you are viewing a subdomain as well; if bob is viewing
        'jethro.divmod.com' or 'www.divmod.com', he should still see the
        username 'bob'.
        """
        domainUser = self.username.split('@')[0]
        return self.usernameRenderingTest(
            self.username, 'www.example.com', domainUser)



class _PublicAthenaLivePageTestMixin(AuthenticatedNavigationTestMixin):
    """
    Mixin which defines test methods which exercise functionality provided by
    the various L{xmantissa.publicweb.PublicPageMixin} subclasses, like
    L{PublicAthenaLivePage} and L{PublicNavAthenaLivePage}.
    """
    signupURL = u'sign/up'
    signupPrompt = u'sign up now'

    def setUp(self):
        self.store = Store(filesdir=self.mktemp())
        installOn(WebSite(store=self.store), self.store)
        self.siteStore = Store(filesdir=self.mktemp())

        def siteStoreTxn():
            Mantissa().installSite(self.siteStore, "/", generateCert=False)
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
