
from axiom.test.historic import stubloader
from xmantissa.signup import FreeTicketSignup

from twisted.application.service import IService

class FreeTicketSignupTestCase(stubloader.StubbedTest):
    def setUp(self):
        stubloader.StubbedTest.setUp(self)
        self.service = IService(self.store)
        self.service.startService()
        return self.store.whenFullyUpgraded()


    def tearDown(self):
        return self.service.stopService()


    def testUpgrade(self):
        fts = self.store.findUnique(FreeTicketSignup)
        self.assertEqual(fts.prefixURL, '/a/b')
        self.assertEqual(fts.booth, self.store)
        self.assertEqual(fts.benefactor, self.store)
        # we are mostly interested in this
        self.failUnless(fts.emailTemplate)
