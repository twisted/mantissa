
from axiom.test.historic.stubloader import StubbedTest
from axiom.batch import processor

from xmantissa.fulltext import HypeIndexer, XapianIndexer, PyLuceneIndexer

hypeProcessor = processor(HypeIndexer)
xapianProcessor = processor(XapianIndexer)
pyluceneProcessor = processor(PyLuceneIndexer)

class RemoteIndexerTestCase(StubbedTest):
    def testUpgradeHype(self):
        indexer = self.store.findUnique(HypeIndexer)
        self.assertEquals(
            [self.store.findUnique(hypeProcessor)],
            list(indexer.getSources()))


    def testUpgradeXapian(self):
        indexer = self.store.findUnique(XapianIndexer)
        self.assertEquals(
            [self.store.findUnique(xapianProcessor)],
            list(indexer.getSources()))


    def testUpgradePyLucene(self):
        indexer = self.store.findUnique(PyLuceneIndexer)
        self.assertEquals(
            [self.store.findUnique(pyluceneProcessor)],
            list(indexer.getSources()))
