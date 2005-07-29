
import os
import sys

from zope.interface import classProvides

from twisted.python import usage
from twisted import plugin

from axiom import iaxiom

from xmantissa.website import WebSite, StaticSite, WebConfigurationError


class WebConfiguration(usage.Options):
    classProvides(plugin.IPlugin, iaxiom.IAxiomaticCommand)

    name = 'web'
    description = 'Web.  Yay.'

    optParameters = [
        ('port', 'p', None, 'TCP port number to bind'),
        ]

    def __init__(self, *a, **k):
        usage.Options.__init__(self, *a, **k)
        self.staticPaths = []

    didSomething = 0

    def postOptions(self):
        s = self.parent.getStore()
        def _():
            if self['port'] is not None:
                portno = int(self['port'])
                for ws in s.query(WebSite):
                    ws.portno = portno
                    break
                else:
                    ws = WebSite(store=s, portno=portno)
                    ws.install()
                self.didSomething = 1
            for webPath, filePath in self.staticPaths:
                for ss in s.query(StaticSite,
                                  StaticSite.prefixURL == webPath):
                    ss.staticContentPath = filePath
                    break
                else:
                    ss = StaticSite(store=s,
                                    staticContentPath=filePath,
                                    prefixURL=webPath)
                    ss.install()
                self.didSomething = 1
        try:
            s.transact(_)
        except WebConfigurationError, wce:
            print wce
            sys.exit(1)
        if not self.didSomething:
            self.opt_help()

    def opt_static(self, pathMapping):
        codec = sys.stdin.encoding or sys.getdefaultencoding()
        webPath, filePath = unicode(pathMapping, codec).split(os.pathsep, 1)
        if webPath.startswith('/'):
            webPath = webPath[1:]
        self.staticPaths.append((webPath, os.path.abspath(filePath)))
    opt_s = opt_static

    def opt_list(self):
        self.didSomething = 1
        s = self.parent.getStore()
        for ws in s.query(WebSite):
            print 'Configured to use port %d.' % (ws.portno,)
            break
        else:
            print 'No configured webservers.'

        for ss in s.query(StaticSite):
            print '/%s => %s' % (ss.prefixURL, ss.staticContentPath)

    opt_static.__doc__ = """
    Add an element to the mapping of web URLs to locations of static
    content on the filesystem (webpath%sfilepath)
    """ % (os.pathsep,)
