# Copyright (c) 2008 Divmod.  See LICENSE for details.

"""
Tests for L{xmantissa.ampserver}.
"""

from zope.interface import Interface, implements
from zope.interface.verify import verifyObject

from twisted.python.failure import Failure
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ServerFactory
from twisted.cred.credentials import UsernamePassword
from twisted.protocols.amp import IBoxReceiver, IBoxSender
from twisted.trial.unittest import TestCase

from epsilon.ampauth import CredReceiver
from epsilon.amprouter import _ROUTE

from axiom.item import Item
from axiom.store import Store
from axiom.attributes import text, inmemory
from axiom.dependency import installOn
from axiom.userbase import LoginSystem

from xmantissa.ixmantissa import IProtocolFactoryFactory, IBoxReceiverFactory
from xmantissa.ampserver import (
    _RouteConnector, AMPConfiguration,
    AMPAvatar, ProtocolUnknown, Router, Connect, connectRoute,
    EchoFactory, EchoReceiver)

__metaclass__ = type


class AMPConfigurationTests(TestCase):
    """
    Tests for L{xmantissa.ampserver.AMPConfiguration} which defines how to
    create an L{AMP} server.
    """
    def setUp(self):
        """
        Create an in-memory L{Store} with an L{AMPConfiguration} in it.
        """
        self.store = Store()
        self.conf = AMPConfiguration(store=self.store)
        installOn(self.conf, self.store)


    def test_interfaces(self):
        """
        L{AMPConfiguration} implements L{IProtocolFactoryFactory}.
        """
        self.assertTrue(verifyObject(IProtocolFactoryFactory, self.conf))


    def test_powerup(self):
        """
        L{ionstallOn} powers up the target for L{IProtocolFactoryFactory} with
        L{AMPConfiguration}.
        """
        self.assertIn(
            self.conf, list(self.store.powerupsFor(IProtocolFactoryFactory)))


    def test_getFactory(self):
        """
        L{AMPConfiguration.getFactory} returns a L{ServerFactory} instance
        which returns L{CredReceiver} instances from its C{buildProtocol}
        method.
        """
        factory = self.conf.getFactory()
        self.assertTrue(isinstance(factory, ServerFactory))
        protocol = factory.buildProtocol(None)
        self.assertTrue(isinstance(protocol, CredReceiver))


    def test_portal(self):
        """
        L{AMPConfiguration.getFactory} returns a factory which creates
        protocols which have a C{portal} attribute which is a L{Portal} which
        authenticates and authorizes using L{axiom.userbase}.
        """
        factory = self.conf.getFactory()
        protocol = factory.buildProtocol(None)
        portal = protocol.portal

        localpart = u'alice'
        domain = u'example.org'
        password = u'foobar'

        class IDummy(Interface):
            pass

        loginSystem = self.store.findUnique(LoginSystem)
        account = loginSystem.addAccount(
            localpart, domain, password,internal=True)
        subStore = account.avatars.open()
        avatar = object()
        subStore.inMemoryPowerUp(avatar, IDummy)
        login = portal.login(
            UsernamePassword(
                '%s@%s' % (localpart.encode('ascii'), domain.encode('ascii')),
                password),
            None, IDummy)
        def cbLoggedIn(result):
            self.assertIdentical(IDummy, result[0])
            self.assertIdentical(avatar, result[1])
        login.addCallback(cbLoggedIn)
        return login



class CollectingSender:
    """
    An L{IBoxSender} which collects and saves boxes and errors sent to it.
    """
    implements(IBoxSender)

    def __init__(self):
        self.boxes = []
        self.errors = []


    def sendBox(self, box):
        """
        Reject boxes with non-string keys or values; save all the rest in
        C{self.boxes}.
        """
        for k, v in box.iteritems():
            if not (isinstance(k, str) and isinstance(v, str)):
                raise TypeError("Cannot send boxes containing non-strings")
        self.boxes.append(box)


    def unhandledError(self, failure):
        self.errors.append(failure.getErrorMessage())



class SomeReceiver:
    sender = None
    reason = None
    started = False
    stopped = False

    def __init__(self):
        self.boxes = []


    def startReceivingBoxes(self, sender):
        self.started = True
        self.sender = sender


    def ampBoxReceived(self, box):
        if self.started and not self.stopped:
            self.boxes.append(box)


    def stopReceivingBoxes(self, reason):
        self.stopped = True
        self.reason = reason






class StubBoxReceiverFactory(Item):
    """
    L{IBoxReceiverFactory}
    """
    protocol = text()

    receivers = inmemory()

    def activate(self):
        self.receivers = []


    def getBoxReceiver(self):
        receiver = SomeReceiver()
        self.receivers.append(receiver)
        return receiver



class AMPAvatarTests(TestCase):
    """
    Tests for L{AMPAvatar} which provides an L{IBoxReceiver} implementation
    that supports routing messages to other L{IBoxReceiver} implementations.
    """
    def setUp(self):
        """
        Create a L{Store} with an L{AMPAvatar} installed on it.
        """
        self.store = Store()
        self.avatar = AMPAvatar(store=self.store)
        installOn(self.avatar, self.store)
        self.factory = StubBoxReceiverFactory(
            store=self.store, protocol=u"bar")
        self.store.powerUp(self.factory, IBoxReceiverFactory)


    def test_interface(self):
        """
        L{AMPAvatar} powers up the item on which it is installed for
        L{IBoxReceiver} and indirects that interface to the real router
        implementation of L{IBoxReceiver}.
        """
        router = IBoxReceiver(self.store)
        self.assertTrue(verifyObject(IBoxReceiver, router))
        self.assertNotIdentical(self.avatar, router)


    def test_connectorStarted(self):
        """
        L{AMPAvatar.indirect} returns a L{Router} with a started route
        connector as its default receiver.
        """
        receiver = SomeReceiver()
        self.avatar.__dict__['connectorFactory'] = lambda router: receiver
        router = self.avatar.indirect(IBoxReceiver)
        router.startReceivingBoxes(object())
        self.assertTrue(receiver.started)



class RouteConnectorTests(TestCase):
    """
    Tests for L{_RouteConnector}.
    """
    def setUp(self):
        """
        Create a L{Store} with an L{AMPAvatar} installed on it.
        """
        self.store = Store()
        self.factory = StubBoxReceiverFactory(
            store=self.store, protocol=u"bar")
        self.store.powerUp(self.factory, IBoxReceiverFactory)
        self.router = Router()
        self.sender = CollectingSender()
        self.connector = _RouteConnector(self.store, self.router)
        self.router.startReceivingBoxes(self.sender)
        self.router.bindRoute(self.connector, None)


    def test_accept(self):
        """
        L{_RouteConnector.accept} returns a C{dict} with a C{'route'} key
        associated with a new route identifier which may be used to send AMP
        boxes to a new instance of the L{IBoxReceiver} indicated by the
        C{protocol} argument passed to C{connect}.
        """
        firstIdentifier = self.connector.accept(
            "first origin", u"bar")['route']
        firstReceiver = self.factory.receivers.pop()
        secondIdentifier = self.connector.accept(
            "second origin", u"bar")['route']
        secondReceiver = self.factory.receivers.pop()

        self.router.ampBoxReceived(
            {_ROUTE: firstIdentifier, 'foo': 'bar'})
        self.router.ampBoxReceived(
            {_ROUTE: secondIdentifier, 'baz': 'quux'})

        self.assertEqual(firstReceiver.boxes, [{'foo': 'bar'}])
        self.assertEqual(secondReceiver.boxes, [{'baz': 'quux'}])


    def test_unknownProtocol(self):
        """
        L{_RouteConnector.accept} raises L{ProtocolUnknown} if passed the name
        of a protocol for which no factory can be found.
        """
        self.assertRaises(
            ProtocolUnknown, self.connector.accept, "origin", u"foo")


    def test_originRoute(self):
        """
        The L{IBoxReceiver}s created by L{_RouteConnector.accept} are started with
        L{IBoxSender}s which are associated with the origin route specified to
        C{accept}.
        """
        origin = u'origin route'
        self.connector.accept(origin, u'bar')

        [bar] = self.factory.receivers
        self.assertTrue(bar.started)
        bar.sender.sendBox({'foo': 'bar'})
        self.assertEqual(self.sender.boxes, [{_ROUTE: origin, 'foo': 'bar'}])

        bar.sender.unhandledError(Failure(RuntimeError("test failure")))
        self.assertEqual(self.sender.errors, ["test failure"])



class ConnectRouteTests(TestCase):
    """
    Tests for L{connectRoute} which implements Mantissa-specific route creation
    logic.
    """
    def test_connectRoute(self):
        """
        L{connectRoute} takes an L{AMP}, a L{Router}, an L{IBoxReceiver} and a
        protocol name and issues a L{Connect} command for that protocol and for
        a newly created route associated with the given receiver over the
        L{AMP}.
        """
        commands = []
        results = []
        class FakeAMP:
            def callRemote(self, cmd, **kw):
                commands.append((cmd, kw))
                results.append(Deferred())
                return results[-1]

        amp = FakeAMP()
        sender = CollectingSender()
        router = Router()
        router.startReceivingBoxes(sender)

        receiver = SomeReceiver()
        protocol = u"proto name"

        d = connectRoute(amp, router, receiver, protocol)

        self.assertEqual(
            commands, [(Connect, {'origin': u'0', 'protocol': u'proto name'})])
        results[0].callback({'route': u'remote route'})

        def cbConnected(receiverAgain):
            self.assertIdentical(receiver, receiverAgain)
            self.assertTrue(receiver.started)

            receiver.sender.sendBox({'foo': 'bar'})
            self.assertEqual(
                sender.boxes, [{_ROUTE: 'remote route', 'foo': 'bar'}])
            router.ampBoxReceived({_ROUTE: '0', 'baz': 'quux'})
            self.assertEqual(receiver.boxes, [{'baz': 'quux'}])
        d.addCallback(cbConnected)
        return d



class BoxReceiverFactoryPowerupTestMixin:
    """
    Common tests for implementors of L{IBoxReceiverFactory}.

    @ivar factoryClass: the L{IBoxReceiverFactory} implementor.
    @ivar protocolClass: An L{IBoxReceiver} implementor.
    """

    def test_factoryInterfaces(self):
        """
        C{self.factoryClass} instances provide L{IBoxReceiverFactory}.
        """
        self.assertTrue(verifyObject(IBoxReceiverFactory, self.factoryClass()))


    def test_factoryPowerup(self):
        """
        When installed, C{self.factoryClass} is a powerup for L{IBoxReceiverFactory}.
        """
        store = Store()
        factory = self.factoryClass(store=store)
        installOn(factory, store)
        self.assertEqual(
            list(store.powerupsFor(IBoxReceiverFactory)),
            [factory])


    def test_getBoxReceiver(self):
        """
        C{self.factoryClass.getBoxReceiver} returns an instance of C{self.protocolClass}.
        """
        receiver = self.factoryClass().getBoxReceiver()
        self.assertTrue(isinstance(receiver, self.protocolClass))


    def test_receiverInterfaces(self):
        """
        C{self.protocolClass} instances provide L{IBoxReceiver}.
        """
        self.assertTrue(verifyObject(IBoxReceiver, self.protocolClass()))



class EchoTests(BoxReceiverFactoryPowerupTestMixin, TestCase):
    """
    Tests for L{EchoFactory} and L{EchoReceiver}, classes which provide a
    simple AMP echo protocol for a Mantissa AMP server.
    """

    factoryClass = EchoFactory
    protocolClass = EchoReceiver

    def test_ampBoxReceived(self):
        """
        L{EchoReceiver.ampBoxReceived} sends the received box back to the
        sender.
        """
        sender = CollectingSender()
        receiver = EchoReceiver()
        receiver.startReceivingBoxes(sender)
        receiver.ampBoxReceived({'foo': 'bar'})
        self.assertEqual(sender.boxes, [{'foo': 'bar'}])
        receiver.stopReceivingBoxes(Failure(Exception("test exception")))
