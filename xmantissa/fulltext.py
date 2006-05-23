# -*- test-case-name: xmantissa.test.test_fulltext -*-

"""
General functionality re-usable by various concrete fulltext indexing systems.
"""

import atexit

from zope.interface import implements

from twisted.python import log
from twisted.internet import defer, reactor

from axiom import item, attributes, iaxiom

from xmantissa import ixmantissa

HYPE_INDEX_DIR = u'hype.index'
XAPIAN_INDEX_DIR = u'xap.index'
LUCENE_INDEX_DIR = u'lucene.index'

VERBOSE = True

class RemoteIndexer(item.InstallableMixin):
    """
    Implements most of a full-text indexer.

    This uses L{axiom.batch} to perform indexing out of process and presents an
    asynchronous interface to in-process searching of that indexing.
    """
    implements(iaxiom.IReliableListener, ixmantissa.ISearchProvider)


    def openReadIndex(self):
        raise NotImplementedError


    def openWriteIndex(self):
        raise NotImplementedError


    def __finalizer__(self):
        d = self.__dict__
        id = self.storeID
        s = self.store
        def finalize():
            idx = d.get('_index', None)
            if idx is not None:
                if VERBOSE:
                    log.msg("Closing %r from finalizer of %s/%d" % (idx, s, id))
                idx.close()
        return finalize


    def activate(self):
        assert not hasattr(self, '_index')
        self._index = None
        if VERBOSE:
            log.msg("Activating %s/%d with null index" % (self.store, self.storeID))


    def _closeIndex(self):
        if VERBOSE:
            log.msg("%s/%d closing index" % (self.store, self.storeID))
        if self._index is not None:
            if VERBOSE:
                log.msg("%s/%d *really* closing index" % (self.store, self.storeID))
            self._index.close()
            self._index = None


    # IReliableListener
    def suspend(self):
        if VERBOSE:
            log.msg("%s/%d suspending" % (self.store, self.storeID))
        self._closeIndex()
        return defer.succeed(None)


    def resume(self):
        if VERBOSE:
            log.msg("%s/%d resuming" % (self.store, self.storeID))
        return defer.succeed(None)


    def processItem(self, item):
        reactor.callLater(10, lambda: self)

        if self._index is None:
            self._index = self.openWriteIndex()
            if VERBOSE:
                log.msg("Opened %s %s/%d for writing" % (self._index, self.store, self.storeID))

        if VERBOSE:
            log.msg("%s/%d indexing document" % (self.store, self.storeID))
        self._index.add(ixmantissa.IFulltextIndexable(item))
        self.indexCount += 1


    # ISearchablemumblkelkjaeroiutr28u3
    def search(self, aString, count=None, offset=None, retry=3):
        b = iaxiom.IBatchService(self.store)
        if VERBOSE:
            log.msg("%s/%d issueing suspend" % (self.store, self.storeID))
        d = b.suspend(self.storeID)

        def reallySearch(ign):
            if VERBOSE:
                log.msg("%s/%d getting reader index" % (self.store, self.storeID))
            idx = self.openReadIndex()
            try:
                if VERBOSE:
                    log.msg("%s/%d searching for %s" % (self.store, self.storeID, aString))
                results = list(idx.search(aString.encode('utf-8')))
                if VERBOSE:
                    log.msg("%s/%d found %d results" % (self.store, self.storeID, len(results)))
                if count is not None and offset is not None:
                    results = results[offset:offset + count]
                    if VERBOSE:
                        log.msg("%s/%d sliced from %s to %s, leaving %d results" % (self.store, self.storeID, offset, offset + count, len(results)))
                return results
            finally:
                idx.close()
        d.addCallback(reallySearch)

        def resumeIndexing(results):
            if VERBOSE:
                log.msg("%s/%s issueing resume" % (self.store, self.storeID))
            b.resume(self.storeID).addErrback(log.err)
            return results
        d.addBoth(resumeIndexing)

        def searchFailed(err):
            log.msg("Search failed somehow:")
            log.err(err)
            if retry:
                log.msg("Re-issuing search")
                return self.search(aString, count, offset, retry=retry-1)
            else:
                log.msg("Wow, lots of failures searching.  Giving up and returning (probably wrong!) no results to user.")
                return []
        d.addErrback(searchFailed)
        return d



try:
    import hype
except ImportError:
    hype = None

class _HypeIndex(object):
    def __init__(self, index):
        self.index = index
        self.close = index.close


    def add(self, message):
        doc = hype.Document()
        for (k, v) in message.valueParts():
            doc.add_hidden_text(v.encode('utf-8'))
        doc['@uri'] = message.uniqueIdentifier()

        for part in message.textParts():
            doc.add_text(part.encode('utf-8'))

        self.index.put_doc(doc)


    def search(self, term):
        return [int(d.uri) for d in self.index.search(term)]



class HypeIndexer(RemoteIndexer, item.Item):

    indexCount = attributes.integer(default=0)
    installedOn = attributes.reference()
    indexDirectory = attributes.text(default=HYPE_INDEX_DIR)

    _index = attributes.inmemory()

    if hype is None:
        def openReadIndex(self):
            raise NotImplementedError("hype is unavailable")


        def openWriteIndex(self):
            raise NotImplementedError("hype is unavailable")
    else:
        def openReadIndex(self):
            hypedir = self.store.newDirectory(self.indexDirectory)
            return _HypeIndex(hype.Database(hypedir.path, hype.ESTDBREADER | hype.ESTDBLCKNB | hype.ESTDBCREAT))


        def openWriteIndex(self):
            hypedir = self.store.newDirectory(self.indexDirectory)
            return _HypeIndex(hype.Database(hypedir.path, hype.ESTDBWRITER | hype.ESTDBCREAT))



from xapwrap import index, document

class _XapianIndex(object):
    def __init__(self, smartIndex):
        self.smartIndex = smartIndex
        self.close = smartIndex.close


    def add(self, message):
        textFields = []
        for part in message.textParts():
            textFields.append(document.TextField(part.encode('utf-8')))

        values = [
            document.Value(k, v.encode('utf-8'))
            for (k, v)
            in message.valueParts()
            ]

        keywords = [
            document.Keyword(k, v.encode('utf-8'))
            for (k, v)
            in message.keywordParts()]

        self.smartIndex.index(
            document.Document(textFields=textFields,
                              values=values,
                              keywords=keywords,
                              uid=message.uniqueIdentifier()))


    def search(self, term):
        return [d['uid'] for d in self.smartIndex.search(term.encode('utf-8'))]



class XapianIndexer(RemoteIndexer, item.Item):

    indexCount = attributes.integer(default=0)
    installedOn = attributes.reference()
    indexDirectory = attributes.text(default=XAPIAN_INDEX_DIR)

    _index = attributes.inmemory()

    def openReadIndex(self):
        xapDir = self.store.newDirectory(self.indexDirectory)
        if not xapDir.exists():
            self.openWriteIndex().close()
        return _XapianIndex(index.SmartReadOnlyIndex(str(xapDir.path)))

    def openWriteIndex(self):
        xapDir = self.store.newDirectory(self.indexDirectory)
        return _XapianIndex(index.SmartIndex(str(xapDir.path), True))



try:
    import PyLucene
except ImportError:
    PyLucene = None

class _PyLuceneIndex(object):
    def __init__(self, fsdir, index, analyzer):
        self.fsdir = fsdir
        self.index = index
        _closeObjects.append(self)
        self.analyzer = analyzer


    def add(self, message):
        doc = PyLucene.Document()
        for part in message.textParts():
            doc.add(
                PyLucene.Field.Text('text', part.encode('utf-8')))
        doc.add(
            PyLucene.Field('storeID',
                           message.uniqueIdentifier(),
                           PyLucene.Field.Store.YES,
                           PyLucene.Field.Index.UN_TOKENIZED))
        # Deprecated. use Field(name, value, Field.Store.YES, Field.Index.UN_TOKENIZED) instead
        self.index.addDocument(doc)


    def search(self, phrase):
        query = PyLucene.QueryParser.parse(phrase, 'text', self.analyzer)
        hits = self.index.search(query)
        return [int(h.get('storeID')) for (n, h) in hits]


    closed = False
    def close(self):
        if not self.closed:
            self.index.close()
            self.fsdir.close()
        self.closed = True
        try:
            _closeObjects.remove(self)
        except ValueError:
            pass


_closeObjects = []
def _closeIndexes():
    """
    Helper for _PyLuceneIndex to make sure FSDirectory and IndexWriter
    instances always get closed.  This gets registered with atexit and
    closes any _PyLuceneIndex objects still in _closeObjects when it gets
    run.
    """
    global _closeObjects
    for o in _closeObjects:
        o.close()
    _closeObjects = []
atexit.register(_closeIndexes)


class PyLuceneIndexer(RemoteIndexer, item.Item):

    indexCount = attributes.integer(default=0)
    installedOn = attributes.reference()
    indexDirectory = attributes.text(default=LUCENE_INDEX_DIR)

    _index = attributes.inmemory()


    def _analyzer(self):
        return PyLucene.SimpleAnalyzer()


    def _setLockDirectory(self):
        lockdir = self.store.newTemporaryFilePath('lucene-locks')
        if not lockdir.exists():
            lockdir.makedirs()
        # Is Lucene really so bad that I actually have to do this?  I hope not
        # but I can't see any other way. - exarkun

        # XXX Actually this doesn't do anything at all, apparently. - exarkun
        PyLucene.FSDirectory.LOCK_DIR = lockdir.path


    if PyLucene is None:
        def openReadIndex(self):
            raise NotImplementedError("PyLucene is unavailable")


        def openWriteIndex(self):
            raise NotImplementedError("PyLucene is unavailable")
    else:
        def openReadIndex(self):
            luceneDir = self.store.newDirectory(self.indexDirectory)

            self._setLockDirectory()

            if not luceneDir.exists():
                self.openWriteIndex().close()

            fsdir = PyLucene.FSDirectory.getDirectory(luceneDir.path, False)
            return _PyLuceneIndex(fsdir, PyLucene.IndexSearcher(fsdir), self._analyzer())


        def openWriteIndex(self):
            self._setLockDirectory()

            luceneDir = self.store.newDirectory(self.indexDirectory)

            create = not luceneDir.exists()

            fsdir = PyLucene.FSDirectory.getDirectory(luceneDir.path, create)
            analyzer = self._analyzer()

            # XXX TODO - Creating an IndexWriter might fail with an error
            # acquiring the write lock.  This should only ever be possible
            # after a hardware crash or some other unclean shutdown of the
            # batch process.  If it does happen, though, we probably need to
            # delete the Lucene index and recreate it.
            return _PyLuceneIndex(
                fsdir,
                PyLucene.IndexWriter(fsdir, analyzer, create),
                analyzer)
