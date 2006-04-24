# -*- test-case-name: xmantissa.test.test_search -*-

from __future__ import division

from zope.interface import implements

from twisted.internet import defer
from twisted.python import log, components

from nevow import inevow, athena

from axiom import attributes, item

from xmantissa import ixmantissa


class SearchResult(item.Item):
    """
    A temporary, in-database object associated with a particular search (ie,
    one time that one guy typed in that one search phrase) and a single item
    which was found in that search.  These live in the database to make it easy
    to display and sort them, but they are deleted when they get kind of
    oldish.

    XXX TODO - These should be kept in a temporary table or an in-memory
    database or something.
    """

    indexedItem = attributes.reference(doc="""
    An item which was found by a search.  This is adaptable to
    L{IFulltextIndexable}.
    """, allowNone=False, whenDeleted=attributes.reference.CASCADE)

    identifier = attributes.integer(doc="""
    An identifier unique to the search in which this result was found.
    """, allowNone=False, indexed=True)



class SearchAggregator(item.Item, item.InstallableMixin):
    implements(ixmantissa.ISearchAggregator, ixmantissa.INavigableElement)

    schemaVersion = 1
    typeName = 'mantissa_search_aggregator'

    installedOn = attributes.reference()
    searches = attributes.integer(default=0)

    def installOn(self, other):
        super(SearchAggregator, self).installOn(other)
        other.powerUp(self, ixmantissa.ISearchAggregator)
        other.powerUp(self, ixmantissa.INavigableElement)


    # INavigableElement
    def getTabs(self):
        return []


    # ISearchAggregator
    def providers(self):
        return list(self.installedOn.powerupsFor(ixmantissa.ISearchProvider))


    def count(self, term):
        def countedHits(results):
            total = 0
            for (success, result) in results:
                if success:
                    total += result
                else:
                    log.err(result)
            return total

        return defer.DeferredList([
            provider.count(term)
            for provider
            in self.providers()], consumeErrors=True).addCallback(countedHits)


    def search(self, term, count, offset):
        self.searches += 1

        d = defer.DeferredList([
            provider.search(term, count, offset)
            for provider in self.providers()
            ], consumeErrors=True)

        def searchCompleted(results):
            allSearchResults = []
            for (success, result) in results:
                if success:
                    allSearchResults.append(result)
                else:
                    log.err(result)
            return allSearchResults
        d.addCallback(searchCompleted)

        return d



class AggregateSearchResults(athena.LiveFragment):
    fragmentName = 'search'

    def __init__(self, aggregator):
        super(AggregateSearchResults, self).__init__()
        self.aggregator = aggregator


    def head(self):
        return None


    def render_search(self, ctx, data):
        req = inevow.IRequest(ctx)
        term = req.args.get('term', [None])[0]
        if term is None:
            return ''
        d = self.aggregator.search(term, 1000, 0)
        def gotSearchResultFragments(fragments):
            for f in fragments:
                f.setFragmentParent(self)
            return fragments
        d.addCallback(gotSearchResultFragments)
        return d

components.registerAdapter(AggregateSearchResults, SearchAggregator, ixmantissa.INavigableFragment)


class SearchProviderMixin:
    """
    Helper class for search providers which wish to be able to query the
    database for the results of a search.  This class just provides a method
    which subclasses can call which will put the results of a search into a
    bunch of L{SearchResult} items.

    @ivar store: The axiom Store in which to create the SearchResults.
    @ivar indexer: The B{real} L{ISearchProvider} with which to perform the
    search.

    XXX TODO - Put the SearchResults into an in-memory database or something
    """
    implements(ixmantissa.ISearchProvider)

    def storeSearchResults(self, results):
        s = self.store
        def transacted(results):
            # Pick a new identifier for this particular set of search results.
            identifier = s.query(SearchResult).getColumn("identifier").max(default=0) + 1

            # Delete the temporary, in-database search results for all previous
            # searches save the most recent ten.
            s.query(SearchResult, SearchResult.identifier < (identifier - 10)).deleteFromStore()
            for r in results:
                SearchResult(store=s, identifier=identifier, indexedItem=s.getItemByID(r))
            return identifier
        return s.transact(transacted, results)


    def search(self, term, count, offset):
        d = self.indexer.search(term, count, offset)
        d.addCallback(self.storeSearchResults)
        d.addCallback(self.wrapSearchResults)
        return d


    def wrapSearchResults(self, searchIdentifier):
        raise NotImplementedError("Implement wrapSearchResults in subclasses.")
