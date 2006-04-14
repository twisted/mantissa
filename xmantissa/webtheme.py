
import os, sys

from twisted.python.util import sibpath

from nevow.loaders import xmlfile
from nevow import tags

from xmantissa.offering import getInstalledOfferings, getOfferings

def getAllThemes():
    l = []
    for offering in getOfferings():
        l.extend(offering.themes)
    l.sort(key=lambda o: o.priority)
    l.reverse()
    return l

def getInstalledThemes(store):
    l = []
    for offering in getInstalledOfferings(store).itervalues():
        l.extend(offering.themes)
    l.sort(key=lambda o: o.priority)
    l.reverse()
    return l

def getLoader(n):
    # TODO: implement PublicApplication (?) in webapp.py, so we can make sure
    # that these go in the right order.  Right now we've only got the one
    # though.
    for t in getAllThemes():
        fact = t.getDocFactory(n, None)
        if fact is not None:
            return fact

    raise RuntimeError("No loader for %r anywhere" % (n,))

class XHTMLDirectoryTheme(object):
    def __init__(self, themeName, priority=0):
        self.themeName = themeName
        self.priority = priority
        self.cachedLoaders = {}

    def getDocFactory(self, fragmentName, default=None):
        if fragmentName in self.cachedLoaders:
            return self.cachedLoaders[fragmentName]
        p = os.path.join(
            sibpath(sys.modules[self.__class__.__module__].__file__, 'themes'),
            self.themeName,
            fragmentName+'.html')
        if os.path.exists(p):
            loader = xmlfile(p)
            self.cachedLoaders[fragmentName] = loader
            return loader
        return default

    def head(self):
        return None

class MantissaTheme(XHTMLDirectoryTheme):
    def head(self):
        return tags.link(rel='stylesheet', type='text/css',
                         href='/Mantissa/mantissa.css')
