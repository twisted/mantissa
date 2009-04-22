import sha

from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath

from nevow.inevow import IRequest
from nevow.context import WovenContext
from nevow.testutil import FakeRequest

from xmantissa.cachejs import HashedJSModuleProvider, CachedJSModule


class JSCachingTestCase(TestCase):
    """
    Tests for L{xmantissa.cachejs}.
    """
    hostname = 'test-mantissa-js-caching.example.com'
    def _render(self, resource):
        """
        Test helper which tries to render the given resource.
        """
        ctx = WovenContext()
        req = FakeRequest(headers={'host': self.hostname})
        ctx.remember(req, IRequest)
        return req, resource.renderHTTP(ctx)


    def test_hashExpiry(self):
        """
        L{HashedJSModuleProvider.resourceFactory} should return a L{static.Data}
        with an C{expires} value far in the future.
        """
        MODULE_NAME = 'Dummy.Module'
        MODULE_CONTENT = '/* Hello, world. /*\n'
        f = self.mktemp()
        fObj = file(f, 'w')
        fObj.write(MODULE_CONTENT)
        fObj.close()
        m = HashedJSModuleProvider()
        m.moduleCache[MODULE_NAME] = CachedJSModule(
            MODULE_NAME, FilePath(f))
        d, segs = m.locateChild(None, [sha.new(MODULE_CONTENT).hexdigest(),
                                       MODULE_NAME])
        self.assertEqual([], segs)
        d.time = lambda: 12345
        req, result = self._render(d)
        self.assertEquals(
            req.headers['expires'],
            'Tue, 31 Dec 1974 03:25:45 GMT')
        self.assertEquals(
            result,
            '/* Hello, world. /*\n')



