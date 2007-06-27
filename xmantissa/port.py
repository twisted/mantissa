# -*- test-case-name: xmantissa.test.test_port -*-

"""
Network port features for Mantissa services.

Provided herein are L{IService} L{Item} classes which can be used to take care
of most of the work required to run a network server within a Mantissa server.

Framework code should define an L{Item} subclass which implements
L{xmantissa.ixmantissa.IProtocolFactoryFactory} as desired.  No direct
interaction with the reactor nor specification of port or other network
configuration is necessary in that subclass.  Port types from this module can
be directly instantiated or configuration can be left up to another tool which
operates on arbitrary ports and L{IProtocolFactoryFactory} powerups (for
example, the administrative powerup L{xmantissa.webadmin.PortConfiguration}).

For example, a finger service might be defined in this way::

    from fingerproject import FingerFactory

    from axiom.item import Item
    from axiom.attributes import integer

    from xmantissa.ixmantissa import IProtocolFactoryFactory

    class Finger(Item):
        '''
        A finger (RFC 1288) server.
        '''
        implements(IProtocolFactoryFactory)
        powerupInterfaces = (IProtocolFactoryFactory,)

        requestCount = integer(doc=''
        The number of finger requests which have been responded to, ever.
        ''')

        def getFactory(self):
            return FingerFactory(self)

All concerns related to binding ports can be disregarded.  Once this item has
been added to a site store, an administrator will have access to it and may
configure it to listen on one or more ports.
"""

from zope.interface import implements

try:
    from OpenSSL import SSL
except ImportError:
    SSL = None

from twisted.application.service import IService, IServiceCollection
from twisted.internet.ssl import PrivateCertificate, CertificateOptions
from twisted.python.reflect import qual

from axiom.item import Item, declareLegacyItem, normalize
from axiom.attributes import inmemory, integer, reference, path, text
from axiom.upgrade import registerAttributeCopyingUpgrader


class PortMixin:
    """
    Mixin implementing most of L{IService} as would be appropriate for an Axiom
    L{Item} subclass in order to manage the lifetime of an
    L{twisted.internet.interfaces.IListeningPort}.
    """
    implements(IService)

    powerupInterfaces = (IService,)

    # Required by IService but unused by this code.
    name = None

    def activate(self):
        self.parent = None
        self._listen = None
        self.listeningPort = None


    def installed(self):
        """
        Callback invoked after this item has been installed on a store.

        This is used to set the service parent to the store's service object.
        """
        self.setServiceParent(self.store)


    def deleted(self):
        """
        Callback invoked after a transaction in which this item has been
        deleted is committed.

        This is used to remove this item from its service parent, if it has
        one.
        """
        if self.parent is not None:
            self.disownServiceParent()


    # IService
    def setServiceParent(self, parent):
        IServiceCollection(parent).addService(self)
        self.parent = parent


    def disownServiceParent(self):
        IServiceCollection(self.parent).removeService(self)
        self.parent = None


    def privilegedStartService(self):
        if self.portNumber < 1024:
            self.listeningPort = self.listen()


    def startService(self):
        if self.listeningPort is None:
            self.listeningPort = self.listen()


    def stopService(self):
        d = self.listeningPort.stopListening()
        self.listeningPort = None
        return d



class TCPPort(PortMixin, Item):
    """
    An Axiom Service Item which will bind a TCP port to a protocol factory when
    it is started.
    """
    schemaVersion = 2

    portNumber = integer(doc="""
    The TCP port number on which to listen.
    """)

    interface = text(doc="""
    The hostname to bind to.
    """, default=u'')

    factory = reference(doc="""
    An Item with a C{getFactory} method which returns a Twisted protocol
    factory.
    """, whenDeleted=reference.CASCADE)

    parent = inmemory(doc="""
    A reference to the parent service of this service, whenever there is a
    parent.
    """)

    _listen = inmemory(doc="""
    An optional reference to a callable implementing the same interface as
    L{IReactorTCP.listenTCP}.  If set, this will be used to bind a network
    port.  If not set, the reactor will be imported and its C{listenTCP} method
    will be used.
    """)

    listeningPort = inmemory(doc="""
    A reference to the L{IListeningPort} returned by C{self.listen} which is
    set whenever there there is one listening.
    """)

    def listen(self):
        if self._listen is not None:
            _listen = self._listen
        else:
            from twisted.internet import reactor
            _listen = reactor.listenTCP
        return _listen(self.portNumber, self.factory.getFactory(),
                       interface=self.interface.encode('ascii'))

declareLegacyItem(
    typeName=normalize(qual(TCPPort)),
    schemaVersion=1,
    attributes=dict(
        portNumber=integer(),
        factory=reference(),
        parent=inmemory(),
        _listen=inmemory(),
        listeningPort=inmemory()))

registerAttributeCopyingUpgrader(TCPPort, 1, 2)



class SSLPort(PortMixin, Item):
    """
    An Axiom Service Item which will bind a TCP port to a protocol factory when
    it is started.
    """
    schemaVersion = 2

    portNumber = integer(doc="""
    The TCP port number on which to listen.
    """)

    interface = text(doc="""
    The hostname to bind to.
    """, default=u'')

    certificatePath = path(doc="""
    Name of the file containing the SSL certificate to use for this server.
    """)

    factory = reference(doc="""
    An Item with a C{getFactory} method which returns a Twisted protocol
    factory.
    """, whenDeleted=reference.CASCADE)

    parent = inmemory(doc="""
    A reference to the parent service of this service, whenever there is a
    parent.
    """)

    _listen = inmemory(doc="""
    An optional reference to a callable implementing the same interface as
    L{IReactorTCP.listenTCP}.  If set, this will be used to bind a network
    port.  If not set, the reactor will be imported and its C{listenTCP} method
    will be used.
    """)

    listeningPort = inmemory(doc="""
    A reference to the L{IListeningPort} returned by C{self.listen} which is
    set whenever there there is one listening.
    """)


    def getContextFactory(self):
        if SSL is None:
            raise RuntimeError("No SSL support: you need to install OpenSSL.")
        cert = PrivateCertificate.loadPEM(
            self.certificatePath.open().read())
        certOpts = CertificateOptions(
            cert.privateKey.original,
            cert.original,
            requireCertificate=False,
            method=SSL.SSLv23_METHOD)
        return certOpts


    def listen(self):
        if self._listen is not None:
            _listen = self._listen
        else:
            from twisted.internet import reactor
            _listen = reactor.listenSSL
        return _listen(
            self.portNumber,
            self.factory.getFactory(),
            self.getContextFactory(),
            interface=self.interface.encode('ascii'))

declareLegacyItem(
    typeName=normalize(qual(SSLPort)),
    schemaVersion=1,
    attributes=dict(
        portNumber=integer(),
        certificatePath=path(),
        factory=reference(),
        parent=inmemory(),
        _listen=inmemory(),
        listeningPort=inmemory()))

registerAttributeCopyingUpgrader(SSLPort, 1, 2)



__all__ = ['TCPPort', 'SSLPort']
