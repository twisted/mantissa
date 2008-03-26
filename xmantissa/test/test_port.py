
"""
Tests for L{xmantissa.port}.
"""

from twisted.trial.unittest import TestCase
from twisted.application.service import IService, IServiceCollection
from twisted.internet.protocol import ServerFactory
from twisted.internet.defer import Deferred
from twisted.internet.ssl import CertificateOptions

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import inmemory, integer
from axiom.dependency import installOn

from xmantissa.port import TCPPort, SSLPort


class DummyPort(object):
    """
    Stub class used to track what reactor listen calls have been made and what
    created ports have been stopped.
    """
    stopping = None

    def __init__(self, portNumber, factory, contextFactory=None, interface=''):
        self.portNumber = portNumber
        self.factory = factory
        self.contextFactory = contextFactory
        self.interface = interface


    def stopListening(self):
        assert self.stopping is None
        self.stopping = Deferred()
        return self.stopping



class DummyFactory(Item):
    """
    Helper class used as a stand-in for a real protocol factory by the unit
    tests.
    """
    dummyAttribute = integer(doc="""
    Meaningless attribute which serves only to make this a valid Item subclass.
    """)

    realFactory = inmemory(doc="""
    A reference to the protocol factory which L{getFactory} will return.
    """)

    def getFactory(self):
        return self.realFactory



class PortTestsMixin:
    """
    Test method-defining mixin class for port types with C{portNumber} and
    C{factory} attributes.

    Included are tests for various persistence-related behaviors as well as the
    L{IService} implementation which all ports should have.

    @ivar portType: The L{Item} subclass which will be tested.

    @ivar lowPortNumber: A port number which requires privileges to bind on
    POSIX.  Used to test L{privilegedStartService}.

    @ivar highPortNumber: A port number which does not require privileges to
    bind on POSIX.  Used to test the interaction between
    L{privilegedStartService} and L{startService}.

    @ivar dbdir: The path at which to create the test L{Store}.  This must be
    bound before L{setUp} is run, since that is the only method which examines
    its value.

    @ivar ports: A list of ports which have been bound using L{listen}.
    created in L{setUp}.
    """
    portType = None

    lowPortNumber = 123
    highPortNumber = 1234
    someInterface = u'127.0.0.1'

    def port(self, **kw):
        """
        Create and return a new port instance with the given attribute values.
        """
        return self.portType(**kw)


    def listen(self, *a, **kw):
        """
        Pretend to bind a port.  Used as a stub implementation of a reactor
        listen method.  Subclasses should override and implement to append
        useful information to C{self.ports}.
        """
        raise NotImplementedError


    def checkPort(self, port, alternatePort=None):
        """
        Assert that the given port has been properly created.

        @type port: L{DummyPort}
        @param port: A port which has been created by the code being tested.

        @type alternatePort: C{int}
        @param alternatePort: If not C{None}, the port number on which C{port}
        should be listening.
        """
        raise NotImplementedError


    def setUp(self):
        self.filesdir = self.mktemp()
        self.store = Store(filesdir=self.filesdir)
        self.realFactory = ServerFactory()
        self.factory = DummyFactory(store=self.store, realFactory=self.realFactory)
        self.ports = []


    def test_portNumberAttribute(self):
        """
        Test that C{self.portType} remembers the port number it is told to
        listen on.
        """
        port = self.port(store=self.store, portNumber=self.lowPortNumber)
        self.assertEqual(port.portNumber, self.lowPortNumber)


    def test_interfaceAttribute(self):
        """
        Test that C{self.portType} remembers the interface it is told to listen
        on.
        """
        port = self.port(store=self.store, interface=self.someInterface)
        self.assertEqual(port.interface, self.someInterface)


    def test_factoryAttribute(self):
        """
        Test that C{self.portType} remembers the factory it is given to associate
        with its port.
        """
        port = self.port(store=self.store, factory=self.factory)
        self.assertIdentical(port.factory, self.factory)


    def test_service(self):
        """
        Test that C{self.portType} becomes a service on the store it is installed on.
        """
        port = self.port(store=self.store)
        installOn(port, self.store)

        self.assertEqual(
            list(self.store.powerupsFor(IService)),
            [port])


    def test_setServiceParent(self):
        """
        Test that the C{self.portType.setServiceParent} method adds the C{self.portType} to
        the Axiom Store Service as a child.
        """
        port = self.port(store=self.store)
        port.setServiceParent(self.store)
        self.failUnlessIn(port, list(IService(self.store)))


    def test_disownServiceParent(self):
        """
        Test that the C{self.portType.disownServiceParent} method removes the
        C{self.portType} from the Axiom Store Service.
        """
        port = self.port(store=self.store)
        port.setServiceParent(self.store)
        port.disownServiceParent()
        self.failIfIn(port, list(IService(self.store)))


    def test_serviceParent(self):
        """
        Test that C{self.portType} is a child of the store service after it is
        installed.
        """
        port = self.port(store=self.store)
        installOn(port, self.store)

        service = IServiceCollection(self.store)
        self.failUnlessIn(port, list(service))


    def _start(self, portNumber, methodName):
        port = self.port(store=self.store, portNumber=portNumber, factory=self.factory)
        port._listen = self.listen
        getattr(port, methodName)()
        return self.ports


    def _privilegedStartService(self, portNumber):
        return self._start(portNumber, 'privilegedStartService')


    def _startService(self, portNumber):
        return self._start(portNumber, 'startService')


    def test_startPrivilegedService(self):
        """
        Test that C{self.portType} binds a low-numbered port with the reactor when it
        is started with privilege.
        """
        ports = self._privilegedStartService(self.lowPortNumber)
        self.assertEqual(len(ports), 1)
        self.checkPort(ports[0])


    def test_dontStartPrivilegedService(self):
        """
        Test that C{self.portType} doesn't bind a high-numbered port with the
        reactor when it is started with privilege.
        """
        ports = self._privilegedStartService(self.highPortNumber)
        self.assertEqual(ports, [])


    def test_startServiceLow(self):
        """
        Test that C{self.portType} binds a low-numbered port with the reactor
        when it is started without privilege.
        """
        ports = self._startService(self.lowPortNumber)
        self.assertEqual(len(ports), 1)
        self.checkPort(ports[0])


    def test_startServiceHigh(self):
        """
        Test that C{self.portType} binds a high-numbered port with the reactor
        when it is started without privilege.
        """
        ports = self._startService(self.highPortNumber)
        self.assertEqual(len(ports), 1)
        self.checkPort(ports[0], self.highPortNumber)


    def test_startServiceNoInterface(self):
        """
        Test that C{self.portType} binds to all interfaces if no interface is
        explicitly specified.
        """
        port = self.port(store=self.store, portNumber=self.highPortNumber, factory=self.factory)
        port._listen = self.listen
        port.startService()
        self.assertEqual(self.ports[0].interface, '')


    def test_startServiceInterface(self):
        """
        Test that C{self.portType} binds to only the specified interface when
        instructed to.
        """
        port = self.port(store=self.store, portNumber=self.highPortNumber, factory=self.factory, interface=self.someInterface)
        port._listen = self.listen
        port.startService()
        self.assertEqual(self.ports[0].interface, self.someInterface)


    def test_startedOnce(self):
        """
        Test that C{self.portType} only binds one network port when
        C{privilegedStartService} and C{startService} are both called.
        """
        port = self.port(store=self.store, portNumber=self.lowPortNumber, factory=self.factory)
        port._listen = self.listen
        port.privilegedStartService()
        self.assertEqual(len(self.ports), 1)
        self.checkPort(self.ports[0])
        port.startService()
        self.assertEqual(len(self.ports), 1)


    def test_stopService(self):
        """
        Test that C{self.portType} cleans up its listening port when it is stopped.
        """
        port = self.port(store=self.store, portNumber=self.lowPortNumber, factory=self.factory)
        port._listen = self.listen
        port.startService()
        stopped = port.stopService()
        stopping = self.ports[0].stopping
        self.failIfIdentical(stopping, None)
        self.assertIdentical(stopped, stopping)


    def test_deletedFactory(self):
        """
        Test that the deletion of a C{self.portType}'s factory item results in the
        C{self.portType} being deleted.
        """
        port = self.port(store=self.store, portNumber=self.lowPortNumber, factory=self.factory)
        self.factory.deleteFromStore()
        self.assertEqual(list(self.store.query(self.portType)), [])


    def test_deletionDisownsParent(self):
        """
        Test that a deleted C{self.portType} no longer shows up in the children list
        of the service which used to be its parent.
        """
        port = self.port(store=self.store, portNumber=self.lowPortNumber, factory=self.factory)
        port.setServiceParent(self.store)
        port.deleteFromStore()
        service = IServiceCollection(self.store)
        self.failIfIn(port, list(service))



class TCPPortTests(PortTestsMixin, TestCase):
    """
    Tests for L{xmantissa.port.TCPPort}.
    """
    portType = TCPPort


    def checkPort(self, port, alternatePort=None):
        if alternatePort is None:
            alternatePort = self.lowPortNumber
        self.assertEqual(port.portNumber, alternatePort)
        self.assertEqual(port.factory, self.realFactory)


    def listen(self, port, factory, interface=''):
        self.ports.append(DummyPort(port, factory, interface=interface))
        return self.ports[-1]



class SSLPortTests(PortTestsMixin, TestCase):
    """
    Tests for L{xmantissa.port.SSLPort}.
    """
    portType = SSLPort

    dummyCertificateData = """
-----BEGIN CERTIFICATE-----
MIICmTCCAgICAQEwDQYJKoZIhvcNAQEEBQAwgZQxCzAJBgNVBAYTAlVTMRQwEgYD
VQQDEwtleGFtcGxlLmNvbTERMA8GA1UEBxMITmV3IFlvcmsxEzARBgNVBAoTCkRp
dm1vZCBMTEMxETAPBgNVBAgTCE5ldyBZb3JrMSIwIAYJKoZIhvcNAQkBFhNzdXBw
b3J0QGV4YW1wbGUuY29tMRAwDgYDVQQLEwdUZXN0aW5nMB4XDTA2MTIzMDE5MDEx
NloXDTA3MTIzMDE5MDExNlowgZQxCzAJBgNVBAYTAlVTMRQwEgYDVQQDEwtleGFt
cGxlLmNvbTERMA8GA1UEBxMITmV3IFlvcmsxEzARBgNVBAoTCkRpdm1vZCBMTEMx
ETAPBgNVBAgTCE5ldyBZb3JrMSIwIAYJKoZIhvcNAQkBFhNzdXBwb3J0QGV4YW1w
bGUuY29tMRAwDgYDVQQLEwdUZXN0aW5nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCB
iQKBgQCrmNNyXLHAETcDH8Uxhmbo8IhFFMx1C4i7oTHTKsmD84E3YFj/RdByrWrG
TL4XskALpfmw1+LxQmMO8n4sIsN3QmjkAWhFhMEquKv6NNN+sRo6vF+ytEasuYn/
7gY/iT7LYqUmKWckBsPYzT9elyOXi6miI0tFdeyfXRSxOslKewIDAQABMA0GCSqG
SIb3DQEBBAUAA4GBABotNizqPoGWIG5BMsl8lxseqiw/8AwvoiQNpYTrC8W+Umsg
oZEaMuVkf/NDJEa3TXdYcAzkFwGN9Cn/WCgHEkLxIZ66aHV0bfcE7YJjHRDrrLiY
chPndOGGrD3iTuWaGnauUcsjJ+RsxqHMBu6NRQYgkoYNsOr0UA1ek7O1vjMy
-----END CERTIFICATE-----
-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQCrmNNyXLHAETcDH8Uxhmbo8IhFFMx1C4i7oTHTKsmD84E3YFj/
RdByrWrGTL4XskALpfmw1+LxQmMO8n4sIsN3QmjkAWhFhMEquKv6NNN+sRo6vF+y
tEasuYn/7gY/iT7LYqUmKWckBsPYzT9elyOXi6miI0tFdeyfXRSxOslKewIDAQAB
AoGAHd9YCBOs+gPFMO0J9iowpiKhhm0tfr7ISemw89MCC8+LUimatK3hsOURrn3T
peppDd4SDsA2iMuG1SZP4r0Wi9ZncZ+uj6KfVHg6rJZRDW2cPsGNyBw2HO8pFxnh
NsfxioutzCqJ9A0KwqSNQsBpOAlRWzP13+/W5wYAGK+yrLECQQDYgOhVR+1KOhty
CI0NVITNFL5IOZ254Eu46qbEGwPNJvkzdp+Wx5gsfCip9aiZgw3LMEeGXu9P1C4N
AqDM4uozAkEAyua0F0nCRLzjLAAw4odC+vA6jnq6K4M7QT6cQVwmrxgOj6jGEOGu
eaoWbXi2bKcxOGBNDZW0PVKmpq4hZblmmQJBALwFP0AIxg+HZRxkRrMD6oz77cBl
oQ+ytbAywH9ggq2gohzKcRAN6J8BeIMZn8EpqkoCdKtCOQyX1SJhXOpySjcCQDds
mZka7tQz/KISU0gtxqAhav1sjNpB+Lez0J8R+wctPR0E70XBQBW/3mx84uf/K7TI
qYOidx+hKiCxxDGzWVECQHNVutQ1ABjmv6EDJTo28QQsm5hNbfS+tVY3bSihNjLM
Y+O7ib90LsqfQ8r0GUphQVi4EA4QMJqaF7ZxKms79qA=
-----END RSA PRIVATE KEY-----
    """

    def checkPort(self, port, alternatePort=None):
        if alternatePort is None:
            alternatePort = self.lowPortNumber
        self.assertEqual(port.portNumber, alternatePort)
        self.assertEqual(port.factory, self.realFactory)
        self.failUnless(isinstance(port.contextFactory, CertificateOptions))


    def port(self, certificatePath=None, **kw):
        if certificatePath is None:
            certificatePath = self.store.newFilePath('certificate.pem')
            assert not certificatePath.exists()
            certificatePath.setContent(self.dummyCertificateData)
        return self.portType(certificatePath=certificatePath, **kw)


    def listen(self, port, factory, contextFactory, interface=''):
        self.ports.append(DummyPort(port, factory, contextFactory, interface=interface))
        return self.ports[-1]


    def test_certificatePathAttribute(self):
        """
        Test that L{SSLPort} remembers the certificate filename it is given.
        """
        certificatePath = self.store.newFilePath('foo', 'bar')
        port = self.port(store=self.store, certificatePath=certificatePath)
        self.assertEqual(port.certificatePath, certificatePath)
