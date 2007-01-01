# -*- test-case-name: xmantissa.test.test_webcmd -*-

import os
import sys

from twisted.python import usage, reflect
from twisted.python.filepath import FilePath

from axiom import item, attributes
from axiom.dependency import installOn, onlyInstallPowerups
from axiom.scripts import axiomatic

from xmantissa.website import WebSite, StaticSite, WebConfigurationError
from xmantissa import ixmantissa, webapp, webadmin
from xmantissa.port import TCPPort, SSLPort


def decodeCommandLine(cmdline):
    """Turn a byte string from the command line into a unicode string.
    """
    codec = sys.stdin.encoding or sys.getdefaultencoding()
    return unicode(cmdline, codec)



class WebConfiguration(axiomatic.AxiomaticCommand):
    name = 'web'
    description = 'Web.  Yay.'

    optParameters = [
        ('port', 'p', None,
         'TCP port over which to serve HTTP (empty string to disable)'),
        ('secure-port', 's', None,
         'TCP port over which to serve HTTPS (empty string to disable)'),
        ('pem-file', 'f', None,
         'Filename containing PEM-format private key and certificate '
         '(empty string to disable; ignored if --secure-port is not '
         'specified)'),
        ('http-log', 'h', None,
         'Filename to which to log HTTP requests (empty string to disable)'),
        ('hostname', 'H', None,
         'Canonical hostname for this server (used in URL generation).'),
        ]

    def __init__(self, *a, **k):
        super(WebConfiguration, self).__init__(*a, **k)
        self.staticPaths = []

    didSomething = 0


    def _getWebSite(self):
        return self.parent.getStore().findOrCreate(
            WebSite, lambda ws: installOn(ws, ws.store))


    def _changePort(self, type, **kw):
        ws = self._getWebSite()
        port = ws.store.findOrCreate(
            type,
            lambda p: installOn(p, p.store),
            factory=ws)
        if kw:
            for k, v in kw.iteritems():
                setattr(port, k, v)
        else:
            port.deleteFromStore()


    def postOptions(self):
        s = self.parent.getStore()
        def _():
            change = {}

            # Find the HTTP port, if there is one.
            if self['port'] is not None:
                if self['port']:
                    self._changePort(TCPPort, portNumber=int(self['port']))
                else:
                    self._changePort(TCPPort)
                self.didSomething = 1

            # Find the HTTPS information, if there is any.
            if self['secure-port'] is not None:
                if self['secure-port']:
                    extra = {}
                    if self['pem-file'] is not None:
                        if self['pem-file']:
                            extra['certificatePath'] = FilePath(self['pem-file'])
                    self._changePort(SSLPort,
                                     portNumber=int(self['secure-port']),
                                     **extra)
                else:
                    self._changePort(SSLPort)
                self.didSomething = 1

            if self['http-log'] is not None:
                if self['http-log']:
                    change['httpLog'] = self['http-log']
                else:
                    change['httpLog'] = None

            if self['hostname'] is not None:
                if self['hostname']:
                    change['hostname'] = self.decodeCommandLine(self['hostname'])
                else:
                    change['hostname'] = None

            # If HTTP or HTTPS is being configured, make sure there's
            # a WebSite with the right attribute values.
            if change:
                ws = self._getWebSite()
                for (k, v) in change.iteritems():
                    setattr(ws, k, v)
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
                                    prefixURL=webPath,
                                    sessionless=True)
                    onlyInstallPowerups(ss, s)
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


    def opt_list(self):
        self.didSomething = 1
        s = self.parent.getStore()
        for ws in s.query(WebSite):
            print 'The hostname is', ws.hostname or 'not set.'
            for tcp in s.query(TCPPort, TCPPort.factory == ws):
                print 'Configured to use HTTP port %d.' % (tcp.portNumber,)
            for ssl in s.query(SSLPort, SSLPort.factory == ws):
                print 'Configured to use HTTPS port %d with certificate %s' % (ssl.portNumber, ssl.certificatePath.path)
            if ws.httpLog is not None:
                print 'Logging HTTP requests to', ws.httpLog
            break
        else:
            print 'No configured webservers.'


        def powerupsWithPriorityFor(interface):
            for cable in s.query(
                item._PowerupConnector,
                attributes.AND(item._PowerupConnector.interface == unicode(reflect.qual(interface)),
                               item._PowerupConnector.item == s),
                sort=item._PowerupConnector.priority.descending):
                yield cable.powerup, cable.priority

        print 'Sessionless plugins:'
        for srp, prio in powerupsWithPriorityFor(ixmantissa.ISessionlessSiteRootPlugin):
            print '  %s (prio. %d)' % (srp, prio)
        print 'Sessioned plugins:'
        for srp, prio in powerupsWithPriorityFor(ixmantissa.ISiteRootPlugin):
            print '  %s (prio. %d)' % (srp, prio)
        sys.exit(0)

    opt_static.__doc__ = """
    Add an element to the mapping of web URLs to locations of static
    content on the filesystem (webpath%sfilepath)
    """ % (os.pathsep,)

class WebApplication(axiomatic.AxiomaticCommand):
    name = 'web-application'
    description = 'Web interface for normal user'

    optParameters = [
        ('theme', 't', '', 'The name of the default theme for this user.'),
        ]

    def postOptions(self):
        s = self.parent.getStore()
        installOn(webapp.PrivateApplication(
            store=s,
            preferredTheme=decodeCommandLine(self['theme'])), s)

class WebAdministration(axiomatic.AxiomaticCommand):
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
                installOn(webadmin.AdminStatsApplication(store=s), s)

        if self['developer']:
            didSomething = True
            if self['disable']:
                for app in s.query(webadmin.DeveloperApplication):
                    app.deleteFromStore()
                    break
                else:
                    raise usage.UsageError('Developer controls already disabled.')
            else:
                installOn(webadmin.DeveloperApplication(store=s), s)
        if not didSomething:
            raise usage.UsageError("Specify something or I won't do anything.")
