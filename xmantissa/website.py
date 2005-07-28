
"""

This module defines the basic engine for web sites and applications using
Mantissa.  It defines the basic in-database web server, and an authentication
binding using nevow.guard.

To interact with the code defined here, create a web site using 

"""

from zope.interface import implements

from twisted.application.service import IService, Service
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import ICredentialsChecker, AllowAnonymousAccess

from twisted.internet import reactor

from nevow.rend import NotFound
from nevow.guard import SessionWrapper
from nevow.inevow import IResource
from nevow.appserver import NevowSite
from nevow import static

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

class UnguardedWrapper(SiteRootMixin):
    implements(IResource)

    powerupInterface = ISessionlessSiteRootPlugin

    def __init__(self, store, guardedRoot):
        self.store = store
        self.guardedRoot = guardedRoot

    def locateChild(self, ctx, segments):
        x = SiteRootMixin.locateChild(self, ctx, segments)
        if x is not NotFound:
            return x
        return self.guardedRoot.locateChild(ctx, segments)


JUST_SLASH = ('',)

class StaticSite(Item):
    implements(ISessionlessSiteRootPlugin)

    schemaVersion = 1
    typeName = 'static_web_site'

    staticContentPath = text()
    activationURL = text()

    def install(self):
        # Only 256 segments are allowed in URL paths.  We want to make sure
        # that static powerups always lose priority ordering to dynamic
        # powerups, since dynamic powerups will have information

        self.store.powerUp(self, ISessionlessSiteRootPlugin,
                           priority=self.activationURL.count('/')-256)

    def resourceFactory(self, segments):
        if not self.activationURL:
            needle = ()
        else:
            needle = tuple(self.activationURL.split('/'))
        S = len(needle)
        if segments[:S] == needle:
            if segments == JUST_SLASH:
                # I *HATE* THE WEB
                subsegments = segments
            else:
                subsegments = segments[S:]
            return static.File(self.staticContentPath), subsegments


class WebSite(Item, Service, SiteRootMixin):
    typeName = 'mantissa_web_powerup'
    schemaVersion = 1

    portno = integer()
    staticpath = text()         # I'm setting this up as a non-store-relative
                                # path because I assume the relevant files are
                                # going to be in SVN.

    parent = inmemory()
    running = inmemory()
    name = inmemory()

    port = inmemory()
    site = inmemory()

    def install(self):
        x = IRealm(self.store, None)
        if x is None:
            raise WebConfigurationError(
                'No realm: you need to install a userbase before anything else.')
        y = ICredentialsChecker(self.store, None)
        if y is None:
            raise WebConfigurationError(
                'No checkers: you need to install a userbase before anything else.')

        self.store.powerUp(self, IService)
        self.store.powerUp(self, IResource)

    def privilegedStartService(self):

        guardedRoot = SessionWrapper(
            Portal(IRealm(self.store),
                   [ICredentialsChecker(self.store),
                    AllowAnonymousAccess()]))

        self.site = NevowSite(UnguardedWrapper(self.store, guardedRoot))

        self.port = reactor.listenTCP(self.portno, self.site)

    def stopService(self):
        return self.port.stopListening()
