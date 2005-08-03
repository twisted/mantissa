
"""

This module defines the basic engine for web sites and applications using
Mantissa.  It defines the basic in-database web server, and an authentication
binding using nevow.guard.

To interact with the code defined here, create a web site using the
command-line 'axiomatic' program using the 'web' subcommand.

"""

from zope.interface import implements

from twisted.application.service import IService, Service
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import ICredentialsChecker, AllowAnonymousAccess
from twisted.python.util import sibpath

from twisted.internet import reactor

from nevow.rend import NotFound, Page
from nevow.guard import SessionWrapper
from nevow.inevow import IResource
from nevow.appserver import NevowSite
from nevow.loaders import xmlfile
from nevow.static import File

from axiom.item import Item
from axiom.attributes import integer, inmemory, text

from xmantissa.ixmantissa import ISiteRootPlugin, ISessionlessSiteRootPlugin

class WebConfigurationError(RuntimeError):
    """You specified some invalid configuration.
    """

class SiteRootMixin(object):
    implements(IResource)

    powerupInterface = ISiteRootPlugin

    def renderHTTP(self, ctx):
        raise NotImplementedError(
            "This _must_ be installed at the root of a server.")

    def locateChild(self, ctx, segments):
        self.hitCount += 1
        s = self.store
        P = self.powerupInterface
        while s is not None:
            for plg in s.powerupsFor(P):
                childAndSegments = plg.resourceFactory(segments)
                if childAndSegments is not None:
                    child, segments = childAndSegments # sanity
                                                       # check/documentation; feel
                                                       # free to remove
                    return child, segments
            s = s.parent
        return NotFound

class LoginPage(Page):
    docFactory = xmlfile(sibpath(__file__, "login.html"))

class UnguardedWrapper(SiteRootMixin):
    implements(IResource)

    powerupInterface = ISessionlessSiteRootPlugin
    hitCount = 0

    def __init__(self, store, guardedRoot):
        self.store = store
        self.guardedRoot = guardedRoot

    def locateChild(self, ctx, segments):
        if segments[0] == 'login':
            return LoginPage(), ()
        x = SiteRootMixin.locateChild(self, ctx, segments)
        if x is not NotFound:
            return x
        return self.guardedRoot.locateChild(ctx, segments)


JUST_SLASH = ('',)

class PrefixURLMixin:
    """
    Mixin for use by I[Sessionlesss]SiteRootPlugin implementors; provides a
    resourceFactory method which looks for an 'prefixURL' string on self,
    and calls and returns self.createResource().
    """

    def resourceFactory(self, segments):
        if not self.prefixURL:
            needle = ()
        else:
            needle = tuple(self.prefixURL.split('/'))
        S = len(needle)
        if segments[:S] == needle:
            if segments == JUST_SLASH:
                # I *HATE* THE WEB
                subsegments = segments
            else:
                subsegments = segments[S:]
            return self.createResource(), subsegments

    def install(self):
        # Only 256 segments are allowed in URL paths.  We want to make sure
        # that static powerups always lose priority ordering to dynamic
        # powerups, since dynamic powerups will have information
        priority = self.prefixURL.count('/') - 256
        for iface in ISessionlessSiteRootPlugin, ISiteRootPlugin:
            if iface.providedBy(self):
                self.store.powerUp(self, iface, priority)

class StaticSite(Item, PrefixURLMixin):
    implements(ISessionlessSiteRootPlugin,     # implements both so that it
               ISiteRootPlugin)                # works in both super and sub
                                               # stores.


    schemaVersion = 1
    typeName = 'static_web_site'

    prefixURL = text()
    staticContentPath = text()

    def createResource(self):
        return File(self.staticContentPath)


class WebSite(Item, Service, SiteRootMixin):
    typeName = 'mantissa_web_powerup'
    schemaVersion = 1

    portno = integer(default=0)
    hitCount = integer(default=0)

    parent = inmemory()
    running = inmemory()
    name = inmemory()

    port = inmemory()
    site = inmemory()

    def install(self):
        self.store.powerUp(self, IService)
        self.store.powerUp(self, IResource)

    def privilegedStartService(self):
        realm = IRealm(self.store, None)
        if realm is None:
            raise WebConfigurationError(
                'No realm: '
                'you need to install a userbase before using this service.')
        chkr = ICredentialsChecker(self.store, None)
        if chkr is None:
            raise WebConfigurationError(
                'No checkers: '
                'you need to install a userbase before using this service.')

        guardedRoot = SessionWrapper(
            Portal(realm, [chkr, AllowAnonymousAccess()]))

        self.site = NevowSite(UnguardedWrapper(self.store, guardedRoot))

        self.port = reactor.listenTCP(self.portno, self.site)

    def stopService(self):
        return self.port.stopListening()
