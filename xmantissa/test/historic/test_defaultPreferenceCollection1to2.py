
from axiom.test.historic import stubloader
from xmantissa.prefs import DefaultPreferenceCollection
from xmantissa.settings import Settings

from twisted.application.service import IService

class DefaultPreferenceCollectionTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        s = self.store
        svc = IService(s)
        svc.startService()
        D = s.whenFullyUpgraded()
        def txn(_):
            pc = s.findUnique(DefaultPreferenceCollection)
            self.assertEqual(pc.timezone, 'US/Eastern')
            self.failUnless(s.findUnique(Settings))
        return D.addCallback(txn)
