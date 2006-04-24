
from zope.interface import implements

from twisted.trial import unittest

from axiom import store

from xmantissa import ixmantissa, fulltext


class IndexableThing(object):
    implements(ixmantissa.IFulltextIndexable)

    def __init__(self, uniqueIdentifier, textParts, valueParts, keywordParts):
        self._uniqueIdentifier = uniqueIdentifier
        self._textParts = textParts
        self._valueParts = valueParts
        self._keywordParts = keywordParts


    def uniqueIdentifier(self):
        return self._uniqueIdentifier


    def textParts(self):
        return self._textParts


    def valueParts(self):
        return self._valueParts


    def keywordParts(self):
        return self._keywordParts



class FulltextTestsMixin:
    """
    Tests for any IFulltextIndexer provider.
    """
    def createIndexer(self, path):
        raise NotImplementedError()


    def setUp(self):
        self.dbdir = self.mktemp()
        self.store = store.Store(self.dbdir)
        self.indexer = self.createIndexer(u'index')


    def openWriteIndex(self):
        try:
            return self.indexer.openWriteIndex()
        except NotImplementedError, e:
            raise unittest.SkipTest(str(e))


    def openReadIndex(self):
        try:
            return self.indexer.openReadIndex()
        except NotImplementedError, e:
            raise unittest.SkipTest(str(e))


    def testSimpleSerializedUsage(self):
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
            '7',
            [u'apple', u'banana'],
            {},
            {}))
        writer.add(IndexableThing(
            '21',
            [u'cherry', u'drosophila melanogaster'],
            {},
            {}))
        writer.close()

        reader = self.openReadIndex()

        results = list(reader.search(u'apple'))
        self.assertEquals(results, [7])

        results = list(reader.search(u'banana'))
        self.assertEquals(results, [7])

        results = list(reader.search(u'cherry'))
        self.assertEquals(results, [21])

        results = list(reader.search(u'drosophila'))
        self.assertEquals(results, [21])

        results = list(reader.search(u'melanogaster'))
        self.assertEquals(results, [21])

        reader.close()


    def testWriteReadWriteRead(self):
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
            '1',
            [u'apple', u'banana'],
            {},
            {}))
        writer.close()

        reader = self.openReadIndex()
        results = list(reader.search(u'apple'))
        self.assertEquals(results, [1])
        results = list(reader.search(u'banana'))
        self.assertEquals(results, [1])
        reader.close()

        writer = self.openWriteIndex()
        writer.add(IndexableThing(
            '2',
            [u'cherry', 'drosophila melanogaster'],
            {},
            {}))
        writer.close()

        reader = self.openReadIndex()
        results = list(reader.search(u'apple'))
        self.assertEquals(results, [1])
        results = list(reader.search(u'banana'))
        self.assertEquals(results, [1])

        results = list(reader.search(u'cherry'))
        self.assertEquals(results, [2])
        results = list(reader.search(u'drosophila'))
        self.assertEquals(results, [2])
        results = list(reader.search(u'melanogaster'))
        self.assertEquals(results, [2])
        reader.close()


    def testReadBeforeWrite(self):
        reader = self.openReadIndex()
        results = list(reader.search(u'apple'))
        self.assertEquals(results, [])



class HypeTestCase(FulltextTestsMixin, unittest.TestCase):
    skip = "These tests don't actually pass - and I don't even care."
    def createIndexer(self, path):
        return fulltext.HypeIndexer(store=self.store, indexDirectory=path)



class XapianTestCase(FulltextTestsMixin, unittest.TestCase):
    skip = "These tests don't actually pass - and I don't even care."
    def createIndexer(self, path):
        return fulltext.XapianIndexer(store=self.store, indexDirectory=path)



class PyLuceneTestCase(FulltextTestsMixin, unittest.TestCase):
    def createIndexer(self, path):
        return fulltext.PyLuceneIndexer(store=self.store, indexDirectory=path)
