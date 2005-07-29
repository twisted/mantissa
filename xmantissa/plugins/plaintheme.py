
from zope.interface import classProvides

from xmantissa.ixmantissa import IWebTheme
from twisted.plugin import IPlugin

from twisted.python.util import sibpath

from nevow.loaders import xmlfile, stan
from nevow import tags as t

class PlainTheme(object):
    classProvides(IWebTheme, IPlugin)

    themeName = 'plain'
    priority = 1                # should be 0 on pretty much any other theme

    cssFiles = []

    shellTemplate = stan(
        t.html[
            t.head(render=t.directive("head"))[
                t.title(render=t.directive("title"))
                ],
            t.body[
                t.table[
                    t.tr[
                        t.td[
                            t.div(render=t.directive("navigation")),
                            ],
                        t.td[
                            t.h1(render=t.directive("title")),
                            t.div(render=t.directive("content"))]]]]])

    navBoxTemplate = xmlfile(sibpath(__file__, 'navbox.html'))

    def getDocFactory(cls, fragmentName, default=None):
        if fragmentName == 'shell':
            return cls.shellTemplate
        elif fragmentName == 'navigation':
            return cls.navBoxTemplate
        return default
    getDocFactory = classmethod(getDocFactory)
