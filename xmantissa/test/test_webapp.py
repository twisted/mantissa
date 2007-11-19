from zope.interface import implements

from twisted.trial.unittest import TestCase
from twisted.internet import defer

from axiom.store import Store
from axiom.userbase import LoginSystem
from axiom.item import Item
from axiom.attributes import integer
from axiom.substore import SubStore
from axiom.dependency import installOn
from axiom.plugins.userbasecmd import Create
from axiom.plugins.mantissacmd import Mantissa

from nevow.athena import LiveFragment
from nevow import rend
from nevow.rend import WovenContext
from nevow.testutil import FakeRequest
from nevow.inevow import IRequest, IResource

from xmantissa.ixmantissa import ITemplateNameResolver
from xmantissa import website, webapp
from xmantissa.test.test_publicweb import AuthenticatedNavigationTestMixin

class FakeResourceItem(Item):
    unused = integer()
    implements(IResource)

class WebIDLocationTest(TestCase):

    def setUp(self):
        store = Store()
        ss = SubStore.createNew(store, ['test']).open()
        self.pa = webapp.PrivateApplication(store=ss)
        installOn(self.pa, ss)


    def test_powersUpTemplateNameResolver(self):
        """
        L{PrivateApplication} implements L{ITemplateNameResolver} and should
        power up the store it is installed on for that interface.
        """
        self.assertIn(
            self.pa,
            self.pa.store.powerupsFor(ITemplateNameResolver))


    def test_suchWebID(self):
        """
        Verify that retrieving a webID gives the correct resource.
        """
        i = FakeResourceItem(store=self.pa.store)
        wid = self.pa.toWebID(i)
        ctx = FakeRequest()
        self.assertEqual(self.pa.createResource().locateChild(ctx, [wid]),
                         (i, []))


    def test_noSuchWebID(self):
        """
        Verify that non-existent private URLs generate 'not found' responses.
        """
        ctx = FakeRequest()
        for segments in [
            # something that looks like a valid webID
            ['0000000000000000'],
            # something that doesn't
            ["nothing-here"],
            # more than one segment
            ["two", "segments"]]:
            self.assertEqual(self.pa.createResource().locateChild(ctx, segments),
                             rend.NotFound)


class TestFragment(LiveFragment):
    def locateChild(self, ctx, segs):
        if segs[0] == 'child-of-fragment':
            return ('I AM A CHILD OF THE FRAGMENT', segs[1:])
        return rend.NotFound


class TestClientFactory(object):
    """
    Dummy L{LivePageFactory}.

    @ivar magicSegment: The segment for which to return L{returnValue} from
    L{getClient}.
    @type magicSegment: C{str}

    @ivar returnValue: The value to return from L{getClient} when it is passed
    L{magicSegment}.
    @type returnValue: C{str}.
    """
    def __init__(self, magicSegment, returnValue):
        self.magicSegment = magicSegment
        self.returnValue = returnValue


    def getClient(self, seg):
        if seg == self.magicSegment:
            return self.returnValue


class GenericNavigationAthenaPageTests(TestCase,
                                       AuthenticatedNavigationTestMixin):
    """
    Tests for L{GenericNavigationAthenaPage}.
    """
    def setUp(self):
        """
        Set up a site store, user store, and page instance to test with.
        """
        self.siteStore = Store()
        def siteStoreTxn():
            installOn(
                website.WebSite(store=self.siteStore),
                self.siteStore)

            self.userStore = SubStore.createNew(
                self.siteStore, ['child', 'lookup']).open()
        self.siteStore.transact(siteStoreTxn)

        def userStoreTxn():
            self.privateApp = webapp.PrivateApplication(store=self.userStore)
            installOn(self.privateApp, self.userStore)

            self.navpage = self.createPage(None)
        self.userStore.transact(userStoreTxn)


    def createPage(self, username):
        """
        Create a L{webapp.GenericNavigationAthenaPage} for the given user.
        """
        return webapp.GenericNavigationAthenaPage(
            self.privateApp,
            TestFragment(),
            self.privateApp.getPageComponents(),
            username)


    def test_childLookup(self):
        """
        L{GenericNavigationAthenaPage} should delegate to its fragment and its
        L{LivePageFactory} when it cannot find a child itself.
        """
        self.navpage.factory = tcf = TestClientFactory(
            'client-of-livepage', 'I AM A CLIENT OF THE LIVEPAGE')

        self.assertEqual(self.navpage.locateChild(None,
                                                 ('child-of-fragment',)),
                         ('I AM A CHILD OF THE FRAGMENT', ()))
        self.assertEqual(self.navpage.locateChild(None,
                                             (tcf.magicSegment,)),
                        (tcf.returnValue, ()))


    def test_jsModuleLocation(self):
        """
        L{GenericNavigationAthenaPage.beforeRender} should should call
        L{xmantissa.website.MantissaLivePage.beforeRender}, which shares its
        Athena JavaScript module location with all other pages that use
        L{xmantissa.cachejs}, and provide links to /__jsmodule__/.
        """
        ctx = WovenContext()
        req = FakeRequest()
        ctx.remember(req, IRequest)
        self.navpage.beforeRender(ctx)
        urlObj = self.navpage.getJSModuleURL('Mantissa')
        self.assertEqual(urlObj.pathList()[0], '__jsmodule__')


    def test_beforeRenderDelegation(self):
        """
        L{GenericNavigationAthenaPage.beforeRender} should call
        C{beforeRender} on the wrapped fragment, if it's defined, and return
        its result.
        """
        contexts = []
        result = defer.succeed(None)
        def beforeRender(ctx):
            contexts.append(ctx)
            return result
        self.navpage.fragment.beforeRender = beforeRender
        ctx = WovenContext()
        ctx.remember(FakeRequest(), IRequest)
        self.assertIdentical(
            self.navpage.beforeRender(ctx), result)
        self.assertEqual(contexts, [ctx])



class PrivateApplicationTestCase(TestCase):
    """
    Tests for L{webapp.PrivateApplication}.
    """
    def setUp(self):
        self.siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.siteStore, "/", generateCert=False)

        self.userAccount = Create().addAccount(
            self.siteStore, u'testuser', u'example.com', u'password')
        self.userStore = self.userAccount.avatars.open()

        self.webapp = webapp.PrivateApplication(store=self.userStore)
        installOn(self.webapp, self.userStore)


    def test_createResourceUsername(self):
        """
        L{webapp.PrivateApplication.createResource} should figure out the
        right username and pass it to L{webapp.PrivateRootPage}.
        """
        rootPage = self.webapp.createResource()
        self.assertEqual(rootPage.username, u'testuser@example.com')
