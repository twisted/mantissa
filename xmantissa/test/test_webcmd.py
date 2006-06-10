
import sys

from cStringIO import StringIO

from twisted.trial.unittest import TestCase

from axiom.plugins import webcmd

from axiom.store import Store


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


class TestIdempotentListing(TestCase):

    def setUp(self):
        self.store = Store()

    def getStore(self):
        # fake out "parent" implementation for stuff.
        return self.store

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
