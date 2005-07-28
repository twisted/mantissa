
from xmantissa.ixmantissa import IWebTheme
from xmantissa import plugins
from twisted.plugin import getPlugins

def getAllThemes():
    l = list(getPlugins(IWebTheme, plugins))
    l.sort(key=lambda o: o.priority)
    l.reverse()
    print 'woop', l
    return l
