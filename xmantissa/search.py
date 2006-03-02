# -*- test-case-name: xmantissa.test.test_search -*-

from __future__ import division

from operator import attrgetter

from zope.interface import implements

from twisted.internet import defer
from twisted.python import components, log

from nevow import rend, inevow, tags, flat
from nevow.url import URL

from epsilon.extime import Time

from axiom import attributes
from axiom.item import Item, InstallableMixin

from xmantissa.ixmantissa import (ISearchAggregator, ISearchProvider,
                                  INavigableElement, INavigableFragment,
                                  IPreferenceAggregator)


flat.registerFlattener(lambda t, ign: t.asHumanly(), Time)

class SearchResult(object):
    def __init__(self, description, url, summary, timestamp, score):
        """score: float between 0.0 and 1.0.  bigger numbers win.
           timestamp: an epsilon.extime.Time instance"""

        self.description = description
        self.url = url
        self.summary = summary
        self.timestamp = timestamp
        self.score = score

class SearchAggregator(Item, InstallableMixin):
    implements(ISearchAggregator, INavigableElement)

    schemaVersion = 1
    typeName = 'mantissa_search_aggregator'

    installedOn = attributes.reference()
    searches = attributes.integer(default=0)

    _searchProviders = attributes.inmemory()

    def installOn(self, other):
        super(SearchAggregator, self).installOn(other)
        other.powerUp(self, ISearchAggregator)
        other.powerUp(self, INavigableElement)


    def activate(self):
        self._searchProviders = None


    def _cachePowerups(self):
        self._searchProviders = list(self.installedOn.powerupsFor(ISearchProvider))


    # INavigableElement
    def getTabs(self):
        return []


    # ISearchAggregator
    def providers(self):
        if self._searchProviders is None:
            self._cachePowerups()
        return len(self._searchProviders)


    def count(self, term):
        if self._searchProviders is None:
            self._cachePowerups()

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
            in self._searchProviders], consumeErrors=True).addCallback(countedHits)


    def search(self, term, count, offset):
        self.searches += 1

        if self._searchProviders is None:
            self._cachePowerups()

        d = defer.DeferredList([
            provider.search(term, count, offset)
            for provider in self._searchProviders
            ], consumeErrors=True)

        def searchCompleted(results):
            allSearchResults = []
            for (success, result) in results:
                if success:
                    allSearchResults.extend(result)
                else:
                    log.err(result)

            allSearchResults.sort(key=attrgetter('score'))
            allSearchResults.reverse()
            return allSearchResults
        return d.addCallback(searchCompleted)



class SearchAggregatorFragment(rend.Fragment):
    implements(INavigableFragment)

    fragmentName = 'search'
    live = True
    title = ''

    searchTerm = None
    totalItems = None
    itemsPerPage = None
    currentPage = None

    resultsPattern = None

    def __init__(self, original, docFactory=None):
        rend.Fragment.__init__(self, original, docFactory)
        self.searchAggregator = ISearchAggregator(original.installedOn)
        prefAggregator = IPreferenceAggregator(original.installedOn)
        self.itemsPerPage = prefAggregator.getPreference('itemsPerPage').value


    def head(self):
        return tags.script(type='text/javascript',
                           src='/Mantissa/js/search.js')


    def setSearchTerm(self, ctx):
        qargs = dict(URL.fromContext(ctx).queryList())
        self.searchTerm = qargs['term']
        self.currentPage = 1

        def countedHits(hitCount):
            self.totalItems = hitCount
        return self.searchAggregator.count(self.searchTerm).addCallback(countedHits)


    def beforeRender(self, ctx):
        return self.setSearchTerm(ctx)


    def data_searchTerm(self, ctx, data):
        return self.searchTerm


    def makeResults(self):
        def toDict(result):
            return dict(
                url=result.url,
                description=result.description,
                score="%.1f" % (result.score * 100),
                summary=result.summary, timestamp=result.timestamp)

        d = self.searchAggregator.search(
            self.searchTerm,
            self.itemsPerPage,
            (self.currentPage - 1) * self.itemsPerPage)

        def searchCompleted(results):
            return (len(results),
                    self.resultsPattern(data=map(toDict, results)))
        return d.addCallback(searchCompleted)


    def goingLive(self, ctx, client):
        self.resultsPattern = inevow.IQ(self.docFactory).patternGenerator('results')

        def madeResults((hits, data)):
            start = (self.currentPage - 1) * self.itemsPerPage
            # (start, stop, total)
            client.call('setSearchState', start+1, start+hits, self.totalItems)
            client.set('results', data)

        self.makeResults().addCallback(madeResults)

components.registerAdapter(SearchAggregatorFragment, SearchAggregator, INavigableFragment)
