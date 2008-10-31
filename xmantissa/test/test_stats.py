# Copyright 2008 Divmod, Inc.  See LICENSE for details.

"""
Tests for L{xmantissa.stats}.
"""

from twisted.python import log, failure
from twisted.trial import unittest
from twisted.protocols.amp import ASK, COMMAND, Command, parseString

from axiom.iaxiom import IStatEvent
from axiom.store import Store
from axiom.plugins.mantissacmd import Mantissa

from xmantissa.stats import RemoteStatsCollectorFactory, RemoteStatsCollector
from xmantissa.test.test_ampserver import (
    BoxReceiverFactoryPowerupTestMixin, CollectingSender)
from xmantissa.web import SiteConfiguration



class RemoteStatsCollectorTest(BoxReceiverFactoryPowerupTestMixin, unittest.TestCase):
    """
    Tests for L{RemoteStatsCollectorFactory} and L{RemoteStatsCollector}.
    """
    factoryClass = RemoteStatsCollectorFactory
    protocolClass = RemoteStatsCollector

    def setUp(self):
        """
        Create and start a L{RemoteStatsCollector}.
        """
        self.receiver = RemoteStatsCollectorFactory().getBoxReceiver()
        self.sender = CollectingSender()
        self.receiver.startReceivingBoxes(self.sender)

    def test_deliverStatEvents(self):
        """
        When a L{RemoteStatsCollector} is active, it sends AMP boxes
        to its client when L{IStatEvent}s are logged.
        """
        log.msg(interface=IStatEvent, foo="bar", baz=12, quux=u'\N{SNOWMAN}')
        self.assertEqual(len(self.sender.boxes), 1)
        stat = self.sender.boxes[0]
        self.assertNotIn(ASK, stat)
        self.assertEqual(stat[COMMAND], 'StatUpdate')
        # Skip testing the timestamp, another test which can control its value
        # will do that.
        data = set([
                (d['key'], d['value'])
                for d in parseString(stat['data'])
                if d['key'] != 'time'])
        self.assertEqual(
            data,
            set([('foo', 'bar'), ('baz', '12'),
                 ('quux', u'\N{SNOWMAN}'.encode('utf-8'))]))


    def test_ignoreOtherEvents(self):
        """
        L{RemoteStatsCollection} does not send any boxes for events which don't
        have L{IStatEvent} as the value for their C{'interface'} key.
        """
        log.msg(interface="test log event")
        self.assertEqual(self.sender.boxes, [])


    def test_deliveryStopsAfterDisconnect(self):
        """
        After L{RemoteStatsCollection.stopReceivingBoxes} is called, it no
        longer observes L{IStatEvent} log messages.
        """
        self.receiver.stopReceivingBoxes(
            failure.Failure(Exception("test exception")))
        log.msg(interface=IStatEvent, foo="bar")
        self.assertEqual(self.sender.boxes, [])


    def test_disconnectFailsOutgoing(self):
        """
        L{RemoteStatsCollection.stopReceivingBoxes} causes the L{Deferred}
        associated with any outstanding command to fail with the reason given.
        """
        class DummyCommand(Command):
            pass

        d = self.receiver.callRemote(DummyCommand)
        self.receiver.stopReceivingBoxes(RuntimeError("test exception"))
        return self.assertFailure(d, RuntimeError)


    def test_timestamp(self):
        """
        L{RemoteStatsCollector._emit} sends a I{StatUpdate} command with a
        timestamp taken from the log event passed to it.
        """
        self.receiver._emit({
                'time': 123456789.0,
                'interface': IStatEvent})
        self.assertEqual(len(self.sender.boxes), 1)
        timestamp = [
            d['value']
            for d in parseString(self.sender.boxes[0]['data'])
            if d['key'] == 'time']
        self.assertEqual(timestamp, ['123456789.0'])


    def test_athena(self):
        """
        L{RemoteStatsCollector._emit} sends a I{StatUpdate} command with Athena
        transport data for Athena message send and receive events.
        """
        self.receiver._emit({
                'athena_send_messages': True,
                'count': 17})
        self.receiver._emit({
                'athena_received_messages': True,
                'count': 12})
        self.assertEqual(len(self.sender.boxes), 2)
        send = set([(d['key'], d['value'])
                    for d in parseString(self.sender.boxes[0]['data'])])
        self.assertEqual(
            send,
            set([('count', '17'), ('athena_send_messages', 'True')]))
        received = set([(d['key'], d['value'])
                        for d in parseString(self.sender.boxes[1]['data'])])
        self.assertEqual(
            received,
            set([('count', '12'), ('athena_received_messages', 'True')]))


class HTTPStatsEmitterTest(unittest.TestCase):
    """
    Tests for the production of HTTP stats.
    """

    def test_request(self):
        """
        When a response to an HTTP request is sent, the path, session key,
        response body size, and rendering time are reported.
        """


        self.siteStore = Store(filesdir=self.mktemp())
        Mantissa().installSite(self.siteStore, u'localhost', u"", False)
        self.site = self.siteStore.findUnique(SiteConfiguration)

        testdata = "some response data"
        testpath = "http://localhost/test/path"
        logMessages = []
        log.addObserver(logMessages.append)
        f = self.site.getFactory()
        class FakeChannel(object):
            site = f
        req = f.requestFactory(FakeChannel(), True)
        req.setHost('localhost', 80)
        req.args = {}
        req.path = testpath
        req._getTime = lambda: 1
        req.process()

        req.write(testdata)
        req._getTime = lambda: 2

        req.finishRequest(True)

        log.removeObserver(logMessages.append)

        self.assertEqual(len(logMessages), 2)
