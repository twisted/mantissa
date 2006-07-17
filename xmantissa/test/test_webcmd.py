
import os, sys

from cStringIO import StringIO

from twisted.trial.unittest import TestCase

from axiom.plugins import webcmd

from axiom.store import Store

from xmantissa.website import WebSite


def _captureStandardOutput(f, *a, **k):
    """
    Capture standard output produced during the invocation of a function, and
    return it.

    Since this is for testing command-line tools, SystemExit errors that
    indicate a successful return are caught.
    """
    io = StringIO()
    oldout = sys.stdout
    sys.stdout = io
    try:
        try:
            f(*a, **k)
        finally:
            sys.stdout = oldout
    except SystemExit, se:
        if se.args[0]:
            raise
    return io.getvalue()


class CommandStubMixin:
    """
    Pretend to be the parent command for a subcommand.
    """
    def getStore(self):
        # fake out "parent" implementation for stuff.
        return self.store


class TestIdempotentListing(CommandStubMixin, TestCase):

    def setUp(self):
        self.store = Store()

    def _list(self):
        wconf = webcmd.WebConfiguration()
        wconf.parent = self
        wout = _captureStandardOutput(wconf.parseOptions, ['--list'])
        return wout

    def testListDoesNothing(self):
        """
        Verify that 'axiomatic -d foo.axiom web --list' does not modify
        anything, by running it twice and verifying that the generated output
        is identical the first and second time.
        """
        self.assertEquals(self._list(),
                          self._list())


class ConfigurationTestCase(CommandStubMixin, TestCase):
    def setUp(self):
        self.store = Store()


    def test_shortOptionParsing(self):
        """
        Test that the short form of all the supported command line options are
        parsed correctly.
        """
        opt = webcmd.WebConfiguration()
        opt.parent = self
        opt.parseOptions([
                '-p', '8080', '-s', '8443', '-f', 'file/name',
                '-h', 'http.log', '-H', 'example.com'])
        self.assertEquals(opt['port'], '8080')
        self.assertEquals(opt['secure-port'], '8443')
        self.assertEquals(opt['pem-file'], 'file/name')
        self.assertEquals(opt['http-log'], 'http.log')
        self.assertEquals(opt['hostname'], 'example.com')


    def test_longOptionParsing(self):
        """
        Test that the long form of all the supported command line options are
        parsed correctly.
        """
        opt = webcmd.WebConfiguration()
        opt.parent = self
        opt.parseOptions([
                '--port', '8080', '--secure-port', '8443',
                '--pem-file', 'file/name', '--http-log', 'http.log',
                '--hostname', 'example.com'])
        self.assertEquals(opt['port'], '8080')
        self.assertEquals(opt['secure-port'], '8443')
        self.assertEquals(opt['pem-file'], 'file/name')
        self.assertEquals(opt['http-log'], 'http.log')
        self.assertEquals(opt['hostname'], 'example.com')


    def test_staticParsing(self):
        """
        Test that the --static option parses arguments of the form
        "url:filename" correctly.
        """
        opt = webcmd.WebConfiguration()
        opt.parent = self
        opt.parseOptions([
                '--static', 'foo:bar',
                '--static', 'quux/fooble:/bar/baz'])
        self.assertEquals(
            opt.staticPaths,
            [('foo', os.path.abspath('bar')),
             ('quux/fooble', '/bar/baz')])


    def test_hostname(self):
        """
        Test that the --hostname option changes the C{hostname} attribute of
        the C{WebSite} instance being manipulated.
        """
        ws = WebSite(store=self.store)
        ws.installOn(self.store)

        opt = webcmd.WebConfiguration()
        opt.parent = self
        opt['hostname'] = 'example.com'
        opt.postOptions()

        self.assertEquals(ws.hostname, u'example.com')


    def test_unsetHostname(self):
        """
        Test that passing an empty string to --hostname changes the C{hostname}
        attribute of the C{WebSite} instance to C{None}.
        """
        ws = WebSite(store=self.store)
        ws.installOn(self.store)

        opt = webcmd.WebConfiguration()
        opt.parent = self
        opt['hostname'] = ''
        opt.postOptions()

        self.assertEquals(ws.hostname, None)
