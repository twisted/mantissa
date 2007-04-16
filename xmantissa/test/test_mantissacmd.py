from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath

from epsilon.sslverify import Certificate

from axiom.store import Store
from axiom.plugins.mantissacmd import genSerial, Mantissa
from axiom.test.util import CommandStubMixin

class MiscTestCase(TestCase):
    def test_genSerial(self):
        """
        Test that L{genSerial} returns valid unique serials.
        """
        s1 = genSerial()
        self.assertTrue(isinstance(s1, int), '%r must be an int' % (s1,))
        self.assertTrue(s1 >= 0, '%r must be positive' % (s1,))
        s2 = genSerial()
        self.assertNotEqual(s1, s2)

class CertificateTestCase(CommandStubMixin, TestCase):
    def test_certGeneration(self):
        """
        Test that 'axiomatic mantissa' generates SSL certificates with a
        different unique serial on each invocation.
        """
        def _getCert():
            """
            Get the SSL certificate from an Axiom store directory.
            """
            certFile = FilePath(self.dbdir).child('files').child('server.pem')
            return Certificate.loadPEM(certFile.open('rb').read())

        m = Mantissa()
        m.parent = self

        self.dbdir = self.mktemp()
        self.store = Store(self.dbdir)
        m.parseOptions(['--admin-password', 'foo'])
        cert1 = _getCert()

        self.dbdir = self.mktemp()
        self.store = Store(self.dbdir)
        m.parseOptions(['--admin-password', 'foo'])
        cert2 = _getCert()

        self.assertNotEqual(cert1.serialNumber(), cert2.serialNumber())
