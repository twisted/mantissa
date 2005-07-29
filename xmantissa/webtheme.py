
import os, sys

from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.python.util import sibpath

from nevow.loaders import xmlfile

from xmantissa.ixmantissa import IWebTheme

from xmantissa import plugins
from twisted.plugin import getPlugins

def getAllThemes():
    l = list(getPlugins(IWebTheme, plugins))
    l.sort(key=lambda o: o.priority)
    l.reverse()
    print 'woop', l
    return l


class XHTMLDirectoryTheme(object):
    implements(IWebTheme, IPlugin)

    def __init__(self, themeName, priority=0):
        self.themeName = themeName
        self.priority = priority
        self.cachedLoaders = {}

    def getDocFactory(self, fragmentName, default=None):
        print 'Looking for', repr(fragmentName)
        if fragmentName in self.cachedLoaders:
            print 'it was cached as', self.cachedLoaders[fragmentName]
            return self.cachedLoaders[fragmentName]
        p = os.path.join(
            sibpath(sys.modules[self.__class__.__module__].__file__, 'themes'),
            self.themeName,
            fragmentName+'.html')
        print 'checking path', repr(p)
        if os.path.exists(p):
            loader = xmlfile(p)
            self.cachedLoaders[fragmentName] = loader
            print 'got it', loader
            return loader
        print 'nothing'
        return default


