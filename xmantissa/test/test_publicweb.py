
from zope.interface import implements

from twisted.trial.unittest import TestCase
from twisted.trial.util import suppress as SUPPRESS

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import boolean, integer, inmemory
from axiom.plugins.userbasecmd import Create
from axiom.plugins.mantissacmd import Mantissa
from axiom.dependency import installOn

from nevow import rend, context, inevow
from nevow.flat import flatten
from nevow.tags import title, div, span, h1, h2
from nevow.testutil import FakeRequest

from xmantissa.ixmantissa import (
    IPublicPage, ITemplateNameResolver, INavigableElement)
from xmantissa import signup
from xmantissa.website import WebSite, APIKey
from xmantissa.webapp import PrivateApplication
from xmantissa.prefs import PreferenceAggregator
from xmantissa.webnav import Tab
from xmantissa.offering import Offering, InstalledOffering
from xmantissa.publicweb import (
    FrontPage, PublicAthenaLivePage, PublicNavAthenaLivePage,
    _OfferingsFragment)
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



class FakeTemplateNameResolver(object):
    """
    Template name resolver which knows about one template.

    @ivar correctName: The name of the template this resolver knows about.

    @ivar correctFactory: The template which will be returned for
        C{correctName}.
    """
    implements(ITemplateNameResolver)

    def __init__(self, correctName, correctFactory):
        self.correctName = correctName
        self.correctFactory = correctFactory


    def getDocFactory(self, name, default=None):
        """
        Return the default for all names other than C{self.correctName}.
        Return C{self.correctFactory} for that.
        """
        if name == self.correctName:
            return self.correctFactory
        return default



class TestHonorInstalledThemes(TestCase):
    """
    Various classes should be using template resolvers to determine which theme
    to use based on a site store.
    """
    def setUp(self):
        self.correctDocumentFactory = object()
        self.store = Store()
        self.fakeResolver = FakeTemplateNameResolver(
            None, self.correctDocumentFactory)

        def fakeConform(interface):
            if interface is ITemplateNameResolver:
                return self.fakeResolver
            return None
        self.store.__conform__ = fakeConform


    def test_offeringsFragmentLoader(self):
        """
        L{_OfferingsFragment.docFactory} is the I{front-page} template loaded
        from the store's ITemplateNameResolver.
        """
        self.fakeResolver.correctName = 'front-page'
        frontPage = FrontPage(store=self.store)
        offeringsFragment = _OfferingsFragment(frontPage)
        self.assertIdentical(
            offeringsFragment.docFactory, self.correctDocumentFactory)


    def test_loginPageLoader(self):
        """
        L{LoginPage.fragment} is the I{login} template loaded from the store's
        ITemplateNameResolver.
        """
        self.fakeResolver.correctName = 'login'
        page = publicweb.LoginPage(self.store)
        self.assertIdentical(
            page.fragment, self.correctDocumentFactory)


    def test_passwordResetLoader(self):
        """
        L{PasswordResetResource.fragment} is the I{login} template loaded from
        the store's ITemplateNameResolver.
        """
        self.fakeResolver.correctName = 'reset'
        resetPage = PasswordResetResource(self.store)
        self.assertIdentical(
            resetPage.fragment, self.correctDocumentFactory)



class FakeApplication(Item):
    """
    Fake implementation of an application installed by an offering.
    """
    implements(IPublicPage)

    index = boolean(doc="""
    Flag indicating whether this application wants to be included on the front
    page.
    """)



class _OfferingsFragmentTestCase(TestCase):
    """
    Tests for L{_OFferingsFragment}.
    """
    def test_offerings(self):
        """
        L{_OfferingsFragment.data_offerings} returns a generator of C{dict}
        mapping C{'name'} to the name of an installed offering with an
        L{IPublicPage} powerup which requests a place on the public page.
        """
        store = Store()

        firstOffering = Offering(u'first offering', None, None, None, None,
                                 None, None)
        firstInstalledOffering = InstalledOffering(
            store=store, application=FakeApplication(store=store, index=True),
            offeringName=firstOffering.name)
        object.__setattr__(
            firstInstalledOffering, 'getOffering', lambda: firstOffering)

        secondOffering = Offering(u'second offering', None, None, None, None,
                                  None, None)
        secondInstalledOffering = InstalledOffering(
            store=store, application=FakeApplication(store=store, index=False),
            offeringName=secondOffering.name)
        object.__setattr__(
            secondInstalledOffering, 'getOffering', lambda: secondOffering)

        fragment = _OfferingsFragment(FrontPage(store=store))
        self.assertEqual(
            list(fragment.data_offerings(None, None)),
            [{'name': firstOffering.name}])



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


    def rootURL(self, request):
        """
        Return the root URL for the website associated with the page returned
        by L{createPage}.
        """
        raise NotImplementedError("%r did not implement rootURL" % (self,))


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


    def test_rootURL(self):
        """
        The I{base} renderer should add the website's root URL to the tag it is
        passed.
        """
        page = self.createPage(self.username)
        baseTag = div()
        request = FakeRequest(headers={'host': 'example.com'})
        ctx = context.WebContext(tag=baseTag)
        ctx.remember(request, inevow.IRequest)
        tag = page.render_rootURL(ctx, None)
        self.assertIdentical(tag, baseTag)
        self.assertEqual(tag.attributes, {})
        self.assertEqual(tag.children, [self.rootURL(request)])


    def test_noUsername(self):
        """
        The I{username} renderer should remove its node from the output when
        presented with a None username.
        """
        page = self.createPage(None)
        result = page.render_username(None, None)
        self.assertEqual(result, "")


    def test_noUrchin(self):
        """
        When there's no Urchin API key installed, the I{urchin} renderer should
        remove its node from the output.
        """
        page = self.createPage(None)
        result = page.render_urchin(None, None)
        self.assertEqual(result, "")


    def test_urchin(self):
        """
        When an Urchin API key is present, the code for enabling Google
        Analytics tracking should be inserted into the shell template.
        """
        keyString = u"UA-99018-11"
        APIKey.setKeyForAPI(self.siteStore, APIKey.URCHIN, keyString)
        page = self.createPage(None)
        t = div()
        result = page.render_urchin(context.WebContext(tag=t), None)
        self.assertEqual(result.slotData['urchin-key'], keyString)


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
            self.website = self.siteStore.findUnique(WebSite)
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


    def rootURL(self, request):
        """
        Return the root URL as reported by C{self.website}.
        """
        return self.website.rootURL(request)


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
