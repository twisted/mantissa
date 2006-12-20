import StringIO
from twisted.python import log
from twisted.internet import defer
from twisted.trial import unittest
from axiom import store, attributes, scheduler, iaxiom
from axiom.dependency import installOn

from xmantissa import stats
from epsilon.extime import Time
from epsilon import juice
class StatCollectorTest(unittest.TestCase):

    def testStatCollectionAndRecording(self):
        s = store.Store()
        s.parent = s #should this break something? it should break something.
        installOn(scheduler.Scheduler(store=s), s)
        svc = stats.StatsService(store=s)
        installOn(svc, s)
        log.msg(interface=iaxiom.IStatEvent, stat_foo=17)
        s.findUnique(stats.StatSampler).run()
        minutebucket = list(s.query(stats.StatBucket, attributes.AND(stats.StatBucket.type == u"foo",
                                                                     stats.StatBucket.interval == u"minute")))
        self.assertEquals(len(minutebucket), 1)
        self.assertEquals(minutebucket[0].value, 17)
        svc.stopService()

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
