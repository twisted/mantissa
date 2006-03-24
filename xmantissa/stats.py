# -*- test-case-name: quotient.test.test_stats -*-
# Copyright 2005 Divmod, Inc.  See LICENSE file for details

import time, datetime, itertools

from twisted.application import service
from twisted.python import log
from axiom import iaxiom, item, attributes, errors
from epsilon.extime import Time
from xmantissa.offering import getInstalledOfferings

statDescriptions = {"page_renders": "Nevow page renders per minute",
                    "messages_grabbed": "POP3 messages grabbed per minute",
                    "cache_hits": "Axiom cache hits per minute",
                    "cursor_execute_time": "Seconds spent in cursor.execute per minute",
                    "commits": "Axiom commits per minute",
                    "cache_misses": "Axiom cache misses per minute",
                    "autocommits": "Axiom autocommits per minute"}

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
            self._stuffs = {}

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
    type = attributes.text() #e.g. "messages received per second"
    value = attributes.ieee754_double(default=0.0)
    interval = attributes.text() # e.g. "hour" or "minute" or "day"
    index = attributes.integer()
    time = attributes.timestamp()

class StatSampler(item.Item):
    service = attributes.reference()

    def run(self):
        """Called once per minute to write the ongoing stats to disk."""
        t = Time()
        if self.service.running:
            updates = []
            for scope in self.service.statoscopes.itervalues():
                scope.setElapsed(60)
                for k, v in scope._stuffs.iteritems():
                    b = self.store.findOrCreate(
                        StatBucket, type=unicode(k),
                        interval=u"minute", index=self.service.currentMinuteBucket)
                    b.time = t
                    b.value = float(v)
                    updates.append((k, t, v))
                scope.reset()
            for obs in self.service.observers:
                obs.statUpdate(updates)
            self.service.currentMinuteBucket += 1
            if self.service.currentMinuteBucket >= MAX_MINUTES:
                self.service.currentMinuteBucket = 0
        return Time.fromDatetime(t._time.replace(second=0) + datetime.timedelta(minutes=1))

def aggregateBuckets(store, name, beginning, end):
    """Collect a bunch of per-minute StatBuckets and average their value."""
    if beginning < 0:
        beginning += MAX_MINUTES 
        # this is a round-robin list, so make sure to get
        # the part recorded before the wraparound:
        return store.query(StatBucket,
                           attributes.AND(StatBucket.type==unicode(name),
                                          StatBucket.interval== u"minute",
                                          attributes.OR(StatBucket.index >= beginning,
                                                        StatBucket.index <= end))).getColumn('value').average()
    else:
        return store.query(StatBucket,
                           attributes.AND(StatBucket.type==unicode(name),
                                          StatBucket.interval== u"minute",
                                          StatBucket.index >= beginning,
                                          StatBucket.index <= end)).getColumn('value').average()

class QuarterHourSampler(item.Item):
    service = attributes.reference()
    def run(self):
        """Aggregate the past 15 minutes into a quarter-hour StatBucket."""
        t = Time()
        if self.service.running:
            for name in self.service.statTypes:
                end = self.service.currentMinuteBucket
                beginning =  end - 15
                qhb = self.store.findOrCreate(StatBucket, type=unicode(name), interval=u"quarterhour",
                                              index=self.service.currentQuarterHourBucket)
                qhb.time = t
                qhb.value=aggregateBuckets(self.store, name, beginning, end)
                if self.service.currentQuarterHourBucket > 2880:
                    self.service.currentQuarterHourBucket = 0
            m = t._time.minute
            hdelta, nextm = divmod(m + 15 - (m % 15), 60)
            return Time.fromDatetime(t._time.replace(second=0, minute=nextm) + datetime.timedelta(hours=hdelta))


class DailySampler(item.Item):
    service = attributes.reference()
    def run(self):
        """Aggregate the past 24 hours into a daily StatBucket."""
        t = Time()
        if self.service.running:
            for name in self.service.statTypes:
                end = self.service.currentMinuteBucket
                #only want a day's worth:
                beginning =  end - (24 * 60)
                StatBucket(store=self.store,
                           time=t,
                           interval=u"day",
                           type=unicode(name),
                           value= aggregateBuckets(self.store, name, beginning, end))
        return Time.fromDatetime(t._time.replace(hour=0, second=0, minute=0) + datetime.timedelta(hours=24))

class StatsService(item.Item, service.Service, item.InstallableMixin):

    installedOn = attributes.reference()
    parent = attributes.inmemory()
    running = attributes.inmemory()
    name = attributes.inmemory()
    statoscopes = attributes.inmemory()
    statTypes = attributes.inmemory()
    currentMinuteBucket = attributes.integer(default=0)
    currentQuarterHourBucket = attributes.integer(default=0)
    observers = attributes.inmemory()
    loginInterfaces = attributes.inmemory()

    def installOn(self, store):
        super(StatsService, self).installOn(store)
        store.powerUp(self, service.IService)
        now = datetime.datetime.utcnow()

        try:
            store.findUnique(StatSampler)
        except errors.ItemNotFound:
            s = store.findOrCreate(StatSampler, service=self)
            t = Time.fromDatetime(now.replace(second=0) + datetime.timedelta(minutes=1))
            iaxiom.IScheduler(store).schedule(s, t)

        try:
            store.findUnique(QuarterHourSampler)
        except errors.ItemNotFound:
            qhs = store.findOrCreate(QuarterHourSampler, service=self)
            m = now.minute
            hdelta, nextm = divmod(m + 15 - (m % 15), 60)
            t2 = Time.fromDatetime(now.replace(second=0, minute=m) + datetime.timedelta(hours=hdelta))
            iaxiom.IScheduler(store).schedule(qhs, t2)

        try:
            store.findUnique(DailySampler)
        except errors.ItemNotFound:
            ds = store.findOrCreate(DailySampler, service=self)
            t2 = Time.fromDatetime(now.replace(hour=0, second=0, minute=0) + datetime.timedelta(hours=24))
            iaxiom.IScheduler(store).schedule(ds, t2)

        if self.parent is None:
            self.setServiceParent(store)
            self.startService()

    def startService(self):
        service.Service.startService(self)
        self.statoscopes = {}
        log.addObserver(self._observeStatEvent)
        self.statTypes = statDescriptions.keys()
        self.observers = []
        self.loginInterfaces = {}
        for x in getInstalledOfferings(self.store.parent).values():
            self.loginInterfaces.update(dict(x.loginInterfaces))

    def addStatsObserver(self, obs):
        self.observers.append(obs)
    def removeStatsObserver(self, obs):
        for name, observers in self.observers.iteritems():
            if obs in observers:
                observers.remove(obs)

    def stopService(self):
        log.removeObserver(self._observeStatoscopeEvent)
        log.removeObserver(self._observeStatEvent)
        service.Service.stopService(self)


    def _observeStatEvent(self, events):
        """Look for IStatEvent messages and update internal Statoscopes.

        These Statoscopes are then periodically written to the log by
        _takeSample.
        """
        if 'http_render' in events:
            events = {'interface':iaxiom.IStatEvent, 'name':'nevow', 'stat_page_renders':1}
        elif 'cred_interface' in events:
            if_desc = self.loginInterfaces.get(events['cred_interface'], None)
            if not if_desc:
                #not specified by any offering, therefore ignorable
                return
            events = {'interface':iaxiom.IStatEvent, 'name':if_desc, 'stat_' +
                      if_desc: 1}
        try:
            if not issubclass(events['interface'], iaxiom.IStatEvent ):
                return
            name = events['name']
        except (TypeError, KeyError):
            return

        # retain only keys that start with stat_
        d = itertools.ifilter(lambda k: k[0][:5]=='stat_', events.iteritems())
        # strip the stat_ prefix
        d = dict(itertools.imap(lambda k: (k[0][5:], k[1]), d))
        if not self.statoscopes.get(name):
            self.statoscopes[name] = Statoscope(name, events.get('user'))

        self.statoscopes[name].record(**d)
