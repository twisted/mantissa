from twisted.trial.unittest import TestCase

from axiom.store import Store
from axiom.substore import SubStore

from nevow.athena import LiveFragment
from nevow import rend
from nevow.rend import WovenContext
from nevow.testutil import FakeRequest
from nevow.inevow import IRequest

from xmantissa import website, webapp

class TestFragment(LiveFragment):
    def locateChild(self, ctx, segs):
        if segs[0] == 'child-of-fragment':
            return ('I AM A CHILD OF THE FRAGMENT', segs[1:])
        return rend.NotFound



class FragmentWrappingTestCase(TestCase):
    def test_childLookup(self):
        s = Store(self.mktemp())
        website.WebSite(store=s).installOn(s)

        ss = SubStore.createNew(s, ['child', 'lookup'])
        ss = ss.open()

        privapp = webapp.PrivateApplication(store=ss)
        privapp.installOn(ss)

        class factory:
            def getClient(self, seg):
                if seg == 'client-of-livepage':
                    return 'I AM A CLIENT OF THE LIVEPAGE'

        navpage = webapp.GenericNavigationAthenaPage(
                        privapp,
                        TestFragment(),
                        None)

        navpage.factory = factory()

        self.assertEqual(navpage.locateChild(None, ('child-of-fragment',)),
                         ('I AM A CHILD OF THE FRAGMENT', ()))
        self.assertEqual(navpage.locateChild(None, ('client-of-livepage',)),
                         ('I AM A CLIENT OF THE LIVEPAGE', ()))



class AthenaNavigationTestCase(TestCase):
    """
    Test aspects of L{GenericNavigationAthenaPage}.
    """
    def _render(self, resource):
        """
        Test helper which tries to render the given resource.
        """
        ctx = WovenContext()
        req = FakeRequest()
        ctx.remember(req, IRequest)
        return req, resource.renderHTTP(ctx)


    def test_jsmodules(self):
        """
        Test that the C{jsmodule} child of a L{webapp.PrivateRootPage} is an
        object which will serve up JavaScript modules.
        """
        s = Store()
        a = webapp.PrivateApplication(store=s)
        p = webapp.PrivateRootPage(a, None)
        resource, segments = p.locateChild(None, ('jsmodule',))
        self.failUnless(isinstance(resource, webapp.HashedJSModuleNames))
        self.assertEquals(segments, ())


    def test_resourceFactory(self):
        """
        Test that L{HashedJSModuleNames.resourceFactory} returns a
        L{static.Data} with the right C{expires} value.
        """
        f = self.mktemp()
        fObj = file(f, 'w')
        fObj.write('/* Hello, world. /*\n')
        fObj.close()
        m = webapp.HashedJSModuleNames({'module': f})
        d = m.resourceFactory(f)
        d.time = lambda: 12345
        req, result = self._render(d)
        self.assertEquals(
            req.headers['expires'],
            'Tue, 31 Dec 1974 03:25:45 GMT')
        self.assertEquals(
            result,
            '/* Hello, world. /*\n')

