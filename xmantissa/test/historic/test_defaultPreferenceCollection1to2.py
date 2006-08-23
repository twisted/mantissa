
from axiom.test.historic import stubloader
from xmantissa.prefs import DefaultPreferenceCollection
from xmantissa.settings import Settings

class DefaultPreferenceCollectionTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        pc = self.store.findUnique(DefaultPreferenceCollection)
        self.assertEqual(pc.timezone, 'US/Eastern')
        self.failUnless(self.store.findUnique(Settings))
