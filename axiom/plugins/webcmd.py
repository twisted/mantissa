# -*- test-case-name: xmantissa.test.test_webcmd -*-

import os
import sys

from twisted.python import reflect
from twisted.python.usage import UsageError
from twisted.python.filepath import FilePath

from axiom import item, attributes
from axiom.dependency import installOn, onlyInstallPowerups
from axiom.scripts import axiomatic

from xmantissa.web import SiteConfiguration
from xmantissa.website import StaticSite, APIKey
from xmantissa import ixmantissa, webadmin
from xmantissa.port import TCPPort, SSLPort
from xmantissa.plugins.baseoff import baseOffering


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
         'Filename (relative to files directory of the store) to which to log '
         'HTTP requests (empty string to disable)'),
        ('hostname', 'H', None,
         'Canonical hostname for this server (used in URL generation).'),
        ('urchin-key', '', None,
         'Google Analytics API key for this site')]

    def __init__(self, *a, **k):
        super(WebConfiguration, self).__init__(*a, **k)
        self.staticPaths = []


    didSomething = 0

    def postOptions(self):
        siteStore = self.parent.getStore()

        # Make sure the base mantissa offering is installed.
        offeringTech = ixmantissa.IOfferingTechnician(siteStore)
        offerings = offeringTech.getInstalledOfferingNames()
        if baseOffering.name not in offerings:
            raise UsageError(
                "This command can only be used on Mantissa databases.")

        # It is, we can make some simplifying assumptions.  Specifically,
        # there is exactly one SiteConfiguration installed.
        site = siteStore.findUnique(SiteConfiguration)

        # Get any ports associated with that configuration.  Some of these
        # will have been created by "axiomatic mantissa", but they may have
        # been changed by the admin port configuration interface
        # subsequently.  In the event of multiple ports of a particular
        # type, only the first will be manipulated.  This should be
        # superceded by the functionality described in #2515.
        tcps = list(siteStore.query(TCPPort, TCPPort.factory == site))
        ssls = list(siteStore.query(SSLPort, SSLPort.factory == site))

        if self['port'] is not None:
            if self['port']:
                portNumber = int(self['port'])
                if tcps:
                    tcps[0].portNumber = portNumber
                else:
                    TCPPort(store=siteStore,
                            factory=site,
                            portNumber=portNumber)
            else:
                if tcps:
                    tcps[0].deleteFromStore()
                else:
                    raise UsageError("There is no TCP port to delete.")


        if self['secure-port'] is not None:
            if self['secure-port']:
                portNumber = int(self['secure-port'])
                if self['pem-file'] is not None:
                    if self['pem-file']:
                        certificatePath = FilePath(self['pem-file'])
                    else:
                        certificatePath = None
                if ssls:
                    ssls[0].portNumber = portNumber
                    if self['pem-file'] is not None:
                        ssls[0].certificatePath = certificatePath
                else:
                    port = SSLPort(store=siteStore, factory=site, portNumber=portNumber)
                    if self['pem-file'] is not None:
                        port.certificatePath = certificatePath
            else:
                if ssls:
                    ssls[0].deleteFromStore()
                else:
                    raise UsageError("There is no SSL port to delete.")

        if self['http-log'] is not None:
            if self['http-log']:
                site.httpLog = siteStore.filesdir.preauthChild(
                    self['http-log'])
            else:
                site.httpLog = None

        if self['hostname'] is not None:
            if self['hostname']:
                site.hostname = self.decodeCommandLine(self['hostname'])
            else:
                raise UsageError("Hostname may not be empty.")

        if self['urchin-key'] is not None:
            # Install the API key for Google Analytics, to enable tracking for
            # this site.
            APIKey.setKeyForAPI(
                siteStore, APIKey.URCHIN, self['urchin-key'].decode('ascii'))


        # Set up whatever static content was requested.
        for webPath, filePath in self.staticPaths:
            staticSite = siteStore.findFirst(
                StaticSite, StaticSite.prefixURL == webPath)
            if staticSite is not None:
                staticSite.staticContentPath = filePath
            else:
                staticSite = StaticSite(
                    store=siteStore,
                    staticContentPath=filePath,
                    prefixURL=webPath,
                    sessionless=True)
                onlyInstallPowerups(staticSite, siteStore)


    def opt_static(self, pathMapping):
        webPath, filePath = decodeCommandLine(pathMapping).split(os.pathsep, 1)
        if webPath.startswith('/'):
            webPath = webPath[1:]
        self.staticPaths.append((webPath, os.path.abspath(filePath)))


    def opt_list(self):
        self.didSomething = 1
        s = self.parent.getStore()
        for ws in s.query(SiteConfiguration):
            print 'The hostname is', ws.hostname
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
                    raise UsageError('Administrator controls already disabled.')
            else:
                installOn(webadmin.AdminStatsApplication(store=s), s)

        if self['developer']:
            didSomething = True
            if self['disable']:
                for app in s.query(webadmin.DeveloperApplication):
                    app.deleteFromStore()
                    break
                else:
                    raise UsageError('Developer controls already disabled.')
            else:
                installOn(webadmin.DeveloperApplication(store=s), s)

        if not didSomething:
            raise UsageError("Specify something or I won't do anything.")
