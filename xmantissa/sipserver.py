from twisted.internet import reactor
from twisted.application.service import IService, Service
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import ICredentialsChecker
from axiom.attributes import integer, inmemory, bytes
from axiom.item import Item
from xmantissa import sip

class SIPConfigurationError(RuntimeError):
    """You specified some invalid configuration."""
    
    
class SIPServer(Item, Service):
    typename = 'mantissa_sip_powerup'
    schemaVersion = 1
    portno = integer(default=5060)
    hostnames =  bytes()
    
    parent = inmemory()
    running = inmemory()
    name = inmemory()

    proxy = inmemory()
    port = inmemory()
    site = inmemory()

    def __init__(self, hostnames):
        self.hostnames = hostnames
        
    def installOn(self, other):
        assert self.installedOn is None, "You cannot install a SIPServer on more than one thing"
        other.powerUp(self, IService)
        self.installedOn = other

    def privilegedStartService(self):
        realm = IRealm(self.store, None)
        if realm is None:
            raise SIPConfigurationError(
                'No realm: '
                'you need to install a userbase before using this service.')
        chkr = ICredentialsChecker(self.store, None)
        if chkr is None:
            raise SIPConfigurationError(
                'No checkers: '
                'you need to install a userbase before using this service.')
        portal = Portal(realm, [chkr])
        self.proxy = sip.Proxy(portal)

        f = sip.SIPTransport(self.proxy, self.hostnames.split(','), self.portno)
        self.port = reactor.listenUDP(self.portno, f)
