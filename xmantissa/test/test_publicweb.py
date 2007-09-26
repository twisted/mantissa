from twisted.trial.unittest import TestCase

from axiom.store import Store
from axiom.plugins.userbasecmd import Create
from axiom.plugins.mantissacmd import Mantissa
from axiom.dependency import installOn

from nevow import rend, loaders, tags, context

from xmantissa.website import WebSite
from xmantissa.webapp import PrivateApplication
from xmantissa.publicweb import (
    PublicAthenaLivePage, PublicNavAthenaLivePage, _StandaloneNavFragment)
from xmantissa import signup



class _PublicAthenaLivePageTestMixin:
    """
    Mixin which defines test methods which exercise functionality provided by
    the various L{xmantissa.publicweb.PublicPageMixin} subclasses, like
    L{PublicAthenaLivePage} and L{PublicNavAthenaLivePage}.
    """
    def test_menubarRendererAnonymous(self):
        """
        Verify that the I{menubar} renderer of L{PublicAthenaLivePage} returns
        an instance of the I{login-links} pattern, with the I{signups} pattern
        slot filled when the viewer is anonymous.
        """
        signup._SignupTracker(
            store=self.store,
            signupItem=signup.FreeTicketSignup(
                store=self.store,
                prefixURL=u'lol',
                prompt=u'a prompt.'))

        page = PublicAthenaLivePage(self.store, rend.Fragment())
        page.docFactory = loaders.stan(
            tags.div[
                tags.div(pattern='signup')[
                    tags.slot('prompt'), tags.slot('url')],
                tags.div(pattern='login-links')[tags.slot('signups')]])
        ctx = context.WebContext(tag=tags.div())
        result = page.render_menubar(ctx, None)
        self.assertEqual(result.tagName, 'div')
        signups = result.slotData['signups']
        self.assertEqual(len(signups), 1)
        theSignup = signups[0]
        self.assertEqual(
            theSignup.slotData, {'prompt': u'a prompt.', 'url': u'/lol'})



class PublicNavAthenaLivePageTestCase(TestCase, _PublicAthenaLivePageTestMixin):
    """
    Tests for L{PublicNavAthenaLivePage}.
    """
    def setUp(self):
        self.store = Store()
        installOn(WebSite(store=self.store), self.store)


    def test_menubarRendererAuthenticated(self):
        """
        Verify that the I{menubar} renderer of L{PublicNavAthenaLivePage}
        returns a L{_StandaloneNavFragment} when the viewer is authenticated.
        """
        siteStore = Store(self.mktemp())

        def siteStoreTxn():
            Mantissa().installSite(siteStore, '/')

            return  Create().addAccount(
                siteStore, u'testuser', u'example.com', u'password').avatars.open()

        userStore = siteStore.transact(siteStoreTxn)

        def userStoreTxn():
            installOn(PrivateApplication(store=userStore), userStore)

            page = PublicNavAthenaLivePage(
                siteStore, rend.Fragment(), forUser=u'testuser@example.com')
            result = page.render_menubar(None, None)
            self.failUnless(isinstance(result, _StandaloneNavFragment))
            self.assertEqual(result.username, u'testuser@example.com')

        userStore.transact(userStoreTxn)



class PublicAthenaLivePageTestCase(TestCase, _PublicAthenaLivePageTestMixin):
    """
    Tests for L{PublicAthenaLivePage}.
    """
    def setUp(self):
        self.store = Store()
        installOn(WebSite(store=self.store), self.store)


    def test_menubarRendererAuthenticated(self):
        """
        Verify that the I{menubar} renderer of L{PublicAthenaLivePage} returns
        an instance of the I{loginged-in} pattern when the viewer is
        authenticated.
        """
        page = PublicAthenaLivePage(
            self.store, rend.Fragment(), forUser=u'foo@bar')
        page.docFactory = loaders.stan(tags.div[
            tags.div(attr='test_menubarRendererAuthenticated', pattern='logged-in')[
                tags.slot('username')]])
        result = page.render_menubar(None, None)
        self.assertEqual(result.tagName, 'div')
        self.assertEqual(
            result.attributes['attr'], 'test_menubarRendererAuthenticated')
        self.assertEqual(result.slotData['username'], u'foo@bar')
