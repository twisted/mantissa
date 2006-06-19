
from twisted.trial import unittest

from xmantissa.search import parseSearchTerm


class QueryParseTestCase(unittest.TestCase):
    def testPlainTerm(self):
        """
        Test that a regular boring search query with nothing special is parsed
        as such.
        """
        self.assertEquals(parseSearchTerm(u"foo"), (u"foo", None))
        self.assertEquals(parseSearchTerm(u"foo bar"), (u"foo bar", None))


    def testKeywordTerm(self):
        """
        Test keywords in a search query are found and returned.
        """
        self.assertEquals(
            parseSearchTerm(u"foo:bar"),
            (u"", {u"foo": u"bar"}))
        self.assertEquals(
            parseSearchTerm(u"foo bar:baz"),
            (u"foo", {u"bar": u"baz"}))
        self.assertEquals(
            parseSearchTerm(u"foo bar baz:quux"),
            (u"foo bar", {u"baz": u"quux"}))
        self.assertEquals(
            parseSearchTerm(u"foo bar:baz quux"),
            (u"foo quux", {u"bar": u"baz"}))
        self.assertEquals(
            parseSearchTerm(u"foo bar:baz quux foobar:barbaz"),
            (u"foo quux", {u"bar": u"baz", u"foobar": u"barbaz"}))


    def testBadlyFormedKeywordTerm(self):
        """
        Test that a keyword search that isn't quite right gets cleaned up.
        """
        self.assertEquals(
            parseSearchTerm(u"foo:"),
            (u"foo", None))

        self.assertEquals(
            parseSearchTerm(u":foo"),
            (u"foo", None))

        self.assertEquals(
            parseSearchTerm(u":"),
            (u"", None))
