
import os
import sys

from zope.interface import classProvides

from twisted.python import usage
from twisted import plugin

from axiom import iaxiom

from xmantissa.website import WebSite, StaticSite, WebConfigurationError
from xmantissa import webapp, webadmin

def decodeCommandLine(cmdline):
    """Turn a byte string from the command line into a unicode string.
    """
    codec = sys.stdin.encoding or sys.getdefaultencoding()
    return unicode(cmdline, codec)

class WebConfiguration(usage.Options):
    classProvides(plugin.IPlugin, iaxiom.IAxiomaticCommand)

    name = 'web'
    description = 'Web.  Yay.'

    optParameters = [
        ('port', 'p', None, 'TCP port over which to serve HTTP'),
        ('secure-port', 's', None, 'TCP port over which to serve HTTPS'),
        ('pem-file', 'f', None, 'Filename containing PEM-format private key and certificate'),
        ]

    def __init__(self, *a, **k):
        usage.Options.__init__(self, *a, **k)
        self.staticPaths = []

    didSomething = 0

    def postOptions(self):
        s = self.parent.getStore()
        def _():

            # Find the HTTP port, if there is one.
            if self['port'] is not None:
                portNumber = int(self['port'])
            else:
                portNumber = None

            # Find the HTTPS information, if there is any.
            if (self['secure-port'] is not None) != (self['pem-file'] is not None):
                raise WebConfigurationError("Supply both or neither of secure-port and pem-file")
            else:
                if self['secure-port']:
                    securePort = int(self['secure-port'])
                    pemFile = self['pem-file']
                else:
                    securePort = pemFile = None

            # If HTTP or HTTPS is being configured, make sure there's
            # a WebSite with the right attribute values.
            if portNumber is not None or securePort is not None:
                for ws in s.query(WebSite):
                    ws.portNumber = portNumber
                    ws.securePortNumber = securePort
                    ws.certificateFile = pemFile
                    break
                else:
                    ws = WebSite(store=s, portNumber=portNumber, securePortNumber=securePort, certificateFile=pemFile)
                    ws.installOn(s)
                self.didSomething = 1

            # Set up whatever static content was requested.
            for webPath, filePath in self.staticPaths:
                for ss in s.query(StaticSite,
                                  StaticSite.prefixURL == webPath):
                    ss.staticContentPath = filePath
                    break
                else:
                    ss = StaticSite(store=s,
                                    staticContentPath=filePath,
                                    prefixURL=webPath)
                    ss.installOn(s)
                self.didSomething = 1
        try:
            s.transact(_)
        except WebConfigurationError, wce:
            print wce
            sys.exit(1)
        if not self.didSomething:
            self.opt_help()

    def opt_static(self, pathMapping):
        webPath, filePath = decodeCommandLine(pathMapping).split(os.pathsep, 1)
        if webPath.startswith('/'):
            webPath = webPath[1:]
        self.staticPaths.append((webPath, os.path.abspath(filePath)))
    opt_s = opt_static

    def opt_list(self):
        self.didSomething = 1
        s = self.parent.getStore()
        for ws in s.query(WebSite):
            if ws.portNumber is not None:
                print 'Configured to use HTTP port %d.' % (ws.portNumber,)
            if ws.securePortNumber is not None:
                print 'Configured to use HTTPS port %d with certificate %s' % (ws.securePortNumber, ws.certificateFile)
            break
        else:
            print 'No configured webservers.'

        for ss in s.query(StaticSite):
            print '/%s => %s' % (ss.prefixURL, ss.staticContentPath)

    opt_static.__doc__ = """
    Add an element to the mapping of web URLs to locations of static
    content on the filesystem (webpath%sfilepath)
    """ % (os.pathsep,)

class WebApplication(usage.Options):
    classProvides(plugin.IPlugin, iaxiom.IAxiomaticCommand)

    name = 'web-application'
    description = 'Web interface for normal user'

    optParameters = [
        ('theme', 't', '', 'The name of the default theme for this user.'),
        ]

    def postOptions(self):
        s = self.parent.getStore()
        webapp.PrivateApplication(
            store=s,
            preferredTheme=decodeCommandLine(self['theme']),
            hitCount=0).installOn(s)

class WebAdministration(usage.Options):
    classProvides(plugin.IPlugin, iaxiom.IAxiomaticCommand)

    name = 'web-admin'
    description = 'Administrative controls for the web'

    optFlags = [
        ('admin', 'a', 'Enable administrative controls'),
        ('developer', 'd', 'Enable developer controls'),

        ('disable', 'D', 'Remove the indicated options, instead of enabling them.'),
        ]

    def postOptions(self):
        s = self.parent.getStore()

        didSomething = False

        if self['admin']:
            didSomething = True
            if self['disable']:
                for app in s.query(webadmin.AdminStatsApplication):
                    app.deleteFromStore()
                    break
                else:
                    raise usage.UsageError('Administrator controls already disabled.')
            else:
                webadmin.AdminStatsApplication(store=s).installOn(s)

        if self['developer']:
            didSomething = True
            if self['disable']:
                for app in s.query(webadmin.DeveloperApplication):
                    app.deleteFromStore()
                    break
                else:
                    raise usage.UsageError('Developer controls already disabled.')
            else:
                webadmin.DeveloperApplication(store=s).installOn(s)
        if not didSomething:
            raise usage.UsageError("Specify something or I won't do anything.")
