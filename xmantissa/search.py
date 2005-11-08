from __future__ import division
from zope.interface import implements

from xmantissa.ixmantissa import (ISearchAggregator, ISearchProvider,
                                  INavigableElement, INavigableFragment,
                                  IPreferenceAggregator)
from axiom import attributes
from axiom.item import Item, InstallableMixin
from operator import attrgetter
from nevow import rend, livepage, inevow, tags, flat
from epsilon.extime import Time
from nevow.url import URL
from twisted.python.components import registerAdapter

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

        return max(provider.count(term) for provider in self._searchProviders)

    def search(self, term, count, offset):
        self.searches += 1

        if self._searchProviders is None:
            self._cachePowerups()

        results = []
        for provider in self._searchProviders:
            results.extend(provider.search(term, count, offset))

        results.sort(key=attrgetter('score'))
        results.reverse()

        return results

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
                           src='/static/mantissa/search.js')

    def setSearchTerm(self, ctx):
        qargs = dict(URL.fromContext(ctx).queryList())
        self.searchTerm = qargs['term']
        self.totalItems = self.searchAggregator.count(self.searchTerm)
        self.currentPage = 1

    def beforeRender(self, ctx):
        self.setSearchTerm(ctx)

    def data_searchTerm(self, ctx, data):
        return self.searchTerm

    def makeResults(self):
        data = self.searchAggregator.search(self.searchTerm,
                                            self.itemsPerPage,
                                            (self.currentPage-1) * self.itemsPerPage)

        todict = lambda sr: dict(url=sr.url, description=sr.description,
                                 score="%.1f" % (sr.score * 100),
                                 summary=sr.summary, timestamp=sr.timestamp)

        return (len(data), self.resultsPattern(data=map(todict, data)))

    def goingLive(self, ctx, client):
        self.resultsPattern = inevow.IQ(self.docFactory).patternGenerator('results')
        (hits, data) = self.makeResults()

        start = (self.currentPage - 1) * self.itemsPerPage
        # (start, stop, total)
        client.call('setSearchState', start+1, start+hits, self.totalItems)
        client.set('results', data)

registerAdapter(SearchAggregatorFragment, SearchAggregator, INavigableFragment)
