# -*- test-case-name: xmantissa.test.test_fulltext -*-

"""
General functionality re-usable by various concrete fulltext indexing systems.
"""

import atexit, os, time, weakref

from zope.interface import implements

from twisted.python import log, reflect
from twisted.internet import defer

from epsilon.structlike import record

from axiom import item, attributes, iaxiom, batch
from axiom.upgrade import registerUpgrader

from xmantissa import ixmantissa

HYPE_INDEX_DIR = u'hype.index'
XAPIAN_INDEX_DIR = u'xap.index'
LUCENE_INDEX_DIR = u'lucene.index'

VERBOSE = True

class IndexCorrupt(Exception):
    """
    An attempt was made to open an index which has had unrecoverable data
    corruption.
    """



class _IndexerInputSource(item.Item):
    """
    Tracks L{IBatchProcessor}s which have had an indexer added to them as a
    listener.
    """
    indexer = attributes.reference(doc="""
    The indexer item with which this input source is associated.
    """, whenDeleted=attributes.reference.CASCADE)

    source = attributes.reference(doc="""
    The L{IBatchProcessor} which acts as the input source.
    """, whenDeleted=attributes.reference.CASCADE)



class RemoteIndexer(item.InstallableMixin):
    """
    Implements most of a full-text indexer.

    This uses L{axiom.batch} to perform indexing out of process and presents an
    asynchronous interface to in-process searching of that indexing.
    """
    implements(iaxiom.IReliableListener, ixmantissa.ISearchProvider)


    def openReadIndex(self):
        """
        Return an object usable to search this index.

        Subclasses should implement this.
        """
        raise NotImplementedError


    def openWriteIndex(self):
        """
        Return an object usable to add documents to this index.

        Subclasses should implement this.
        """
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


    def addSource(self, itemSource):
        """
        Add the given L{IBatchProcessor} as a source of input for this indexer.
        """
        _IndexerInputSource(store=self.store, indexer=self, source=itemSource)
        itemSource.addReliableListener(self, style=iaxiom.REMOTE)


    def getSources(self):
        return self.store.query(_IndexerInputSource, _IndexerInputSource.indexer == self).getColumn("source")


    def reset(self):
        """
        Process everything all over again.
        """
        self.indexCount = 0
        indexDir = self.store.newDirectory(self.indexDirectory)
        if indexDir.exists():
            indexDir.remove()
        for src in self.getSources():
            src.removeReliableListener(self)
            src.addReliableListener(self, style=iaxiom.REMOTE)


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
        if self._index is None:
            try:
                self._index = self.openWriteIndex()
            except IndexCorrupt:
                self.reset()
                return

            if VERBOSE:
                log.msg("Opened %s %s/%d for writing" % (self._index, self.store, self.storeID))

        if VERBOSE:
            log.msg("%s/%d indexing document" % (self.store, self.storeID))
        self._index.add(ixmantissa.IFulltextIndexable(item))
        self.indexCount += 1


    # ISearchProvider
    def search(self, aString, keywords=None, count=None, offset=None, retry=3):
        ident = "%s/%d" % (self.store, self.storeID)
        b = iaxiom.IBatchService(self.store)
        if VERBOSE:
            log.msg("%s issuing suspend" % (ident,))
        d = b.suspend(self.storeID)

        def reallySearch(ign):
            if VERBOSE:
                log.msg("%s getting reader index" % (ident,))
            idx = self.openReadIndex()

            if VERBOSE:
                log.msg("%s searching for %s" % (ident, aString))
            results = idx.search(aString.encode('utf-8'), keywords)
            if VERBOSE:
                log.msg("%s found %d results" % (ident, len(results)))
            if count is not None and offset is not None:
                results = results[offset:offset + count]
                if VERBOSE:
                    log.msg("%s sliced from %s to %s, leaving %d results" % (
                            ident, offset, offset + count, len(results)))
            return results

        d.addCallback(reallySearch)

        def resumeIndexing(results):
            if VERBOSE:
                log.msg("%s issuing resume" % (ident,))
            b.resume(self.storeID).addErrback(log.err)
            return results
        d.addBoth(resumeIndexing)

        def searchFailed(err):
            log.msg("Search failed somehow:")
            log.err(err)
            if retry:
                log.msg("Re-issuing search")
                return self.search(aString, keywords, count, offset, retry=retry-1)
            else:
                log.msg("Wow, lots of failures searching.  Giving up and "
                        "returning (probably wrong!) no results to user.")
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


    def search(self, term, keywords=None):
        return [int(d.uri) for d in self.index.search(term)]



class HypeIndexer(RemoteIndexer, item.Item):

    schemaVersion = 3

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


    def search(self, term, keywords=None):
        return [d['uid'] for d in self.smartIndex.search(term.encode('utf-8'))]



class XapianIndexer(RemoteIndexer, item.Item):

    schemaVersion = 3

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


_hitsWrapperWeakrefs = weakref.WeakKeyDictionary()

class _PyLuceneHitsWrapper(record('index hits')):
    """
    Container for a C{Hits} instance and the L{_PyLuceneIndex} from which it
    came.  This gives the C{Hits} instance a sequence-like interface and when a
    _PyLuceneHitsWrapper is garbage collected, it closes the L{_PyLuceneIndex}
    it has a reference to.
    """
    def __init__(self, *a, **kw):
        super(_PyLuceneHitsWrapper, self).__init__(*a, **kw)

        def close(ref, index=self.index):
            log.msg("Hits wrapper expiring, closing index.")
            index.close()
        _hitsWrapperWeakrefs[self] = weakref.ref(self, close)


    def __len__(self):
        return len(self.hits)


    def __getitem__(self, index):
        """
        Retrieve the storeID field of the requested hit, converting it to an
        integer before returning it.  This handles integer indexes as well as
        slices.
        """
        if isinstance(index, slice):
            start = min(index.start, len(self) - 1)
            if index.stop is None:
                if index.step == -1:
                    stop = -1
                else:
                    stop = len(self) - 1
            else:
                stop = min(index.stop, len(self) - 1)
            return [self[i] for i in xrange(start, stop, index.step)]
        if index >= len(self.hits):
            raise IndexError(index)
        return int(self.hits[index]['storeID'])



class _PyLuceneIndex(object):
    def __init__(self, fsdir, index, analyzer):
        self.fsdir = fsdir
        self.index = index
        _closeObjects.append(self)
        self.analyzer = analyzer


    def add(self, message):
        doc = PyLucene.Document()

        for (k, v) in message.keywordParts().iteritems():
            for k in (k, 'text'):
                doc.add(
                    PyLucene.Field(k, v,
                                PyLucene.Field.Store.YES,
                                PyLucene.Field.Index.TOKENIZED))
        doc.add(
            PyLucene.Field('documentType', message.documentType(),
                           PyLucene.Field.Store.YES,
                           PyLucene.Field.Index.TOKENIZED))

        for text in message.textParts():
            doc.add(
                PyLucene.Field('text', text.encode('utf-8'),
                            PyLucene.Field.Store.NO,
                            PyLucene.Field.Index.TOKENIZED))
        doc.add(
            PyLucene.Field('storeID',
                           message.uniqueIdentifier(),
                           PyLucene.Field.Store.YES,
                           PyLucene.Field.Index.UN_TOKENIZED))
        # Deprecated. use Field(name, value, Field.Store.YES, Field.Index.UN_TOKENIZED) instead

        self.index.addDocument(doc)


    def search(self, phrase, keywords=None):
        if not phrase and not keywords:
            return []

        # XXX Colons in phrase will screw stuff up.  Can they be quoted or
        # escaped somehow?  Probably by using a different QueryParser.
        if keywords:
            fieldPhrase = u' '.join(u':'.join((k, v)) for (k, v) in keywords.iteritems())
            if phrase:
                phrase = phrase + u' ' + fieldPhrase
            else:
                phrase = fieldPhrase

        qp = PyLucene.QueryParser('text', self.analyzer)
        qp.setDefaultOperator(qp.Operator.AND)
        query = qp.parseQuery(phrase)

        hits = self.index.search(query)
        return _PyLuceneHitsWrapper(self, hits)


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
    while _closeObjects:
        _closeObjects[-1].close()
atexit.register(_closeIndexes)


class PyLuceneIndexer(RemoteIndexer, item.Item):

    schemaVersion = 3

    indexCount = attributes.integer(default=0)
    installedOn = attributes.reference()
    indexDirectory = attributes.text(default=LUCENE_INDEX_DIR)

    _index = attributes.inmemory()
    _lockfile = attributes.inmemory()


    def reset(self):
        """
        In addition to the behavior of the superclass, delete any dangling
        lockfiles which may prevent this index from being opened.  With the
        tested version of PyLucene (something pre-2.0), this appears to not
        actually be necessary: deleting the entire index directory but
        leaving the lockfile in place seems to still allow the index to be
        recreated (perhaps because when the directory does not exist, we
        pass True as the create flag when opening the FSDirectory, I am
        uncertain).  Nevertheless, do this anyway for now.
        """
        RemoteIndexer.reset(self)
        if hasattr(self, '_lockfile'):
            os.remove(self._lockfile)
            del self._lockfile


    def _analyzer(self):
        return PyLucene.StandardAnalyzer([])


    if PyLucene is None:
        def openReadIndex(self):
            raise NotImplementedError("PyLucene is unavailable")


        def openWriteIndex(self):
            raise NotImplementedError("PyLucene is unavailable")
    else:
        def openReadIndex(self):
            luceneDir = self.store.newDirectory(self.indexDirectory)


            if not luceneDir.exists():
                self.openWriteIndex().close()

            fsdir = PyLucene.FSDirectory.getDirectory(luceneDir.path, False)
            try:
                reader = PyLucene.IndexSearcher(fsdir)
            except PyLucene.JavaError, e:
                raise IndexCorrupt()
            else:
                return _PyLuceneIndex(fsdir, reader, self._analyzer())


        def openWriteIndex(self):
            luceneDir = self.store.newDirectory(self.indexDirectory)


            create = not luceneDir.exists()

            analyzer = self._analyzer()

            fsdir = PyLucene.FSDirectory.getDirectory(luceneDir.path, create)
            try:
                writer = PyLucene.IndexWriter(fsdir, analyzer, create)
            except PyLucene.JavaError, e:
                lockTimeout = u'Lock obtain timed out: Lock@'
                msg = e.getJavaException().getMessage()
                if msg.startswith(lockTimeout):
                    self._lockfile = msg[len(lockTimeout):]
                raise IndexCorrupt()
            return _PyLuceneIndex(fsdir, writer, analyzer)



def remoteIndexer1to2(oldIndexer):
    """
    Previously external application code was responsible for adding a
    RemoteListener to a batch work source as a reliable listener.  This
    precluded the possibility of the RemoteListener resetting itself
    unilaterally.  With version 2, RemoteListener takes control of adding
    itself as a reliable listener and keeps track of the sources with which it
    is associated.  This upgrader creates that tracking state.
    """
    newIndexer = oldIndexer.upgradeVersion(
        oldIndexer.typeName, 1, 2,
        indexCount=oldIndexer.indexCount,
        installedOn=oldIndexer.installedOn,
        indexDirectory=oldIndexer.indexDirectory)

    listeners = newIndexer.store.query(
        batch._ReliableListener,
        batch._ReliableListener.listener == newIndexer)

    for listener in listeners:
        _IndexerInputSource(
            store=newIndexer.store,
            indexer=newIndexer,
            source=listener.processor)

    return newIndexer

def remoteIndexer2to3(oldIndexer):
    """
    The documentType keyword was added to all indexable items.  Indexes need to
    be regenerated for this to take effect.  Also, PyLucene no longer stores
    the text of messages it indexes, so deleting and re-creating the indexes
    will make them much smaller.
    """
    newIndexer = oldIndexer.upgradeVersion(
        oldIndexer.typeName, 2, 3,
        indexCount=oldIndexer.indexCount,
        installedOn=oldIndexer.installedOn,
        indexDirectory=oldIndexer.indexDirectory)
    newIndexer.reset()
    return newIndexer


for cls in [HypeIndexer, XapianIndexer, PyLuceneIndexer]:
    item.declareLegacyItem(
        cls.typeName, 2,
        dict(indexCount=attributes.integer(),
             installedOn=attributes.reference(),
             indexDirectory=attributes.text()))

    registerUpgrader(
        remoteIndexer1to2,
        item.normalize(reflect.qual(cls)),
        1,
        2)
    registerUpgrader(
        remoteIndexer2to3,
        item.normalize(reflect.qual(cls)),
        2,
        3)
del cls
