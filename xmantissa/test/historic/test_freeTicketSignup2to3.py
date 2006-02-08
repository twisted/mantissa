
from axiom.test.historic import stubloader
from xmantissa.signup import FreeTicketSignup

from twisted.application.service import IService

class FreeTicketSignupTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        s = self.store
        svc = IService(s)
        svc.startService()
        D = s.whenFullyUpgraded()
        def txn(_):
            fts = s.findUnique(FreeTicketSignup)
            self.assertEqual(fts.prefixURL, '/a/b')
            self.assertEqual(fts.booth, s)
            self.assertEqual(fts.benefactor, s)
            # we are mostly interested in this
            self.failUnless(fts.emailTemplate)
        return D.addCallback(txn)
