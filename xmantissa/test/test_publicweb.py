from twisted.trial.unittest import TestCase

from axiom.store import Store
from axiom.plugins.userbasecmd import Create
from axiom.plugins.mantissacmd import Mantissa
from axiom.dependency import installOn

from nevow import rend

from xmantissa.website import WebSite
from xmantissa.webapp import PrivateApplication
from xmantissa.publicweb import (
    PublicAthenaLivePage, PublicNavAthenaLivePage, _StandaloneNavFragment)

class PublicNavAthenaLivePageTestCase(TestCase):
    """
    Tests for L{PublicNavAthenaLivePage}.
    """
    def test_menubarRendererAnonymous(self):
        """
        Verify that the I{menubar} renderer of L{PublicNavAthenaLivePage}
        returns the empty string when the viewer is anonymous.
        """
        store = Store()
        installOn(WebSite(store=store), store)

        page = PublicNavAthenaLivePage(store, rend.Fragment())
        self.assertEqual(page.render_menubar(None, None), '')


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



class PublicAthenaLivePageTestCase(TestCase):
    """
    Tests for L{PublicAthenaLivePage}.
    """
    def setUp(self):
        self.store = Store()
        installOn(WebSite(store=self.store), self.store)


    def test_menubarRendererAnonymous(self):
        """
        Verify that the I{menubar} renderer of L{PublicAthenaLivePage} returns
        the empty string when the viewer is anonymous.
        """
        page = PublicAthenaLivePage(self.store, rend.Fragment())
        self.assertEqual(page.render_menubar(None, None), '')


    def test_menubarRendererAuthenticated(self):
        """
        Verify that the I{menubar} renderer of L{PublicAthenaLivePage} returns
        the empty string when the viewer is authenticated.
        """
        page = PublicAthenaLivePage(
            self.store, rend.Fragment(), forUser=u'foo@bar')
        self.assertEqual(page.render_menubar(None, None), '')
