"""
Tests for L{xmantissa.websharing}
"""
from twisted.trial.unittest import TestCase

from axiom.userbase import LoginMethod, LoginSystem
from axiom.store import Store
from axiom.dependency import installOn

from xmantissa import websharing, sharing

class WebSharingTestCase(TestCase):
    """
    Tests for L{xmantissa.websharing}
    """
    def test_linkTo(self):
        """
        Test that L{xmantissa.websharing.linkTo} generates a URL using the
        localpart of the account's internal L{axiom.userbase.LoginMethod}
        """
        s = Store(self.mktemp())
        ls = LoginSystem(store=s)
        installOn(ls, s)

        acct = ls.addAccount(
            u'right', u'host', u'', verified=True, internal=True)
        acct.addLoginMethod(
            u'wrong', u'host', internal=False, verified=False)

        share = sharing.shareItem(ls, shareID=u'loginsystem')
        self.assertEquals(
            websharing.linkTo(share, s),
            '/by/right/loginsystem')
