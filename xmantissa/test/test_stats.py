"""
Tests for L{xmantissa.stats}.
"""

from twisted.python import log
from twisted.internet import defer
from twisted.trial import unittest
from twisted.application.service import IService

from epsilon.extime import Time
from epsilon import juice

from axiom.store import Store
from axiom.scheduler import Scheduler
from axiom import attributes, iaxiom
from axiom.dependency import installOn

from xmantissa import stats
from xmantissa.stats import StatsService


class StatCollectorTest(unittest.TestCase):
    """
    Tests for L{xmantissa.stats.StatsService}.
    """
    def setUp(self):
        """
        Create a store with a scheduler and a stats service and start the
        store's service.
        """
        self.store = Store()
        # should this break something? it should break something.
        self.store.parent = self.store

        self.scheduler = Scheduler(store=self.store)
        installOn(self.scheduler, self.store)

        self.statService = StatsService(store=self.store)
        installOn(self.statService, self.store)

        IService(self.store).startService()


    def tearDown(self):
        """
        Stop the store's service.
        """
        return IService(self.store).stopService()
    

    def test_statCollectionAndRecording(self):
        """
        Logging an L{iaxiom.IStatEvent} should result in the creation of a
        L{stats.StatBucket} with minute resolution and a type corresponding
        to the C{stat_} key in the log event dictionary.
        """
        log.msg(interface=iaxiom.IStatEvent, stat_foo=17)
        self.store.findUnique(stats.StatSampler).run()
        minutebucket = list(
            self.store.query(
                stats.StatBucket,
                attributes.AND(stats.StatBucket.type == u"foo",
                               stats.StatBucket.interval == u"minute")))
        self.assertEquals(len(minutebucket), 1)
        self.assertEquals(minutebucket[0].value, 17)



class FakeProtocol(juice.Juice):
    sent = False
    def sendBoxCommand(self, command, box, requiresAnswer=True):
        self.sent = True
class RemoteStatCollectorTest(unittest.TestCase):

    def testUpdates(self):
        r = stats.RemoteStatsObserver(hostname="fred", port=1)
        r.protocol = FakeProtocol(False)
        r.statUpdate(Time(), [("candy bars", 17), ("enchiladas", 2)])
        self.assertEquals(r.protocol.sent, True)

    def testConnecting(self):
        self.connected = False

        def win(_):
            self.connected = True
            return defer.Deferred()
        f = stats.RemoteStatsObserver._connectToStatsServer
        stats.RemoteStatsObserver._connectToStatsServer = win
        r = stats.RemoteStatsObserver (hostname="fred", port=1)
        r.activate()
        r.statUpdate(Time(), [("candy bars", 17), ("enchiladas", 2)])
        self.assertEquals(self.connected, True)
        stats.RemoteStatsObserver._connectToStatsServer = f
