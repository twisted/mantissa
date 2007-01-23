from axiom.test.historic import stubloader
from xmantissa.publicweb import CustomizedPublicPage
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite
from xmantissa.webgestalt import AuthenticationApplication
from xmantissa.prefs import PreferenceAggregator, DefaultPreferenceCollection
from xmantissa.search import SearchAggregator


class PATestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        """
        Ensure upgraded fields refer to correct items.
        """
        pa = self.store.findUnique(PrivateApplication)
        self.assertEqual(pa.customizedPublicPage, pa.store.findUnique(CustomizedPublicPage))
        self.assertEqual(pa.authenticationApplication, pa.store.findUnique(AuthenticationApplication))
        self.assertEqual(pa.preferenceAggregator, pa.store.findUnique(PreferenceAggregator))
        self.assertEqual(pa.defaultPreferenceCollection, pa.store.findUnique(DefaultPreferenceCollection))
        self.assertEqual(pa.searchAggregator, pa.store.findUnique(SearchAggregator))
        self.assertEqual(pa.website, pa.store.findUnique(WebSite))
