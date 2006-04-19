from twisted.trial.unittest import TestCase

from axiom.store import Store

from nevow.athena import LiveFragment
from nevow import rend

from xmantissa import webapp

class TestFragment(LiveFragment):
    def locateChild(self, ctx, segs):
        if segs[0] == 'child-of-fragment':
            return ('I AM A CHILD OF THE FRAGMENT', segs[1:])
        return rend.NotFound

class FragmentWrappingTestCase(TestCase):
    def test_childLookup(self):
        s = Store()

        privapp = webapp.PrivateApplication(store=s)
        privapp.installOn(s)

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

