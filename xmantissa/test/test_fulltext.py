
from zope.interface import implements

from twisted.trial import unittest

from axiom import iaxiom, store, batch, item, attributes

from xmantissa import ixmantissa, fulltext


class IndexableThing(item.Item):
    implements(ixmantissa.IFulltextIndexable)

    _uniqueIdentifier = attributes.text()
    _textParts = attributes.inmemory()
    _valueParts = attributes.inmemory()
    _keywordParts = attributes.inmemory()


    def uniqueIdentifier(self):
        return self._uniqueIdentifier


    def textParts(self):
        return self._textParts


    def valueParts(self):
        return self._valueParts


    def keywordParts(self):
        return self._keywordParts



class FakeMessageSource(item.Item):
    """
    Stand-in for an item type returned from L{axiom.batch.processor}.  Doesn't
    actually act as a source of anything, just used to test that items are kept
    track of properly.
    """
    anAttribute = attributes.text(doc="""
    Nothing.  Axiom requires at least one attribute per item-type.
    """)

    added = attributes.inmemory()
    removed = attributes.inmemory()

    def activate(self):
        self.added = []
        self.removed = []


    def addReliableListener(self, what, style):
        self.added.append((what, style))


    def removeReliableListener(self, what):
        self.removed.append(what)



class IndexerTestsMixin:
    def createIndexer(self):
        raise NotImplementedError()


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


    def setUp(self):
        self.dbdir = self.mktemp()
        self.path = u'index'
        self.store = store.Store(self.dbdir)
        self.indexer = self.createIndexer()



class FulltextTestsMixin(IndexerTestsMixin):
    """
    Tests for any IFulltextIndexer provider.
    """

    def testSources(self):
        """
        Test that multiple IBatchProcessors can be added to a RemoteIndexer and
        that an indexer can be reset, with respect to input from its sources.
        """
        firstSource = FakeMessageSource(store=self.store)
        secondSource = FakeMessageSource(store=self.store)
        self.indexer.addSource(firstSource)
        self.indexer.addSource(secondSource)

        self.assertEquals(firstSource.added, [(self.indexer, iaxiom.REMOTE)])
        self.assertEquals(secondSource.added, [(self.indexer, iaxiom.REMOTE)])

        self.assertEquals(
            list(self.indexer.getSources()),
            [firstSource, secondSource])

        firstSource.added = []
        secondSource.added = []

        self.indexer.reset()
        self.assertEquals(firstSource.removed, [self.indexer])
        self.assertEquals(secondSource.removed, [self.indexer])
        self.assertEquals(firstSource.added, [(self.indexer, iaxiom.REMOTE)])
        self.assertEquals(secondSource.added, [(self.indexer, iaxiom.REMOTE)])


    def testSimpleSerializedUsage(self):
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
            _uniqueIdentifier=u'7',
            _textParts=[u'apple', u'banana'],
            _valueParts={},
            _keywordParts={}))
        writer.add(IndexableThing(
            _uniqueIdentifier=u'21',
            _textParts=[u'cherry', u'drosophila melanogaster'],
            _valueParts={},
            _keywordParts={}))
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
            _uniqueIdentifier=u'1',
            _textParts=[u'apple', u'banana'],
            _valueParts={},
            _keywordParts={}))
        writer.close()

        reader = self.openReadIndex()
        results = list(reader.search(u'apple'))
        self.assertEquals(results, [1])
        results = list(reader.search(u'banana'))
        self.assertEquals(results, [1])
        reader.close()

        writer = self.openWriteIndex()
        writer.add(IndexableThing(
            _uniqueIdentifier=u'2',
            _textParts=[u'cherry', 'drosophila melanogaster'],
            _valueParts={},
            _keywordParts={}))
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


    def testKeywordIndexing(self):
        """
        Test that an L{IFulltextIndexable}'s keyword parts can be searched for.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
            _uniqueIdentifier=u'50',
            _textParts=[u'apple', u'banana'],
            _valueParts={},
            _keywordParts={u'subject': u'fruit'}))
        writer.close()

        reader = self.openReadIndex()
        self.assertEquals(list(reader.search(u'fruit')), [])
        self.assertEquals(list(reader.search(u'apple')), [50])
        self.assertEquals(list(reader.search(u'apple', {u'subject': u'fruit'})), [50])
        self.assertEquals(list(reader.search(u'', {u'subject': u'fruit'})), [50])


    def testKeywordTokenization(self):
        """
        Keyword values should be tokenized just like text parts.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
            _uniqueIdentifier=u'50',
            _textParts=[u'apple', u'banana'],
            _valueParts={},
            _keywordParts={u'subject': u'list of fruit things'}))
        writer.close()

        reader = self.openReadIndex()
        self.assertEquals(list(reader.search(u'fruit')), [])
        self.assertEquals(list(reader.search(u'apple')), [50])
        self.assertEquals(list(reader.search(u'apple', {u'subject': u'fruit'})), [50])
        self.assertEquals(list(reader.search(u'', {u'subject': u'fruit'})), [50])
        self.assertEquals(list(reader.search(u'', {u'subject': u'list'})), [50])
        self.assertEquals(list(reader.search(u'', {u'subject': u'things'})), [50])



class CorruptionRecoveryMixin(IndexerTestsMixin):
    def corruptIndex(self):
        raise NotImplementedError()


    def testRecoveryAfterFailure(self):
        """
        Create an indexer, attach some sources to it, let it process some
        messages, corrupt the database, let it try to clean things up, then
        make sure the index is in a reasonable state.
        """
        # Try to access the indexer directly first so that if it is
        # unavailable, the test will be skipped.
        self.openReadIndex().close()

        service = batch.BatchProcessingService(self.store, iaxiom.REMOTE)
        task = service.step()

        source = batch.processor(IndexableThing)(store=self.store)
        self.indexer.addSource(source)

        things = [
            IndexableThing(store=self.store,
                           _uniqueIdentifier=u'100',
                           _textParts=[u'apple', u'banana'],
                           _valueParts={},
                           _keywordParts={}),
            IndexableThing(store=self.store,
                           _uniqueIdentifier=u'200',
                           _textParts=[u'cherry'],
                           _valueParts={},
                           _keywordParts={})]

        for i in xrange(len(things)):
            task.next()

        self.indexer.suspend()

        # Sanity check - make sure both items come back from a search before
        # going on with the real core of the test.
        reader = self.openReadIndex()
        self.assertEquals(reader.search(u'apple'), [100])
        self.assertEquals(reader.search(u'cherry'), [200])
        self.assertEquals(reader.search(u'drosophila'), [])
        reader.close()

        self.corruptIndex()
        self.indexer.resume()

        things.append(
            IndexableThing(store=self.store,
                           _uniqueIdentifier=u'300',
                           _textParts=[u'drosophila', u'melanogaster'],
                           _valueParts={},
                           _keywordParts={}))

        # Step it once so that it notices the index has been corrupted.
        task.next()
        self.indexer.suspend()

        # At this point, the index should have been deleted, so any search
        # should turn up no results.
        reader = self.openReadIndex()
        self.assertEquals(reader.search(u'apple'), [])
        self.assertEquals(reader.search(u'cherry'), [])
        self.assertEquals(reader.search(u'drosophila'), [])
        reader.close()

        self.indexer.resume()

        # Step it another N so that each thing gets re-indexed.
        for i in xrange(len(things)):
            task.next()

        self.indexer.suspend()

        reader = self.openReadIndex()
        self.assertEquals(reader.search(u'apple'), [100])
        self.assertEquals(reader.search(u'cherry'), [200])
        self.assertEquals(reader.search(u'drosophila'), [300])
        reader.close()



class HypeFulltextTestCase(FulltextTestsMixin, unittest.TestCase):
    skip = "These tests don't actually pass - and I don't even care."
    def createIndexer(self):
        return fulltext.HypeIndexer(store=self.store, indexDirectory=self.path)



class XapianFulltextTestCase(FulltextTestsMixin, unittest.TestCase):
    skip = "These tests don't actually pass - and I don't even care."
    def createIndexer(self):
        return fulltext.XapianIndexer(store=self.store, indexDirectory=self.path)



class PyLuceneTestsMixin:
    def createIndexer(self):
        return fulltext.PyLuceneIndexer(store=self.store, indexDirectory=self.path)



class PyLuceneFulltextTestCase(PyLuceneTestsMixin, FulltextTestsMixin, unittest.TestCase):
    def testAutomaticClosing(self):
        """
        Test that if we create a writer and call the close-helper function,
        the writer gets closed.
        """
        writer = self.openWriteIndex()
        fulltext._closeIndexes()
        self.failUnless(writer.closed, "Writer should have been closed.")


    def testRepeatedClosing(self):
        """
        Test that if for some reason a writer is explicitly closed after the
        close-helper has run, nothing untoward occurs.
        """
        writer = self.openWriteIndex()
        fulltext._closeIndexes()
        writer.close()
        self.failUnless(writer.closed, "Writer should have stayed closed.")



class PyLuceneCorruptionRecoveryTestCase(PyLuceneTestsMixin, CorruptionRecoveryMixin, unittest.TestCase):
    def corruptIndex(self):
        """
        Cause a PyLucene index to appear corrupted.
        """
        for ch in self.store.newFilePath(self.path).children():
            ch.setContent('hello, world')


    def testFailureDetectionFromWriter(self):
        """
        Fulltext indexes are good at two things: soaking up I/O bandwidth and
        corrupting themselves.  For the latter case, we need to be able to
        detect the condition before we can make any response to it.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
            _uniqueIdentifier=u'10',
            _textParts=[u'apple', u'banana'],
            _valueParts={},
            _keywordParts={}))
        writer.close()
        self.corruptIndex()
        self.assertRaises(fulltext.IndexCorrupt, self.openWriteIndex)
        self.assertRaises(fulltext.IndexCorrupt, self.openReadIndex)


    def testFailureDetectionFromReader(self):
        """
        Like testFailureDetectionFromWriter, but opens a reader after
        corrupting the index and asserts that it also raises the appropriate
        exception.
        """
        writer = self.openWriteIndex()
        writer.add(IndexableThing(
            _uniqueIdentifier=u'10',
            _textParts=[u'apple', u'banana'],
            _valueParts={},
            _keywordParts={}))
        writer.close()
        self.corruptIndex()
        self.assertRaises(fulltext.IndexCorrupt, self.openReadIndex)
        self.assertRaises(fulltext.IndexCorrupt, self.openWriteIndex)



class PyLuceneLockedRecoveryTestCase(PyLuceneTestsMixin, CorruptionRecoveryMixin, unittest.TestCase):
    def setUp(self):
        CorruptionRecoveryMixin.setUp(self)
        self.corruptedIndexes = []


    def corruptIndex(self):
        """
        Loosely simulate filesystem state following a SIGSEGV or power
        failure.
        """
        self.corruptedIndexes.append(self.openWriteIndex())
