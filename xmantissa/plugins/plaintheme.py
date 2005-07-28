
from zope.interface import classProvides

from xmantissa.ixmantissa import IWebTheme
from twisted.plugin import IPlugin

from nevow.loaders import stan
from nevow import tags as t

class PlainTheme(object):
    classProvides(IWebTheme, IPlugin)

    themeName = 'plain'
    priority = 1                # should be 0 on pretty much any other theme

    cssFiles = []

    shellTemplate = stan(
        t.html[
            t.head[
                ],
            t.body[
                t.table[
                    t.tr[
                        t.td[
                            t.div(render=t.directive("navigation")),
                            ],
                        t.td[
                            t.div(render=t.directive("content"))]]]]])

    navBoxTemplate = stan(
        t.ul(render='sequence', data='navigation')[
            t.li(pattern='item')[
                t.a(href=t.slot('link'))[
                    t.slot(name='name')],
                t.invisible(render='subtabs')
                ]
            ])

    def getDocFactory(self, fragmentName):
        if fragmentName == 'shell':
            return self.shellTemplate
        elif fragmentName == 'navigation':
            return self.navBoxTemplate
