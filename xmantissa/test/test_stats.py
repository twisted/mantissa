from twisted.python import log
from twisted.trial import unittest
from axiom import store, attributes, scheduler, iaxiom
from xmantissa import stats

class StatCollectorTest(unittest.TestCase):

    def testStatCollectionAndRecording(self):
        s = store.Store()
        s.parent = s #should this break something? it should break something.
        scheduler.Scheduler(store=s).installOn(s)
        svc = stats.StatsService(store=s)
        svc.installOn(s)
        log.msg(interface=iaxiom.IStatEvent, stat_foo=17)
        s.findUnique(stats.StatSampler).run()
        minutebucket = list(s.query(stats.StatBucket, attributes.AND(stats.StatBucket.type == u"foo",
                                                                     stats.StatBucket.interval == u"minute")))
        self.assertEquals(len(minutebucket), 1)
        self.assertEquals(minutebucket[0].value, 17)
        svc.stopService()
