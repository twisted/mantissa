from zope.interface import implements
from xmantissa import search, ixmantissa
from axiom.item import Item
from axiom.store import Store
from axiom import attributes
from twisted.trial.unittest import TestCase

def makeSearchProvider(results):
    # results = dict of {term:list of SearchResult instances}

    class SomeSearchProvider(Item):
        implements(ixmantissa.ISearchProvider)

        schemaVersion = 1
        typeName = 'some_search_provider'

        installedOn = attributes.reference()

        def installOn(self, other):
            assert self.installedOn is None
            other.powerUp(self, ixmantissa.ISearchProvider)
            self.installedOn = other

        def count(self, term):
            return len(results.get(term, ()))

        def search(self, term, count, offset):
            if term in results:
                return results[term][offset:count+offset]
            return []

    return SomeSearchProvider

class SearchTestCase(TestCase):
    def testCountAndPriority(self):
        makeResults = lambda n: list(search.SearchResult('', '', None, None, p) for p in xrange(n))
        (term, resultCount) = ("hey hey", 10)
        results = {term : makeResults(resultCount)}

        store = Store()
        itemsPerPage = 5

        def txn():
            makeSearchProvider(results)(store=store).installOn(store)
            s = search.SearchAggregator(store=store)
            s.installOn(store)
            return s

        aggregator = store.transact(txn)
        self.assertEqual(aggregator.count(term), resultCount)
        self.assertEqual(len(aggregator.search(term, count=0, offset=0)), 0)
        self.assertEqual(len(aggregator.search(term, count=5, offset=0)), 5)
        self.assertEqual(len(aggregator.search(term, count=resultCount, offset=resultCount)), 0)
        self.assertEqual(len(aggregator.search(term, count=1, offset=resultCount-1)), 1)
        self.assertEqual(len(aggregator.search("nonsense", count=0, offset=0)), 0)

        searchResults = aggregator.search(term, count=resultCount, offset=0)
        self.assertEqual(len(searchResults), resultCount)
        self.assertEqual(sorted(searchResults, key=lambda r: r.score, reverse=True),
                         searchResults)
