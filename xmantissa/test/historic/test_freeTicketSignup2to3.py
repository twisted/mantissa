
from axiom.test.historic import stubloader
from xmantissa.signup import FreeTicketSignup

class FreeTicketSignupTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        fts = self.store.findUnique(FreeTicketSignup)
        self.assertEqual(fts.prefixURL, '/a/b')
        self.assertEqual(fts.booth, self.store)
        self.assertEqual(fts.benefactor, self.store)
        # we are mostly interested in this
        self.failUnless(fts.emailTemplate)
