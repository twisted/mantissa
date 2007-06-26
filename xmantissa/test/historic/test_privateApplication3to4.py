
"""
Tests for the upgrade of L{PrivateApplication} schema from 3 to 4.
"""

from axiom.test.historic.stubloader import StubbedTest

from xmantissa.ixmantissa import ITemplateNameResolver
from xmantissa.website import WebSite
from xmantissa.webapp import PrivateApplication
from xmantissa.publicweb import CustomizedPublicPage
from xmantissa.webgestalt import AuthenticationApplication
from xmantissa.prefs import PreferenceAggregator, DefaultPreferenceCollection
from xmantissa.search import SearchAggregator

from xmantissa.test.historic.stub_privateApplication3to4 import (
    PREFERRED_THEME, HIT_COUNT, PRIVATE_KEY)

class PrivateApplicationUpgradeTests(StubbedTest):
    """
    Tests for L{xmantissa.webapp.privateApplication3to4}.
    """
    def test_powerup(self):
        """
        At version 4, L{PrivateApplication} should be an
        L{ITemplateNameResolver} powerup on its store.
        """
        application = self.store.findUnique(PrivateApplication)
        powerups = list(self.store.powerupsFor(ITemplateNameResolver))
        self.assertIn(application, powerups)


    def test_attributes(self):
        """
        All of the attributes of L{PrivateApplication} should have the same
        values on the upgraded item as they did before the upgrade.
        """
        application = self.store.findUnique(PrivateApplication)
        self.assertEqual(application.preferredTheme, PREFERRED_THEME)
        self.assertEqual(application.hitCount, HIT_COUNT)
        self.assertEqual(application.privateKey, PRIVATE_KEY)

        website = self.store.findUnique(WebSite)
        self.assertIdentical(application.website, website)

        customizedPublicPage = self.store.findUnique(CustomizedPublicPage)
        self.assertIdentical(
            application.customizedPublicPage, customizedPublicPage)

        authenticationApplication = self.store.findUnique(
            AuthenticationApplication)
        self.assertIdentical(
            application.authenticationApplication, authenticationApplication)

        preferenceAggregator = self.store.findUnique(PreferenceAggregator)
        self.assertIdentical(
            application.preferenceAggregator, preferenceAggregator)

        defaultPreferenceCollection = self.store.findUnique(
            DefaultPreferenceCollection)
        self.assertIdentical(
            application.defaultPreferenceCollection,
            defaultPreferenceCollection)

        searchAggregator = self.store.findUnique(SearchAggregator)
        self.assertIdentical(application.searchAggregator, searchAggregator)

        self.assertIdentical(application.privateIndexPage, None)
