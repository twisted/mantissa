
from axiom.test.historic.stubloader import saveStub
from axiom.batch import processor

from xmantissa.fulltext import HypeIndexer, XapianIndexer, PyLuceneIndexer

def createDatabase(s):
    for cls in [HypeIndexer, XapianIndexer, PyLuceneIndexer]:
        indexer = cls(store=s)
        processor(cls)(store=s).addReliableListener(indexer)


if __name__ == '__main__':
    saveStub(createDatabase, 7053)
