
from axiom.test.historic import stubloader
from xmantissa.prefs import DefaultPreferenceCollection
from xmantissa.settings import Settings

from twisted.application.service import IService

class DefaultPreferenceCollectionTestCase(stubloader.StubbedTest):
    def setUp(self):
        stubloader.StubbedTest.setUp(self)
        self.service = IService(self.store)
        self.service.startService()
        return self.store.whenFullyUpgraded()


    def tearDown(self):
        return self.service.stopService()


    def testUpgrade(self):
        pc = self.store.findUnique(DefaultPreferenceCollection)
        self.assertEqual(pc.timezone, 'US/Eastern')
        self.failUnless(self.store.findUnique(Settings))
