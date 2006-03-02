from zope.interface import implements

from twisted.trial.unittest import TestCase
from twisted.internet import defer

from axiom.item import Item
from axiom.store import Store
from axiom import attributes

from xmantissa import search, ixmantissa

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
            return defer.succeed(len(results.get(term, ())))

        def search(self, term, count, offset):
            if term in results:
                return defer.succeed(results[term][offset:count+offset])
            return defer.succeed([])

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
        tests = []
        tests.append(aggregator.count(term).addCallback(self.assertEquals, resultCount))
        tests.append(aggregator.search(term, count=0, offset=0).addCallback(len).addCallback(self.assertEquals, 0))
        tests.append(aggregator.search(term, count=5, offset=0).addCallback(len).addCallback(self.assertEquals, 5))
        tests.append(aggregator.search(term, count=resultCount, offset=resultCount).addCallback(len).addCallback(self.assertEquals, 0))
        tests.append(aggregator.search(term, count=1, offset=resultCount-1).addCallback(len).addCallback(self.assertEquals, 1))
        tests.append(aggregator.search("nonsense", count=0, offset=0).addCallback(len).addCallback(self.assertEquals, 0))
        tests.append(aggregator.search(term, count=resultCount, offset=0).addCallback(len).addCallback(self.assertEquals, resultCount))

        def gotSearchResults(searchResults):
            self.assertEquals(
                sorted(searchResults, key=lambda r: r.score, reverse=True),
                searchResults)
        tests.append(aggregator.search(term, count=resultCount, offset=0).addCallback(gotSearchResults))

        return defer.DeferredList(tests, fireOnOneErrback=True)
