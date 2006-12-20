# -*- test-case-name: quotient.test.test_stats -*-
# Copyright 2005 Divmod, Inc.  See LICENSE file for details

"""

Statistics collection and recording facility.

Primarily this is a system for handling time-series data such as
"mail messages received per minute". The idea is that you call the
Twisted logger with the stat values to be recorded, and the given
values will be added to the collector. Once a minute, these values are
stored in the database; each stat has a set of StatBuckets that are
reused for per-minute stats, keeping values for a week. Every 15
minutes, these values are totalled; the 15-minute totals are kept for
a month. Finally, daily stats are recorded, and kept indefinitely.

Example::
  twisted.python.log.msg(interface=axiom.iaxiom.IStatEvent,
                         userstore=store, stat_foo=1, stat_bar=2, ...)

The 'userstore' argument, if present, indicates the store to record
per-user stats in, in addition to the global stats.

The statDescriptions dict in this module maps stat names (such as
'foo' or 'bar' here) to human-readable descriptions.

See L{xmantissa.webadmin.AdminStatsFragment} for the code that graphs
these stats in the admin page.
"""

import time, datetime, itertools

from twisted.internet import reactor, protocol
from twisted.application import service
from twisted.protocols import policies
from twisted.python import log

from axiom import iaxiom, item, attributes, errors, userbase, upgrade
from epsilon.extime import Time
from xmantissa.offering import getInstalledOfferings
from epsilon import juice

statDescriptions = {
    "page_renders": "Nevow page renders per minute",
    "messages_grabbed": "POP3 messages grabbed per minute",
    "messagesSent": "SMTP messages sent per minute",
    "messagesReceived": "SMTP messages received per minute",
    "mimePartsCreated": "MIME parts created per minute",
    "cache_hits": "Axiom cache hits per minute",
    "cursor_execute_time": "Seconds spent in cursor.execute per minute",
    "cursor_blocked_time": ("Seconds spent waiting for the database lock per "
                            "minute"),
    "commits": "Axiom commits per minute",
    "cache_misses": "Axiom cache misses per minute",
    "autocommits": "Axiom autocommits per minute",
    "athena_messages_sent": "Athena messages sent per minute",
    "athena_messages_received": "Athena messages received per minute",

    "actionDuration": "Seconds/Minute spent executing Imaginary Commands",
    "actionExecuted": "Imaginary Commands/Minute executed",

    "bandwidth_http_up": "HTTP KB/sec received",
    "bandwidth_http_down": "HTTP KB/sec sent",
    "bandwidth_https_up": "HTTPS KB/sec sent",
    "bandwidth_https_down": "HTTPS KB/sec received",
    "bandwidth_pop3_up": "POP3 server KB/sec sent",
    "bandwidth_pop3_down":"POP3 server KB/sec received",
    "bandwidth_pop3s_up":"POP3S server KB/sec sent",
    "bandwidth_pop3s_down": "POP3S server KB/sec received",
    "bandwidth_smtp_up": "SMTP server KB/sec sent",
    "bandwidth_smtp_down": "SMTP server KB/sec received",
    "bandwidth_smtps_up": "SMTPS server KB/sec sent",
    "bandwidth_smtps_down": "SMTPS server KB/sec received",
    "bandwidth_pop3-grabber_up": "POP3 grabber KB/sec sent",
    "bandwidth_pop3-grabber_down": "POP3 grabber KB/sec received",
    "bandwidth_sip_up": "SIP KB/sec sent",
    "bandwidth_sip_down": "SIP KB/sec received",
    "bandwidth_telnet_up": "Telnet KB/sec sent",
    "bandwidth_telnet_down": "Telnet KB/sec received",
    "bandwidth_ssh_up": "SSH KB/sec sent",
    "bandwidth_ssh_down": "SSH KB/sec received",

    "Imaginary logins": "Imaginary Logins/Minute",
    "Web logins": "Web Logins/Minute",
    "SMTP logins": "SMTP Logins/Minute",
    "POP3 logins": "POP3 Logins/Minute",
    }

MAX_MINUTES = 24 * 60 * 7 # a week of minutes

class Statoscope(object):
    """A thing useful for metering the rate of stuff over time.

    A Statoscope instance tracks two things:
        - elapsed time
        - a count of any number of stuffs
    'stuffs' are things that happen over time. For example they may be 'bytes'
    or 'messages'.

    parameters:
    - name: The sort of thing this scope tracks. Example: "POP grabber"
    - user: The responsible user, or None for things that can't be blamed on
      only one user.
    - elapsed: the initial elapsed time.
    - stuffs: a dict of initial stuff counts, or None.
    """

    def __init__(self, name, user=None, elapsed=0., stuffs=None):
        self.name = name
        self.user = user
        self._stuffs = {}
        self.reset(elapsed, stuffs)

    def copy(self):
        """Return a mostly-deep copy of self."""
        return Statoscope(self.name, self.user, self.elapsed(), self._stuffs.copy())

    def reset(self, elapsed=0., stuffs=None):
        """Reset the elapsed time and count of stuffs."""
        self._mark = None
        self._time = elapsed
        if stuffs:
            self._stuffs = stuffs.copy()
        else:
            self._stuffs = dict.fromkeys(self._stuffs.iterkeys(), 0)

    def start(self):
        """Start the internal timer."""
        self._checkpointTimer()
        self._mark = time.time()

    def stop(self):
        """Stop the internal timer."""
        assert self._mark is not None
        self._time += time.time() - self._mark
        self._mark = None

    def record(self, **kw):
        """Record a number of stuffs.

        example: scope.record(bytes=4238, messages=3)
        """
        for k, v in kw.iteritems():
            try:
                self._stuffs[k] += v
            except KeyError:
                self._stuffs[k] = v

    def rate(self, stuff):
        """Return the count of stuff divided by the elapsed time."""
        self._checkpointTimer()
        return self._stuffs[stuff]/self._time

    def total(self, stuff):
        """Return the total number of stuff recorded."""
        return self._stuffs[stuff]

    def elapsed(self):
        """Return the seconds elapsed on the internal timer."""
        self._checkpointTimer()
        return self._time

    def setElapsed(self, time):
        """Set the elapsed time."""
        self._time = time

    def getHumanlyChoices(self):
        """Return a list of possible stuffs for getHumanlyStuff."""
        stuffs = ['elapsed']
        for stuff in self._stuffs:
            stuffs.append(stuff)
            stuffs.append(stuff+'/s')
        return stuffs

    def getHumanlyStuff(self, stuff):
        """Get a stuff with a name a human might use.

        Stuff should be one of the possibilites enumerated by getHumanlyChoices.
        """
        if stuff == 'elapsed':
            return self.elapsed()
        elif stuff[-2:] == '/s':
            stuff = stuff[:-2]
            return self.rate(stuff)
        else:
            return self.total(stuff)

    def _checkpointTimer(self):
        if self._mark is not None:
            now = time.time()
            elapsed = now - self._mark
            self._mark = now
            self._time += elapsed

    def __repr__(self):
        self._checkpointTimer()
        return 'stats.Statoscope(%(name)r, %(user)r, %(_time)r, %(_stuffs)r)' % vars(self)

    def __str__(self):
        if self.user:
            user = ', user %r' % (self.user,)
        else:
            user = ''
        s = 'stats for %r%s\n' % (self.name, user)
        if not self._time:
            s += '%s elapsed\n' % (formatSize(self._time, 's'),)
            for stuff, value in self._stuffs.iteritems():
                s += '%s\n' % (formatSize(value, stuff),)
            return s
        else:
            s += '%s elapsed\n' % (formatSize(self._time, 's'),)
            for stuff, value in self._stuffs.iteritems():
                s += '%s\t%s\n' % (formatSize(value/self._time, stuff+'/s'), formatSize(value, stuff))
            return s



def plural(n):
    return "%g" % (n,) != "1" and "s" or ""

def formatSize(size, suffix='', pluralize=False, base10=None, fractionalDigits=None, forceSIPrefixes=False):
    """Convert a number to a string with a metric prefix.

    @suffix: the suffix to put after the computed prefix, like "bytes" or "b"

    @pluralize: iff True, add "s" to suffix when appropiate and use "kilo"
    instead of "k"

    @base10: iff True, use real SI prefixes like "kilo", iff False, use
    base2ish "kibi" and such, iff None, guess.

    @fractionalDigits: the maximum number of digits after the decimal point, or
    None for unlimited.

    @forceSIPrefixes: iff True, use base10ish prefixes even for base2ish
    definitions.

    By default, base2ish (Ki, Mi, Gi...) prefixes are used only if the number
    is a multiple of 1024, otherwise base10ish (k, M, G...) are used. Set the
    `base10` parameter to True or False to force this.
    """
    if (base10 is False) or (size % 1024 == 0 and base10 is not True):
        if pluralize:
            prefixes = ['', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi']
        else:
            prefixes = ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi']
        step = 1024.0
    else:
        if pluralize:
            prefixes = ['', 'kilo', 'mega', 'giga', 'tera', 'peta']
        else:
            prefixes = ['', 'k', 'M', 'G', 'T', 'P']
        step = 1000.0

    if forceSIPrefixes:
        if pluralize:
            prefixes = ['', 'kilo', 'mega', 'giga', 'tera', 'peta']
        else:
            prefixes = ['', 'k', 'M', 'G', 'T', 'P']

    s = size
    while s >= step and prefixes:
        s /= step
        prefixes.pop(0)
    if prefixes:
        if fractionalDigits is not None:
            s = round(s, fractionalDigits)
        start = '%g' % (s,)
        end = "%s%s%s" % (prefixes[0], suffix, plural(s) * pluralize)
        return ' '.join((start, end)).strip()
    return "a whole lot of %s%s (%d)" % (suffix, 's' * pluralize, size)




class StatBucket(item.Item):
    schemaVersion = 2
    "I record the totals for a particular statistic over some time period."
    type = attributes.text(doc="A stat name, such as 'messagesReceived'")
    value = attributes.ieee754_double(default=0.0, doc='Total number of events for this time period')
    interval = attributes.text(doc='A time period, e.g. "quarter-hour" or "minute" or "day"')
    index = attributes.integer(doc='The position in the round-robin list for non-daily stats')
    time = attributes.timestamp(doc='When this bucket was last updated')
    attributes.compoundIndex(interval, type, index)
    attributes.compoundIndex(index, interval)
class QueryStatBucket(item.Item):
    "Pretty much the same thing as above, but just for SQL query stats"
    type = attributes.text("the SQL query string")
    value = attributes.ieee754_double(default=0.0, doc='Total number of events for this time period')
    interval = attributes.text(doc='A time period, e.g. "quarter-hour" or "minute" or "day"')
    index = attributes.integer(doc='The position in the round-robin list for non-daily stats')
    time = attributes.timestamp(doc='When this bucket was last updated')
    attributes.compoundIndex(interval, type, index)

class StatSampler(item.Item):
    service = attributes.reference()

    def run(self):
        """Called once per minute to write the ongoing stats to disk."""
        t = Time()
        if self.service.running:
            updates = []
            queryUpdates = []
            self.doStatSample(self.store, self.service.statoscope, t, updates)
            self.doStatSample(self.store, self.service.queryStatoscope, t, queryUpdates, bucketType=QueryStatBucket)
            for recorder in self.service.userStats.values():
                self.doStatSample(recorder.store, recorder.statoscope, t, updates)
            for obs in self.service.observers:
                obs.statUpdate(t, updates)
                obs.queryStatUpdate(t, queryUpdates)
                
            self.service.currentMinuteBucket += 1
            if self.service.currentMinuteBucket >= MAX_MINUTES:
                self.service.currentMinuteBucket = 0

            if t._time.minute in (15, 30, 45, 00):
                self.service.currentQuarterHourBucket += 1
                if self.service.currentQuarterHourBucket > 2880:
                    self.service.currentQuarterHourBucket = 0

        return Time.fromDatetime(t._time.replace(second=0) + datetime.timedelta(minutes=1))

    def doStatSample(self, store, statoscope, t, updates, bucketType=StatBucket):
        """
        Record stats collected over the past minute.  All current
        statoscopes are dumped into per-minute buckets, and a running
        total for the quarter-hour and day are updated as well.
        """
        statoscope.setElapsed(60)
        for k, v in statoscope._stuffs.items():
            if k.startswith("bandwidth_"):
                #measured in kB/sec, not bytes/minute
                v = float(v) / (60 * 1024)
            mb = store.findOrCreate(
                bucketType, type=unicode(k),
                interval=u"minute", index=self.service.currentMinuteBucket)
            mb.time = t
            mb.value = float(v)
            qhb = store.findOrCreate(
                bucketType, type=unicode(k),
                interval=u"quarter-hour", index=self.service.currentQuarterHourBucket)
            qhb.time = t
            qhb.value += float(v)
            db = store.findOrCreate(
                bucketType, type=unicode(k),
                interval=u"day", time=Time.fromDatetime(t._time.replace(hour=0, second=0, minute=0, microsecond=0)))
            db.value += float(v)
            if (k, v) not in updates:
                updates.append((unicode(k), v))
        statoscope.reset()


class StatsService(item.Item, service.Service):
    """
    I collect and record statistics from various parts of a Mantissa app.
    Data is collected by means of a log observer.
    For example, to record the value 7 for a stat named "foo"::

        log.msg(interface=axiom.iaxiom.IStatEvent, stat_foo=7)

    Per-user stats can be recorded as well by passing the keyword
    argument"userstore" with a Store you wish to record stats into.

    """
    installedOn = attributes.reference()
    parent = attributes.inmemory()
    running = attributes.inmemory()
    name = attributes.inmemory()
    statoscope = attributes.inmemory()
    queryStatoscope = attributes.inmemory()
    statTypes = attributes.inmemory()
    currentMinuteBucket = attributes.integer(default=0)
    currentQuarterHourBucket = attributes.integer(default=0)
    observers = attributes.inmemory()
    loginInterfaces = attributes.inmemory()
    userStats = attributes.inmemory()

    powerupInterfaces = (service.IService,)

    def installed(self):
        # XXX TODO: we should be able to extract and insert this app store, and
        # currently we can't because there's no record of the fact that we're
        # going to power up our store's parent.
        if self.store.parent is not None:
            # store.parent.powerUp(store.parent.getItemByID(store.idInParent), IService)
            # XXX TODO: OMG where are the tests that are failing because
            # nothing will ever start this service?  it seems like that should
            # be tested behavior.
            pass
        now = datetime.datetime.utcnow()

        try:
            self.store.findUnique(StatSampler)
        except errors.ItemNotFound:
            s = self.store.findOrCreate(StatSampler, service=self)
            t = Time.fromDatetime(now.replace(second=0) + datetime.timedelta(minutes=1))
            iaxiom.IScheduler(self.store).schedule(s, t)

        if self.parent is None:
            self.setServiceParent(self.store)
            self.startService()

    def startService(self):
        service.Service.startService(self)
        self.statoscope = Statoscope("mantissa-stats", None)
        self.queryStatoscope = Statoscope("query-stats", None)
        log.addObserver(self._observeStatEvent)
        self.statTypes = statDescriptions.keys()
        self.observers = []

        self.observers.extend(self.store.query(RemoteStatsObserver))
        self.loginInterfaces = {}
        self.userStats = {}
        for x in getInstalledOfferings(self.store.parent).values():
            self.loginInterfaces.update(dict(x.loginInterfaces))

        self.statoscope._stuffs = dict.fromkeys(statDescriptions.iterkeys(), 0)
        self.statoscope._stuffs.update(dict.fromkeys([bucket.type for bucket in
                                                      self.store.query(StatBucket,
                                                                       attributes.AND(StatBucket.index==0,
                                                                                      StatBucket.interval==u"minute"))], 0))

    def addStatsObserver(self, obs):
        self.observers.append(obs)
    def removeStatsObserver(self, obs):
        for name, observers in self.observers.iteritems():
            if obs in observers:
                observers.remove(obs)

    def stopService(self):
        log.removeObserver(self._observeStatEvent)
        service.Service.stopService(self)


    def _observeStatEvent(self, events):
        """Look for IStatEvent messages and update internal Statoscopes.

        These Statoscopes are then periodically written to the log by
        _takeSample.
        """

        if 'http_render' in events:
            events = {'interface':iaxiom.IStatEvent, 'stat_page_renders':1}
        #blech
        elif 'athena_send_messages' in events:
            events = {'interface':iaxiom.IStatEvent, 'stat_athena_messages_sent':events['count']}
        elif 'athena_received_messages' in events:
            events = {'interface':iaxiom.IStatEvent, 'stat_athena_messages_received':events['count']}
        elif 'querySQL' in events:
            self.queryStatoscope.record(**{str(events['querySQL']): events['queryTime']})

        elif 'cred_interface' in events:
            if_desc = self.loginInterfaces.get(events['cred_interface'], None)
            if not if_desc:
                #not specified by any offering, therefore ignorable
                return
            events = {'interface':iaxiom.IStatEvent, 'name':if_desc, 'stat_' +
                      if_desc: 1}
        try:
            if not issubclass(events['interface'], iaxiom.IStatEvent):
                return
        except (TypeError, KeyError):
            return

        # retain only keys that start with stat_
        d = itertools.ifilter(lambda k: k[0][:5]=='stat_', events.iteritems())
        # strip the stat_ prefix
        d = dict(itertools.imap(lambda k: (k[0][5:], k[1]), d))
        self.statoscope.record(**d)
        if 'userstore' in events:
            store = events['userstore']
            user, domain = userbase.getAccountNames(store).next()
            self.userStats.setdefault((user, domain), UserStatRecorder(store, user, domain)).statoscope.record(**d)

class UserStatRecorder:
    "Keeps track of stats recorded for particular users."
    def __init__(self, store, user, domain):
        self.store = store
        self.statoscope = Statoscope("", user="%s@%s" % (user, domain))


class BandwidthMeasuringProtocol(policies.ProtocolWrapper):
    "Wraps a Protocol and sends bandwidth stats to a BandwidthMeasuringFactory."
    def write(self, data):
        self.factory.registerWritten(len(data))
        policies.ProtocolWrapper.write(self, data)

    def writeSequence(self, seq):
        self.factory.registerWritten(sum(map(len, seq)))
        policies.ProtocolWrapper.writeSequence(self, seq)

    def dataReceived(self, data):
        self.factory.registerRead(len(data))
        policies.ProtocolWrapper.dataReceived(self, data)

class BandwidthMeasuringFactory(policies.WrappingFactory):
    "Collects stats on the number of bytes written and read by protocol instances from the wrapped factory."
    protocol = BandwidthMeasuringProtocol

    def __init__(self, wrappedFactory, protocolName):
        policies.WrappingFactory.__init__(self, wrappedFactory)
        self.name = protocolName

    def registerWritten(self, length):
        log.msg(interface=iaxiom.IStatEvent, **{"stat_bandwidth_" + self.name + "_up": length})

    def registerRead(self, length):
        log.msg(interface=iaxiom.IStatEvent, **{"stat_bandwidth_" + self.name + "_down": length})

class RemoteStatsObserver(item.Item):

    hostname = attributes.bytes(doc="A host to send stat updates to")
    port = attributes.integer(doc="The port to send stat updates to")
    protocol = attributes.inmemory(doc="The juice protocol instance to send stat updates over")

    def activate(self):
        #axiom is weak
        self.protocol = None
    def queryStatUpdate(self, t, updates):
        self.statUpdate(t, updates, queryStat=True)
        
    def statUpdate(self, t, updates, queryStat=False):
        """
        Sends a stringified version of the stat update data (a list of
        name, value pairs) and the current time over a juice
        connection to a remote stats collector.

        XXX: find a better way to preserve the structure of the update
        info
        """
        if not self.protocol:
            self._connectToStatsServer().addCallback(
                lambda x: StatUpdate(time=t,
                                     data=repr(updates),
                                     querystat=queryStat).do(self.protocol))
        else:
            StatUpdate(time=t, data=repr(updates),
                       querystat=queryStat).do(self.protocol,
                                               requiresAnswer=False)

    def _connectToStatsServer(self):
        return protocol.ClientCreator(reactor,
                             juice.Juice, False).connectTCP(self.hostname,
                                                     self.port).addCallback(
            lambda p: setattr(self, "protocol", p))

class StatUpdate(juice.Command):
    commandName = "Stat-Update"
    arguments = [('time', juice.Time()), ('data', juice.String()),
                 ('querystat', juice.Boolean())]


class SimpleRemoteStatsCollector(juice.Juice):

    def command_STAT_UPDATE(self, time, data):
        "Shove the current time and some stat data into a log file."
        self.factory.log.write("%s %s\n" % (time, data))
        return {}
    command_STAT_UPDATE.command = StatUpdate

def upgradeStatBucket1to2(bucket):
    if bucket.type.startswith(u"_axiom_query"):
        bucket.deleteFromStore()
        return None
    else:
        return bucket.upgradeVersion("xmantissa_stats_statbucket", 1, 2,
                                     type=bucket.type,
                                     index=bucket.index,
                                     interval=bucket.interval,
                                     value=bucket.value,
                                     time=bucket.time)
upgrade.registerUpgrader(upgradeStatBucket1to2, 'xmantissa_stats_statbucket', 1, 2)
