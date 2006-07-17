
"""
Test for upgrading a WebSite by giving it a hostname attribute.
"""

from nevow.inevow import IResource

from axiom.test.historic.stubloader import StubbedTest

class WebSiteUpgradeTestCase(StubbedTest):
    def test_hostnameUpgrade(self):
        """
        Test that upgraded WebSite instances have their hostname attribute set
        to something and that all their old attributes are preserved.
        """
        # Test that it is still an IResource powerup
        ws = IResource(self.store)

        # Test its old attributes
        self.assertIdentical(ws.installedOn, self.store)
        self.assertEquals(ws.portNumber, 80)
        self.assertEquals(ws.securePortNumber, 443)
        self.assertEquals(ws.certificateFile, 'path/to/cert.pem')
        self.assertEquals(ws.httpLog, 'path/to/httpd.log')
        self.assertEquals(ws.hitCount, 100)

        # Test the new attribute.  We can't actually figure out what hostname
        # the administrator would want, so we leave it as None (which is the
        # default for new WebSites anyway).
        self.assertIdentical(ws.hostname, None)
