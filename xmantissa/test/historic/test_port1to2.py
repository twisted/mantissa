"""
Upgrader tests for L{xmantissa.port} items.
"""

from xmantissa.port import TCPPort, SSLPort
from xmantissa.website import WebSite

from axiom.test.historic.stubloader import StubbedTest

class PortInterfaceUpgradeTest(StubbedTest):
    """
    Schema upgrade tests for L{xmantissa.port} items.

    This upgrade adds an "interface" attribute.
    """
    def test_TCPPort(self):
        """
        Test the TCPPort 1->2 schema upgrade.
        """
        port = self.store.findUnique(TCPPort)
        self.assertEqual(port.portNumber, 80)
        self.assertTrue(isinstance(port.factory, WebSite))
        self.assertEqual(port.interface, u'')

    def test_SSLPort(self):
        """
        Test the SSLPort 1->2 schema upgrade.
        """
        port = self.store.findUnique(SSLPort)
        self.assertEqual(port.portNumber, 443)
        self.assertEqual(port.certificatePath,
                self.store.newFilePath('certificate'))
        self.assertTrue(isinstance(port.factory, WebSite))
        self.assertEqual(port.interface, u'')
