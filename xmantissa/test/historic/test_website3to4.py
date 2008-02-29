
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

        # Test its only remaining attribute.
        self.assertEquals(ws.hitCount, 100)
