# Copyright 2005 Divmod, Inc.  See LICENSE file for details

"""Session Initialization Protocol tests."""
from zope.interface import  implements

from twisted.trial import unittest
from xmantissa import  sip
from twisted.internet import defer, reactor


from twisted.test import proto_helpers

from twisted import cred
import axiom

sip.SIPTransport._resolveA = lambda self, uri: defer.succeed(testurls.get(uri, uri))

# request, prefixed by random CRLFs
request1 = "\n\r\n\n\r" + """\
INVITE sip:foo SIP/2.0
From: mo
To: joe
Content-Length: 4

abcd""".replace("\n", "\r\n")

# request, no content-length
request2 = """INVITE sip:foo SIP/2.0
From: mo
To: joe

1234""".replace("\n", "\r\n")

# request, with garbage after
request3 = """INVITE sip:foo SIP/2.0
From: mo
To: joe
Content-Length: 4

1234

lalalal""".replace("\n", "\r\n")

# three requests
request4 = """INVITE sip:foo SIP/2.0
From: mo
To: joe
Content-Length: 0

INVITE sip:loop SIP/2.0
From: foo
To: bar
Content-Length: 4

abcdINVITE sip:loop SIP/2.0
From: foo
To: bar
Content-Length: 4

1234""".replace("\n", "\r\n")

# response, no content
response1 = """SIP/2.0 200 OK
From:  foo
To:bar
Content-Length: 0

""".replace("\n", "\r\n")

# short header version
request_short = """\
INVITE sip:foo SIP/2.0
f: mo
t: joe
l: 4

abcd""".replace("\n", "\r\n")

request_natted = """\
INVITE sip:foo SIP/2.0
Via: SIP/2.0/UDP 10.0.0.1:5060;rport

""".replace("\n", "\r\n")

trickyRequest = """\
INVITE sip:bob@10.0.0.2 SIP/2.0\r
Via: SIP/2.0/UDP proxy2.org:5060\r
     ;branch=z9hG4bKc97e87daf80295082a8208b5db61beab\r
Via: SIP/2.0/UDP proxy1.org:5060\r
     ;branch=z9hG4bKcab2bd111444e23321d67d33584580b3\r
     ;received=10.1.0.1\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
Max-Forwards: 68\r
Record-Route: sip:proxy2.org:5060;lr,"Awesome Proxy" <sip:proxy1.org:5060>;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
Contact: <sip:alice@client.com>\r
\r
"""



class FakeAvatar:
    implements(sip.IContact)

    def __init__(self, realm, avatarId):
        self.realm = realm
        self.avatarId = avatarId
        self.physicalURL = None
        self.expiry = None

    def registerAddress(self, physicalURL, expiry):
        """Register the physical address of a logical URL.

        @return: Deferred of C{Registration} or failure with RegistrationError.
        """
        self.physicalURL = physicalURL
        self.expiry = expiry
        self.realm.regs += 1
        return self.getRegistrationInfo()

    def unregisterAddress(self, url):
        """Unregister the physical address of a logical URL.

        @return: Deferred of C{Registration} or failure with RegistrationError.
        """
        oldURL = self.physicalURL
        self.physicalURL = None
        self.expiry = 0
        self.realm.regs -= 1
        return [(oldURL, 0)]

    unregisterAllAddresses = lambda self: self.unregisterAddress(None)

    def getRegistrationInfo(self):
        """Get registration info for logical URL.

        @return: Deferred of C{Registration} object or failure of SIPLookupError.
        """
        if self.physicalURL is None:
            raise sip.SIPLookupError()
        return [(self.physicalURL, self.expiry)]

    def callIncoming(self, name, callerURI, callerContact):
        """Record an incoming call with a user's name, the incoming
        SIP URI, and, if they are registered with our system, their
        caller IContact implementor.

        You may *decline* an incoming call by raising an exception in
        this method.  A SIPError is preferred.
        """

    def callOutgoing(self, name, calleeURI):
        """Record an outgoing call.
        """


class TestRealm:
    implements(cred.portal.IRealm)
    regs = 0
    permissive = True

    def __init__(self, domain='127.0.0.1'):
        self.users = {}
        self.domain = domain

    def addUser(self, name):
        self.users[name] = FakeAvatar(self, name)

    def requestAvatar(self, avatarId, mind, *interfaces):
        from atop.credup import NoSuchUser, NoSuchDomain
        domain = avatarId.split('@')[-1]
        if domain == self.domain:
            if self.permissive and not self.users.has_key(avatarId):
                self.addUser(avatarId)
        else:
            raise NoSuchDomain
        try:
            return sip.IContact, self.users[avatarId], lambda: None
        except KeyError:

            raise NoSuchUser

class MessageParsingTestCase(unittest.TestCase):
    def setUp(self):
        self.l = []
        self.parser = sip.MessagesParser(self.l.append)

    def feedMessage(self, message):
        self.parser.dataReceived(message)
        self.parser.dataDone()

    def validateMessage(self, m, method, uri, headers, body):
        """Validate Requests."""
        self.assertEquals(m.method, method)
        self.assertEquals(m.uri.toString(), uri)
        self.assertEquals(m.headers, headers)
        self.assertEquals(m.body, body)
        self.assertEquals(m.finished, 1)

    def testSimple(self):
        l = self.l
        self.feedMessage(request1)
        self.assertEquals(len(l), 1)
        self.validateMessage(l[0], "INVITE", "sip:foo",
                             {"from": ["mo"], "to": ["joe"], "content-length": ["4"]},
                             "abcd")

    def testTwoMessages(self):
        l = self.l
        self.feedMessage(request1)
        self.feedMessage(request2)
        self.assertEquals(len(l), 2)
        self.validateMessage(l[0], "INVITE", "sip:foo",
                             {"from": ["mo"], "to": ["joe"], "content-length": ["4"]},
                             "abcd")
        self.validateMessage(l[1], "INVITE", "sip:foo",
                             {"from": ["mo"], "to": ["joe"]},
                             "1234")

    def testGarbage(self):
        l = self.l
        self.feedMessage(request3)
        self.assertEquals(len(l), 1)
        self.validateMessage(l[0], "INVITE", "sip:foo",
                             {"from": ["mo"], "to": ["joe"], "content-length": ["4"]},
                             "1234")

    def testThreeInOne(self):
        l = self.l
        self.feedMessage(request4)
        self.assertEquals(len(l), 3)
        self.validateMessage(l[0], "INVITE", "sip:foo",
                             {"from": ["mo"], "to": ["joe"], "content-length": ["0"]},
                             "")
        self.validateMessage(l[1], "INVITE", "sip:loop",
                             {"from": ["foo"], "to": ["bar"], "content-length": ["4"]},
                             "abcd")
        self.validateMessage(l[2], "INVITE", "sip:loop",
                             {"from": ["foo"], "to": ["bar"], "content-length": ["4"]},
                             "1234")

    def testShort(self):
        l = self.l
        self.feedMessage(request_short)
        self.assertEquals(len(l), 1)
        self.validateMessage(l[0], "INVITE", "sip:foo",
                             {"from": ["mo"], "to": ["joe"], "content-length": ["4"]},
                             "abcd")

    def testSimpleResponse(self):
        l = self.l
        self.feedMessage(response1)
        self.assertEquals(len(l), 1)
        m = l[0]
        self.assertEquals(m.code, 200)
        self.assertEquals(m.phrase, "OK")
        self.assertEquals(m.headers, {"from": ["foo"], "to": ["bar"], "content-length": ["0"]})
        self.assertEquals(m.body, "")
        self.assertEquals(m.finished, 1)

    def testMultiHeaders(self):
        self.feedMessage(trickyRequest)
        m = self.l[0]
        self.assertEquals(m.headers['record-route'], ["sip:proxy2.org:5060;lr", '"Awesome Proxy" <sip:proxy1.org:5060>;lr'])
    def testContinuationLines(self):
        self.feedMessage(trickyRequest)
        m = self.l[0]
        self.assertEquals(m.headers['via'], ["SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bKc97e87daf80295082a8208b5db61beab",
                          "SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bKcab2bd111444e23321d67d33584580b3;received=10.1.0.1",
                          "SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1"])

class MessageParsingTestCase2(MessageParsingTestCase):
    """Same as base class, but feed data char by char."""

    def feedMessage(self, message):
        for c in message:
            self.parser.dataReceived(c)
        self.parser.dataDone()


class MakeMessageTestCase(unittest.TestCase):

    def testRequest(self):
        r = sip.Request("INVITE", "sip:foo")
        r.addHeader("foo", "bar")
        self.assertEquals(r.toString(), "INVITE sip:foo SIP/2.0\r\nFoo: bar\r\n\r\n")

    def testResponse(self):
        r = sip.Response(200, "OK")
        r.addHeader("foo", "bar")
        r.addHeader("Content-Length", "4")
        r.bodyDataReceived("1234")
        self.assertEquals(r.toString(), "SIP/2.0 200 OK\r\nFoo: bar\r\nContent-length: 4\r\n\r\n1234")

    def testStatusCode(self):
        r = sip.Response(200)
        self.assertEquals(r.toString(), "SIP/2.0 200 OK\r\n\r\n")


class ViaTestCase(unittest.TestCase):

    def checkRoundtrip(self, v):
        s = v.toString()
        self.assertEquals(s, sip.parseViaHeader(s).toString())

    def testComplex(self):
        s = "SIP/2.0/UDP first.example.com:4000;ttl=16;maddr=224.2.0.1 ;branch=a7c6a8dlze (Example)"
        v = sip.parseViaHeader(s)
        self.assertEquals(v.transport, "UDP")
        self.assertEquals(v.host, "first.example.com")
        self.assertEquals(v.port, 4000)
        self.assertEquals(v.ttl, 16)
        self.assertEquals(v.maddr, "224.2.0.1")
        self.assertEquals(v.branch, "a7c6a8dlze")
        self.assertEquals(v.hidden, 0)
        self.assertEquals(v.toString(),
                          "SIP/2.0/UDP first.example.com:4000;ttl=16;branch=a7c6a8dlze;maddr=224.2.0.1")
        self.checkRoundtrip(v)

    def testSimple(self):
        s = "SIP/2.0/UDP example.com;hidden"
        v = sip.parseViaHeader(s)
        self.assertEquals(v.transport, "UDP")
        self.assertEquals(v.host, "example.com")
        self.assertEquals(v.port, 5060)
        self.assertEquals(v.ttl, None)
        self.assertEquals(v.maddr, None)
        self.assertEquals(v.branch, None)
        self.assertEquals(v.hidden, 1)
        self.assertEquals(v.toString(),
                          "SIP/2.0/UDP example.com:5060;hidden")
        self.checkRoundtrip(v)

    def testSimpler(self):
        v = sip.Via("example.com")
        self.checkRoundtrip(v)

    def testRPort(self):
        v = sip.Via("foo.bar", rport=True)
        self.assertEquals(v.toString(), "SIP/2.0/UDP foo.bar:5060;rport")

    def testNAT(self):
        s = "SIP/2.0/UDP 10.0.0.1:5060;received=22.13.1.5;rport=12345"
        v = sip.parseViaHeader(s)
        self.assertEquals(v.transport, "UDP")
        self.assertEquals(v.host, "10.0.0.1")
        self.assertEquals(v.port, 5060)
        self.assertEquals(v.received, "22.13.1.5")
        self.assertEquals(v.rport, 12345)

        self.assertNotEquals(v.toString().find("rport=12345"), -1)

class URLTestCase(unittest.TestCase):

    def testRoundtrip(self):
        for url in [
            "sip:j.doe@big.com",
            "sip:j.doe:secret@big.com;transport=tcp",
            "sip:j.doe@big.com?subject=project",
            "sip:example.com",
            ]:
            self.assertEquals(sip.parseURL(url).toString(), url)

    def testComplex(self):
        s = ("sip:user:pass@hosta:123;transport=udp;user=phone;method=foo;"
             "ttl=12;maddr=1.2.3.4;blah;goo=bar?a=b&c=d")
        url = sip.parseURL(s)
        for k, v in [("username", "user"), ("password", "pass"),
                     ("host", "hosta"), ("port", 123),
                     ("transport", "udp"), ("usertype", "phone"),
                     ("method", "foo"), ("ttl", 12),
                     ("maddr", "1.2.3.4"), ("other", {'blah': '', 'goo': 'bar'}),
                     ("headers", {"a": "b", "c": "d"})]:
            self.assertEquals(getattr(url, k), v)


class ParseTestCase(unittest.TestCase):

    def testParseAddress(self):
        for address, name, urls, params in [

            ('"A. G. Bell" <sip:foo@example.com>', "A. G. Bell", "sip:foo@example.com", {}),
            (' "A. G. Bell" <sip:foo@example.com>', "A. G. Bell", "sip:foo@example.com", {}),
            ('"Bell, A. G." <sip:bell@example.com>', "Bell, A. G.", "sip:bell@example.com", {}),
            ('" \\\\A. G. \\"Bell" <sip:foo@example.com>', " \\A. G. \"Bell", "sip:foo@example.com", {}),
            ('"\\x21A. G. Bell" <sip:foo@example.com>', "x21A. G. Bell", "sip:foo@example.com", {}),
            ("abcd1234-.!%*_+`'~ <sip:foo@example.com>", "abcd1234-.!%*_+`'~", "sip:foo@example.com", {}),
            ('"C\xc3\xa9sar" <sip:C%C3%A9sar@example.com>', u'C\xe9sar', 'sip:C%C3%A9sar@example.com', {}),
            ("Anon <sip:foo@example.com>", "Anon", "sip:foo@example.com", {}),
            ("sip:foo@example.com", "", "sip:foo@example.com", {}),
            ("<sip:foo@example.com>", "", "sip:foo@example.com", {}),
            ("foo <sip:foo@example.com>;tag=bar;foo=baz", "foo", "sip:foo@example.com", {"tag": "bar", "foo": "baz"}),
            ("sip:foo@example.com;tag=bar;foo=baz", "", "sip:foo@example.com", {"tag": "bar", "foo": "baz"}),
            ]:
            gname, gurl, gparams = sip.parseAddress(address)
            self.assertEquals(name, gname)
            self.assertEquals(gurl.toString(), urls)
            self.assertEquals(gparams, params)

    def testHeaderSplitting(self):
        self.assertEquals(sip.splitMultiHeader(r'"fu\\" <sip:foo@example.com>, sip:bar@example.com'),
                                              [r'"fu\\" <sip:foo@example.com>', ' sip:bar@example.com'])


class PermissiveChecker:
    implements(cred.checkers.ICredentialsChecker)

    credentialInterfaces = (cred.credentials.IUsernamePassword,
                            cred.credentials.IUsernameHashedPassword,
                            axiom.userbase.IPreauthCredentials)

    def requestAvatarId(self, credentials):
        return credentials.username

testurls = {'proxy.com' : '127.0.0.1',
            'client.com': '10.0.0.1',
            'server.com': '10.0.0.2',
            'proxy1.org': '10.1.0.1',
            'proxy2.org': '10.1.0.2'}
exampleInvite = """INVITE sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9\r
Max-Forwards: 70\r
Route: <sip:proxy1.org;lr>\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
Contact: <sip:alice@client.com>\r
\r
"""

exampleResponse = """SIP/2.0 200 OK\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK98445eb190a00b7391e9b80b63fad890;rport\r
Via: SIP/2.0/UDP client.com:1234;branch=z9hG4bK74bf9\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
Contact: <sip:alice@client.com>\r
\r
"""
exampleResponseReceived = """SIP/2.0 200 OK\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK98445eb190a00b7391e9b80b63fad890;rport\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=foo.com\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
Contact: <sip:alice@client.com>\r
\r
"""
exampleResponseWrongVia = """SIP/2.0 200 OK\r
Via: SIP/2.0/UDP foo.com:5060;branch=z9hG4bK98445eb190a00b7391e9b80b63fad890;rport\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=foo.com\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
Contact: <sip:alice@client.com>\r
\r
"""
class TestClock:
    time = 0
    def seconds(self):
        return self.time

    def advance(self, n):
        self.time += n

class FakeClockTestCase(unittest.TestCase):
    # Do NOT, EVER, leave base.seconds set to something other than its
    # original value when you finish the test. If you do, other tests
    # (possibly just one) will fail and debugging will be very very
    # difficult.
    def setUpClass(self):
        from twisted.internet import base

        self.clock = TestClock()
        self.originalSeconds = base.seconds
        base.seconds = self.clock.seconds

    def tearDownClass(self):
        from twisted.internet import base
        base.seconds = self.originalSeconds


class ProxyTestCase(FakeClockTestCase):

    def setUp(self):
        r = TestRealm("proxy1.org")
        p = cred.portal.Portal(r)
        p.registerChecker(PermissiveChecker())
        self.proxy = sip.Proxy(p)
        self.sent = []
        self.sip = sip.SIPTransport(self.proxy, ["proxy1.org"], 5060)
        self.proxy._lookupURI = lambda uri: defer.succeed([(testurls.get(uri.host, uri.host), 5060)])
        self.sip.sendMessage = lambda dest, msg: self.sent.append((dest, msg))

    def tearDown(self):
        self.clock.advance(33)
        reactor.iterate()
        self.clock.advance(33)
        reactor.iterate()


    def testRequestForward(self):
        self.sip.datagramReceived(exampleInvite, (testurls["client.com"], 5060))
        self.assertEquals(len(self.sent), 2)
        m, dest = self.sent[1]
        
        self.assertEquals(dest[1], 5060)
        self.assertEquals(dest[0], testurls["proxy2.org"])
        self.assertEquals(m.uri.toString(), "sip:bob@proxy2.org")
        self.assertEquals(m.method, "INVITE")
        self.assertEquals(m.headers["via"],
                          ['SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;rport',
                           'SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1'])
        
    def testReceivedRequestForward(self):
        self.sip.datagramReceived(exampleInvite, ("1.1.1.1", 5060))
        m, dest = self.sent[1]
        self.assertEquals(m.headers["via"],
                          ['SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bKa905c1dc6bf2cba9db06344571cb35fb;rport',
                           'SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=1.1.1.1'])

    def testResponseWrongVia(self):
        # first via must match proxy's address

        self.sip.datagramReceived(exampleResponseWrongVia, ("1.1.1.1", 5060))
        self.assertEquals(len(self.sent), 0)

    def testResponseForward(self):
        self.sip.datagramReceived(exampleResponse, (testurls["server.com"],
                                                    5060))
        self.assertEquals(len(self.sent), 1)
        m, dest = self.sent[0]
        self.assertEquals(dest, (testurls["client.com"], 1234))
        self.assertEquals(m.code, 200)

        self.assertEquals(m.headers["via"], ["SIP/2.0/UDP client.com:1234;branch=z9hG4bK74bf9"])

    def testReceivedResponseForward(self):
        self.sip.datagramReceived(exampleResponseReceived, ("foo.com", 5060))
        self.assertEquals(len(self.sent), 1)
        m, dest = self.sent[0]
        self.assertEquals(dest, ("foo.com", 5060))

    def testCantForwardRequest(self):
        self.proxy.findTargets = lambda uri: defer.fail(sip.SIPLookupError(604))
        # Make all lookups fail with a 604
        self.sip.datagramReceived(exampleInvite, (testurls["client.com"], 5060))
        self.assertEquals(len(self.sent), 2)
        self.assertEquals(self.sent[0][0].code, 100)
        m, dest = self.sent[1]        
        self.assertEquals(m.code, 604)
        self.assertEquals(dest, (testurls["client.com"], 5060))
        self.assertEquals(m.headers["via"], ['SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1'])

class RegistrationTestCase(FakeClockTestCase):

    def setUp(self):
        self.realm = TestRealm("proxy.com")
        self.realm.addUser('joe@proxy.com')
        self.portal = cred.portal.Portal(self.realm)
        c = cred.checkers.InMemoryUsernamePasswordDatabaseDontUse()
        c.credentialInterfaces += (axiom.userbase.IPreauthCredentials,)
        c.addUser('joe@proxy.com', 'passXword')
        self.portal.registerChecker(c)
        self.proxy = sip.Proxy(self.portal)
        self.transport = sip.SIPTransport(self.proxy,
                                          ["proxy.com",'127.0.0.1'], 5060)
        self.sent = []
        self.proxy._lookupURI = lambda uri: [(uri.host, uri.port)]
        def sm(msg, dest):
            self.sent.append((dest, msg))
        self.transport.sendMessage = sm
        



    def tearDown(self):
        self.clock.advance(33)
        
    def testWontForwardRequest(self):
        r = sip.Request("INVITE", "sip:joe@server.com")
        r.addHeader("via", sip.Via("1.2.3.4", branch="z9hG4bKA").toString())
        r.addHeader("to", "<sip:joe@server.com>")
        r.addHeader("from","<sip:bob@example.org>")
        r.addHeader("call-id", "8E0C617B69B2D91187C6000E35CE1034@proxy.com")
        r.addHeader("CSeq", "25317 INVITE")
        self.transport.datagramReceived(r.toString(), ("1.2.3.4", 5060))
        self.assertEquals(len(self.sent), 2)
        self.assertEquals(self.sent[0][1].code, 100)
        dest, m = self.sent[1]
        self.assertEquals(m.code, 401)
        self.assertEquals(dest, ("1.2.3.4", 5060))
        self.assertEquals(m.headers["via"],
                          ["SIP/2.0/UDP 1.2.3.4:5060;branch=z9hG4bKA;received=1.2.3.4"])

    def buildRequest(self):
        r = sip.Request("REGISTER", "sip:proxy.com")
        r.addHeader("to", "sip:joe@proxy.com")
        r.addHeader("from", "sip:joe@proxy.com")
        r.addHeader("call-id", "8E0C617B69B2D91187C6000E35CE1034@proxy.com")
        r.addHeader("CSeq", "25317 REGISTER")
        r.addHeader("contact", "sip:joe@client.com:1234")
        r.addHeader("via", sip.Via("client.com", branch="z9hG4bK9").toString())
        return r

    def registerBad(self):
        r = self.buildRequest()
        self.transport.datagramReceived(r.toString(), (testurls["client.com"], 5060))

    def registerGood(self):
        reg = self.proxy.registrar
        reg.authorizers = reg.authorizers.copy()
        reg.authorizers['basic'] = sip.BasicAuthorizer()
        r = self.buildRequest()
        r.addHeader("authorization", "Basic " + "joe:passXword".encode('base64'))
        self.transport.datagramReceived(r.toString(), (testurls["client.com"], 5060))


    def unregister(self):
        r = self.buildRequest()
        r.headers['contact'][0] = "*"
        r.headers["via"][0] =  sip.Via("client.com",
                                    branch="z9hG4bK10").toString()
        r.addHeader("expires", "0")
        r.addHeader("authorization", "Basic " + "joe:passXword".encode('base64'))
        self.transport.datagramReceived(r.toString(), (testurls["client.com"], 5060))

    def testRegister(self):
        self.registerGood()
        dest, m = self.sent[0]
        self.assertEquals(dest, (testurls["client.com"], 5060))
        self.assertEquals(m.code, 200)
        self.assertEquals(m.headers["via"],
                          ["SIP/2.0/UDP client.com:5060;branch=z9hG4bK9;received=10.0.0.1"])
        self.assertEquals(m.headers["to"], ["sip:joe@proxy.com"])
        self.assertEquals(m.headers["contact"], ["sip:joe@client.com:1234"])
        self.failUnless(int(m.headers["expires"][0]) in (3600, 3601, 3599, 3598))
        self.assertEquals(self.countRegistrations(), 1)
        from atop.credup import Preauthenticated
        ignoredIface, contact, ignoredLogout = unittest.deferredResult(
            self.proxy.portal.login(Preauthenticated('joe@proxy.com'),
                                    None, sip.IContact))
        desturl = contact.getRegistrationInfo()[0][0]
        self.assertEquals((desturl.host, desturl.port), ("client.com", 1234))


    def testUnregister(self):
        self.registerGood()
        self.unregister()
        dest, m = self.sent[1]
        self.assertEquals(dest, (testurls["client.com"], 5060))
        self.assertEquals(m.code, 200)
        self.assertEquals(m.headers["via"],
                          ["SIP/2.0/UDP client.com:5060;branch=z9hG4bK10;received=10.0.0.1"])
        self.assertEquals(m.headers["to"], ["sip:joe@proxy.com"])
        self.assertEquals(m.headers["contact"], ["sip:joe@client.com:1234"])
        self.assertEquals(m.headers["expires"], ["0"])
        self.assertEquals(self.countRegistrations(), 0)


    def testFailedAuthentication(self):
        self.registerBad()

        self.assertEquals(self.countRegistrations(), 0)
        self.assertEquals(len(self.sent), 1)
        dest, m = self.sent[0]
        self.assertEquals(m.code, 401)


    def testBasicAuthentication(self):
        self.registerGood()
        self.assertEquals(self.countRegistrations(), 1)
        self.assertEquals(len(self.sent), 1)
        dest, m = self.sent[0]
        self.assertEquals(m.code, 200)


    def testFailedBasicAuthentication(self):
        reg = self.proxy.registrar
        reg.authorizers = reg.authorizers.copy()
        reg.authorizers['basic'] = sip.BasicAuthorizer()

        r = sip.Request("REGISTER", "sip:proxy.com")
        r.addHeader("to", "sip:joe@proxy.com")
        r.addHeader("contact", "sip:joe@client.com:1234")
        r.addHeader("via", sip.Via("client.com").toString())
        r.addHeader("from", "sip:joe@proxy.com")
        r.addHeader("call-id", "8E0C617B69B2D91187C6000E35CE1034@proxy.com")
        r.addHeader("CSeq", "25317 REGISTER")
        r.addHeader("authorization", "Basic " + "userXname:password".encode('base64'))
        self.transport.datagramReceived(r.toString(), ("client.com", 5060))

        self.assertEquals(self.countRegistrations(), 0)
        self.assertEquals(len(self.sent), 1)
        dest, m = self.sent[0]
        self.assertEquals(m.code, 401)

    def testWrongToDomainRegister(self):
        r = sip.Request("REGISTER", "sip:proxy.com")
        r.addHeader("to", "sip:joe@foo.com")
        r.addHeader("from", "sip:joe@foo.com")
        r.addHeader("call-id", "8E0C617B69B2D91187C6000E35CE1034@proxy.com")
        r.addHeader("CSeq", "25317 REGISTER")
        r.addHeader("contact", "sip:joe@client.com:1234")
        r.addHeader("via", sip.Via("client.com").toString())
        self.transport.datagramReceived(r.toString(), ("client.com", 5060))

        self.assertEquals(self.sent[0][1].code , 401)

    def testWrongDomainLookup(self):
        self.realm.permissive = 0
        self.registerGood()
        url = sip.URL(username="joe", host="foo.com")
        f = unittest.deferredResult(self.proxy.findTargets(url))
        self.assertEquals(f[0], url)

    def testNoContactLookup(self):
        self.realm.permissive = 0
        self.registerGood()
        url = sip.URL(username="jane", host="proxy.com")
        f = unittest.deferredError(self.proxy.findTargets(url))
        f.trap(sip.SIPLookupError)
    testNoContactLookup.todo = "Fix cred to raise NoSuchUser when looking up nonexistent users"

    def countRegistrations(self):
        return self.realm.regs


class Client:

    def __init__(self):
         self.received = []

    def responseReceived(self, response, ct=None):
        self.received.append(response)

    def start(self, thingy):
        pass

    def sendMessage(self, msg, *etc):
        pass
    
class LiveTest(FakeClockTestCase):

    def setUp(self):
        r = TestRealm('proxy.com')
        p = cred.portal.Portal(r)
        p.registerChecker(PermissiveChecker())
        self.proxy = sip.Proxy(p)
        self.transport = sip.SIPTransport(self.proxy,
                                          ["proxy.com",'127.0.0.1'], 5060)
        self.serverPort = reactor.listenUDP(0, self.transport,
                                            interface="127.0.0.1")
        self.client = Client()
        self.clientTransport = sip.SIPTransport(self.client, ["localhost"],
                                                5060)
        self.clientPort = reactor.listenUDP(0, self.clientTransport,
                                            interface="127.0.0.1")
        self.serverPortNo = self.serverPort.getHost().port
        self.transport.port = self.serverPortNo
        self.clientTransport.port = self.clientPort.getHost().port        

    def tearDown(self):
        self.clock.advance(181)
        self.clientPort.stopListening()
        self.serverPort.stopListening()
        reactor.iterate()
        reactor.iterate()

    def testRegister(self):
        p = self.clientPort.getHost().port
        r = sip.Request("REGISTER", "sip:proxy.com")
        r.addHeader("to", "sip:joe@proxy.com")
        r.addHeader("from", "sip:joe@proxy.com")
        r.addHeader("contact", "sip:joe@127.0.0.1:%d" % p)
        r.addHeader("call-id", "8E0C617B69B2D91187C6000E35CE1034@proxy.com")
        r.addHeader("CSeq", "25317 REGISTER")
        r.addHeader("via", sip.Via("127.0.0.1", port=p).toString())
        self.clientTransport.sendRequest(r, ("127.0.0.1", self.serverPortNo))
        while not len(self.client.received):
            reactor.iterate()
        self.assertEquals(len(self.client.received), 1)
        r = self.client.received[0]
        self.assertEquals(r.code, 200)

registerRequest = """
REGISTER sip:intarweb.us SIP/2.0\r
Via: SIP/2.0/UDP 192.168.1.100:50609;branch=z9hG4bK74bf9;rport\r
From: <sip:exarkun@intarweb.us:50609>\r
To: <sip:exarkun@intarweb.us:50609>\r
Contact: "exarkun" <sip:exarkun@192.168.1.100:50609>\r
Call-ID: 94E7E5DAF39111D791C6000393764646@intarweb.us\r
CSeq: 9898 REGISTER\r
Expires: 500\r
User-Agent: X-Lite build 1061\r
Content-Length: 0\r
\r
"""

challengeResponse = """\
SIP/2.0 401 Unauthorized\r
Via: SIP/2.0/UDP 192.168.1.100:50609;branch=z9hG4bK74bf9;received=127.0.0.1;rport=5632\r
To: <sip:exarkun@intarweb.us:50609>\r
From: <sip:exarkun@intarweb.us:50609>\r
Call-ID: 94E7E5DAF39111D791C6000393764646@intarweb.us\r
CSeq: 9898 REGISTER\r
WWW-Authenticate: Digest nonce="92956076410767313901322208775",opaque="1674186428",qop="auth",algorithm="MD5",realm="intarweb.us"\r
\r
"""

authRequest = """\
REGISTER sip:intarweb.us SIP/2.0\r
Via: SIP/2.0/UDP 192.168.1.100:50609;branch=z9hG4bK74bf10;rport\r
From: <sip:exarkun@intarweb.us:50609>\r
To: <sip:exarkun@intarweb.us:50609>\r
Contact: "exarkun" <sip:exarkun@192.168.1.100:50609>\r
Call-ID: 94E7E5DAF39111D791C6000393764646@intarweb.us\r
CSeq: 9899 REGISTER\r
Expires: 500\r
Authorization: Digest username="exarkun",realm="intarweb.us",nonce="92956076410767313901322208775",response="4a47980eea31694f997369214292374b",uri="sip:intarweb.us",algorithm=MD5,opaque="1674186428"\r
User-Agent: X-Lite build 1061\r
Content-Length: 0\r
\r
"""

okResponse = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP 192.168.1.100:50609;branch=z9hG4bK74bf10;received=127.0.0.1;rport=5632\r
To: <sip:exarkun@intarweb.us:50609>\r
From: <sip:exarkun@intarweb.us:50609>\r
Call-ID: 94E7E5DAF39111D791C6000393764646@intarweb.us\r
CSeq: 9899 REGISTER\r
Contact: sip:exarkun@192.168.1.100:50609\r
Expires: 500\r
Content-length: 0\r
\r
"""

class FakeDigestAuthorizer(sip.DigestAuthorizer):
    def generateNonce(self):
        return '92956076410767313901322208775'
    def generateOpaque(self):
        return '1674186428'



class AuthorizationTestCase(FakeClockTestCase):

    def setUp(self):
        r = TestRealm("intarweb.us")
        p = cred.portal.Portal(r)
        c = cred.checkers.InMemoryUsernamePasswordDatabaseDontUse()
        c.addUser('exarkun@intarweb.us', 'password')
        r.addUser('exarkun@intarweb.us')
        p.registerChecker(c)
        self.proxy = sip.Proxy(p)
        self.siptransport = sip.SIPTransport(self.proxy,
                                             ["intarweb.us"], 5060)
        reg = self.proxy.registrar
        reg.authorizers = reg.authorizers.copy()
        reg.authorizers['digest'] = FakeDigestAuthorizer()
        self.transport = proto_helpers.FakeDatagramTransport()
        self.siptransport.transport = self.transport

    def tearDown(self):
        self.clock.advance(32)
    def testChallenge(self):
        self.siptransport.datagramReceived(registerRequest,
                                           ("127.0.0.1", 5632))
        self.assertEquals(self.transport.written[-1][0], challengeResponse)
        self.assertEquals(self.transport.written[-1][1], ("127.0.0.1", 5632))
        self.transport.written = []

        self.siptransport.datagramReceived(authRequest, ("127.0.0.1", 5632))

        self.assertEquals(self.transport.written[-1][0], okResponse)
        self.assertEquals(self.transport.written[-1][1], ("127.0.0.1", 5632))
        self.clock.advance(33)



# INVITE Alice -> Proxy 1
aliceInvite = """\
INVITE sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9\r
Max-Forwards: 70\r
Route: <sip:proxy1.org;lr>\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
Contact: <sip:alice@client.com>\r
\r
"""

# INVITE Proxy 1 -> Proxy 2
interproxyInvite = """\
INVITE sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;rport\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
Max-Forwards: 69\r
Record-Route: sip:proxy1.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
Contact: <sip:alice@client.com>\r
\r
"""

# 100 Trying Proxy 1 -> Alice
alice100Response = """\
SIP/2.0 100 Trying\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
To: Bob <sip:bob@proxy2.org>\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
\r
"""

# INVITE Proxy 2 -> Bob
bobInvite = """\
INVITE sip:bob@10.0.0.2 SIP/2.0\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bK78c4035c271376836957414fdf557c20;rport\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;received=10.1.0.1;rport=5060\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
Max-Forwards: 68\r
Record-Route: sip:proxy2.org:5060;lr\r
Record-Route: sip:proxy1.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
Contact: <sip:alice@client.com>\r
\r
"""

# Trying Proxy 2 -> Proxy 1
interproxy100Response = """\
SIP/2.0 100 Trying\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;received=10.1.0.1;rport=5060\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
\r
"""

# Ringing Bob -> Proxy 2
bob180Response = """\
SIP/2.0 180 Ringing\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bK78c4035c271376836957414fdf557c20;rport\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;received=10.1.0.1;rport=5060\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
Record-Route: sip:proxy2.org:5060;lr\r
Record-Route: sip:proxy1.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
Contact: <sip:bob@server.com>\r
CSeq: 1 INVITE\r
\r
"""

# 180 Ringing Proxy 2 -> Proxy 1
interproxy180Response = """\
SIP/2.0 180 Ringing\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;received=10.1.0.1;rport=5060\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
Record-Route: sip:proxy2.org:5060;lr\r
Record-Route: sip:proxy1.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
Contact: <sip:bob@server.com>\r
CSeq: 1 INVITE\r
\r
"""

# 180 Ringing Proxy 1 -> Alice
alice180Response = """\
SIP/2.0 180 Ringing\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
Record-Route: sip:proxy2.org:5060;lr\r
Record-Route: sip:proxy1.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
Contact: <sip:bob@server.com>\r
CSeq: 1 INVITE\r
\r
"""

 # 200 OK Bob -> Proxy 2
bob200Response = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bK78c4035c271376836957414fdf557c20;rport\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;received=10.1.0.1;rport=5060\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
Record-Route: sip:proxy2.org:5060;lr\r
Record-Route: sip:proxy1.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 2 INVITE\r
Contact: <sip:bob@server.com>\r
\r
"""

#  200 OK Proxy 2 -> Proxy 1
interproxy200Response = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;received=10.1.0.1;rport=5060\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
Record-Route: sip:proxy2.org:5060;lr\r
Record-Route: sip:proxy1.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 2 INVITE\r
Contact: <sip:bob@server.com>\r
\r
"""

# 200 OK Proxy 1 -> Alice
alice200Response = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
Record-Route: sip:proxy2.org:5060;lr\r
Record-Route: sip:proxy1.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 2 INVITE\r
Contact: <sip:bob@server.com>\r
\r
"""

# ACK Alice -> Proxy 1
aliceAckRequest = """\
ACK sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74b76\r
Max-Forwards: 70\r
Route: sip:proxy1.org:5060;lr\r
Route: sip:proxy2.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 ACK\r
\r
"""

# ACK Proxy 1 -> Proxy 2
interproxyAckRequest = """\
ACK sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1ab7cb324549af198a1faf2f9f455575;rport\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74b76;received=10.0.0.1\r
Max-Forwards: 69\r
Route: sip:proxy2.org:5060;lr\r
Record-Route: sip:proxy1.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 ACK\r
\r
"""

# ACK Proxy 2 -> Bob
bobAckRequest = """\
ACK sip:bob@10.0.0.2 SIP/2.0\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bKdabf9405095cfe3a7641e493e31e73d7;rport\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1ab7cb324549af198a1faf2f9f455575;received=10.1.0.1;rport=5060\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74b76;received=10.0.0.1\r
Max-Forwards: 68\r
Record-Route: sip:proxy2.org:5060;lr\r
Record-Route: sip:proxy1.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 ACK\r
\r
"""

# F18 BYE Bob -> Proxy 2
bobByeRequest = """\
BYE sip:alice@proxy1.org SIP/2.0\r
Via: SIP/2.0/UDP server.com:5060;branch=z9hG4bKnashds7\r
Max-Forwards: 70\r
Route: sip:proxy2.org:5060;lr\r
Route: sip:proxy1.org:5060;lr\r
From: Bob <sip:bob@proxy2.org>;tag=314159\r
To: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 BYE\r
\r
"""
# F19 BYE Proxy 2 -> Proxy 1
interproxyByeRequest = """\
BYE sip:alice@proxy1.org SIP/2.0\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bKc13670ea4bbb24758149818ab9c878cd;rport\r
Via: SIP/2.0/UDP server.com:5060;branch=z9hG4bKnashds7;received=10.0.0.2\r
Max-Forwards: 69\r
Record-Route: sip:proxy2.org:5060;lr\r
Route: sip:proxy1.org:5060;lr\r
From: Bob <sip:bob@proxy2.org>;tag=314159\r
To: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 BYE\r
\r
"""
# F20 BYE Proxy 1 -> Alice
aliceByeRequest = """\
BYE sip:alice@10.0.0.1 SIP/2.0\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK4be41468cfbab722d46f598f3d5e53a9;rport\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bKc13670ea4bbb24758149818ab9c878cd;received=10.1.0.2;rport=5060\r
Via: SIP/2.0/UDP server.com:5060;branch=z9hG4bKnashds7;received=10.0.0.2\r
Max-Forwards: 68\r
Record-Route: sip:proxy1.org:5060;lr\r
Record-Route: sip:proxy2.org:5060;lr\r
From: Bob <sip:bob@proxy2.org>;tag=314159\r
To: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 BYE\r
\r
"""

# F21 200 OK Alice -> Proxy 1
aliceByeResponse = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK4be41468cfbab722d46f598f3d5e53a9;rport\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bKc13670ea4bbb24758149818ab9c878cd;received=10.1.0.2;rport=5060\r
Via: SIP/2.0/UDP server.com:5060;branch=z9hG4bKnashds7;received=10.0.0.2\r
From: Bob <sip:bob@proxy2.org>;tag=314159\r
To: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 BYE\r
\r
"""
# F22 200 OK Proxy 1 -> Proxy 2
interproxyByeResponse = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bKc13670ea4bbb24758149818ab9c878cd;received=10.1.0.2;rport=5060\r
Via: SIP/2.0/UDP server.com:5060;branch=z9hG4bKnashds7;received=10.0.0.2\r
From: Bob <sip:bob@proxy2.org>;tag=314159\r
To: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 BYE\r
\r
"""

# F23 200 OK Proxy 2 -> Bob
bobByeResponse = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP server.com:5060;branch=z9hG4bKnashds7;received=10.0.0.2\r
From: Bob <sip:bob@proxy2.org>;tag=314159\r
To: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 BYE\r
\r
"""
###############
# Messages from 3.8
# F9 CANCEL Alice -> Proxy 1
aliceCancel = """\
CANCEL sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9\r
Max-Forwards: 70\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Route: sip:proxy1.org:5060;lr\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 CANCEL\r
\r
"""
#F10 200 OK Proxy 1 -> Alice
aliceCancel200 = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 CANCEL\r
\r
"""
#F11 CANCEL Proxy 1 -> Proxy 2
# the RFC has this as "CANCEL sip alice@proxy1.org" but I can't see how that works, or matters.
interproxyCancel = """\
CANCEL sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;rport\r
Max-Forwards: 70\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 CANCEL\r
\r
"""
# F12 200 OK Proxy 2 -> Proxy 1
interproxyCancel200 = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;received=10.1.0.1;rport=5060\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 CANCEL\r
\r
"""
#F13 CANCEL Proxy 2 -> Bob
bobCancel = """\
CANCEL sip:bob@10.0.0.2 SIP/2.0\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bK78c4035c271376836957414fdf557c20;rport\r
Max-Forwards: 70\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 CANCEL\r
\r
"""
#F14 200 OK Bob -> Proxy 2
bobCancel200 = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bK78c4035c271376836957414fdf557c20;rport;rport=5060\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 CANCEL\r
\r
"""
#F15 487 Request Terminated Bob -> Proxy 2
bob487 = """\
SIP/2.0 487 Request Terminated\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bK78c4035c271376836957414fdf557c20;rport\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;received=10.1.0.1;rport=5060\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
\r
"""
#F16 ACK Proxy 2 -> Bob
bob487Ack = """\
ACK sip:bob@10.0.0.2 SIP/2.0\r
Via: SIP/2.0/UDP proxy2.org:5060;branch=z9hG4bK78c4035c271376836957414fdf557c20;rport\r
Max-Forwards: 70\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 ACK\r
\r
"""
#F17 487 Request Terminated Proxy 2 -> Proxy 1
interproxy487 = """\
SIP/2.0 487 Request Terminated\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;received=10.1.0.1;rport=5060\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
\r
"""
#F18 ACK Proxy 1 -> Proxy 2
interproxy487Ack = """\
ACK sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP proxy1.org:5060;branch=z9hG4bK1456f8e2565d83971ccb7104399f879b;rport\r
Max-Forwards: 70\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 ACK\r
\r
"""
#F19 487 Request Terminated Proxy 1 -> Alice
alice487 = """\
SIP/2.0 487 Request Terminated\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
\r
"""
#F20 ACK Alice -> Proxy 1
alice487Ack = """\
ACK sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9\r
Max-Forwards: 70\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 ACK\r
\r
"""

###############
# Messages from 3.10

#F20 ACK Alice -> Proxy 1
alice408Ack = """\
ACK sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9\r
Max-Forwards: 70\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 ACK\r
\r
"""

class DoubleStatefulProxyTestCase(FakeClockTestCase):
    # Double the fun! Double the pain! Or double your money back!

    def setUp(self):
        r1 = TestRealm(domain="proxy1.org")
        a = FakeAvatar(r1,"alice@proxy1.org")
        a.registerAddress(sip.URL(host="10.0.0.1",username="alice"),3600)
        r1.users['alice@proxy1.org'] = a
        p1 = cred.portal.Portal(r1)
        p1.registerChecker(PermissiveChecker())
        self.proxy1 = sip.Proxy(p1)
        self.sip1 = sip.SIPTransport(self.proxy1,
                                     ["proxy1.org", "10.1.0.1"], 5060)
        r = TestRealm(domain="proxy2.org")
        a = FakeAvatar(r,"bob@proxy2.org")
        a.registerAddress(sip.URL(host="10.0.0.2",username="bob"),3600)
        r.users['bob@proxy2.org'] = a
        p = cred.portal.Portal(r)
        p.registerChecker(PermissiveChecker())
        self.proxy2 = sip.Proxy(p)
        self.sip2 = sip.SIPTransport(self.proxy2,
                                     ["proxy2.org", "10.1.0.2"], 5060)
        self.testMessages = []
        self.parser = sip.MessagesParser(self.testMessages.append)

        class FakeDatagramTransport1:
            def __init__(self):
                self.written = []                            
            def write(ft, packet, addr=None):
                ft.written.append(packet)
                if addr[0] != "10.0.0.1":
                    reactor.callLater(0, self.sip2.datagramReceived,
                                      packet, ("10.1.0.1", 5060))
                
        class FakeDatagramTransport2:
            def __init__(self):
                self.written = []                            
            def write(ft, packet, addr=None):
                ft.written.append(packet)
                if addr[0] == "10.1.0.1":
                    reactor.callLater(0, self.sip1.datagramReceived,
                                      packet, ("10.1.0.2", 5060))
                elif addr[0] != "10.0.0.2":
                    raise unittest.FailTest("Proxy 2 sent to a wrong host")
                
        ft1 = FakeDatagramTransport1()
        ft2 = FakeDatagramTransport2()        
        self.proxy1SendQueue = ft1.written
        self.proxy2SendQueue = ft2.written
        self.sip1.transport = ft1
        self.sip2.transport = ft2
        
        
        self.proxy1._lookupURI = self.proxy2._lookupURI = lambda uri: defer.succeed([(testurls.get(uri.host, uri.host), 5060)])

    def assertMsgEqual(self, first, second):
        self.testMessages[:] = []
        self.parser.dataReceived(first)
        self.parser.dataDone()
        self.parser.dataReceived(second)
        self.parser.dataDone()
        self.assertEqual(self.testMessages[0],  self.testMessages[1])
        
    def invite(self):
        self.sip1.datagramReceived(aliceInvite, ('10.0.0.1', 5060)) # F4
        reactor.iterate()
        self.assertEquals(len(self.proxy1SendQueue), 2)
        self.assertEquals(len(self.proxy2SendQueue), 2)

        self.assertMsgEqual(self.proxy1SendQueue[0], alice100Response) #F6
        self.assertMsgEqual(self.proxy1SendQueue[1], interproxyInvite) #F5
        self.assertMsgEqual(self.proxy2SendQueue[0], interproxy100Response) #F8
        self.assertMsgEqual(self.proxy2SendQueue[1], bobInvite) #F7
        self.resetq()


    def inviteAnd180(self):
        self.invite()
        self.sip2.datagramReceived(bob180Response, ("10.0.0.2", 5060)) # F9
        reactor.iterate()
        self.assertEquals(len(self.proxy2SendQueue), 1)
        self.assertEquals(len(self.proxy1SendQueue), 1)
        self.assertMsgEqual(self.proxy2SendQueue[0], interproxy180Response)#F10
        self.assertMsgEqual(self.proxy1SendQueue[0], alice180Response) #F11
        self.resetq()


    def testSuccessfulCallFlow(self):
        #Adapted from RFC 3665, section 3.2 (minus proxy auth and TCP)
        self.inviteAnd180()

        self.sip2.datagramReceived(bob200Response, ("10.0.0.2", 5060)) # F12
        reactor.iterate()
        self.assertEquals(len(self.proxy2SendQueue), 1)
        self.assertEquals(len(self.proxy1SendQueue), 1)

        self.assertMsgEqual(self.proxy2SendQueue[0], interproxy200Response)#F13
        self.assertMsgEqual(self.proxy1SendQueue[0], alice200Response) #F14
        self.resetq()

        self.assertEquals(len(self.sip1.serverTransactions), 0)
        self.assertEquals(len(self.sip2.serverTransactions), 0)
        self.assertEquals(len(self.sip1.clientTransactions), 0)
        self.assertEquals(len(self.sip2.serverTransactions), 0)

        self.sip1.datagramReceived(aliceAckRequest, ('10.0.0.1', 5060)) # F15
        reactor.iterate()
        self.assertEquals(len(self.proxy2SendQueue), 1)
        self.assertEquals(len(self.proxy1SendQueue), 1)
        self.parser.dataReceived(interproxyAckRequest);self.parser.dataDone() # F16
        self.assertMsgEqual(self.proxy1SendQueue[0], interproxyAckRequest)#F16
        self.assertMsgEqual(self.proxy2SendQueue[0], bobAckRequest)#F17
        self.resetq()

        self.assertEquals(len(self.sip1.serverTransactions), 0)
        self.assertEquals(len(self.sip2.serverTransactions), 0)
        self.assertEquals(len(self.sip1.clientTransactions), 0)
        self.assertEquals(len(self.sip2.serverTransactions), 0)

        self.sip2.datagramReceived(bobByeRequest, ('10.0.0.2', 5060)) # F18
        reactor.iterate()
        self.assertEquals(len(self.proxy2SendQueue), 1)
        self.assertEquals(len(self.proxy1SendQueue), 1)

        self.assertMsgEqual(self.proxy2SendQueue[0], interproxyByeRequest)#F19
        self.assertMsgEqual(self.proxy1SendQueue[0], aliceByeRequest)#F20
        self.resetq()


        self.sip1.datagramReceived(aliceByeResponse, ('10.0.0.1', 5060)) # F21
        reactor.iterate()
        self.assertEquals(len(self.proxy2SendQueue), 1)
        self.assertEquals(len(self.proxy1SendQueue), 1)

        self.assertMsgEqual(self.proxy1SendQueue[0], interproxyByeResponse)#F22
        self.assertMsgEqual(self.proxy2SendQueue[0], bobByeResponse)#F23
        self.resetq()

        self.clock.advance(33)
        reactor.iterate()
        
        self.assertEquals(len(self.sip1.serverTransactions), 0)
        self.assertEquals(len(self.sip2.serverTransactions), 0)
        self.assertEquals(len(self.sip1.clientTransactions), 0)
        self.assertEquals(len(self.sip2.serverTransactions), 0)
        self.assertEquals(len(self.proxy1.responseContexts), 0)
        self.assertEquals(len(self.proxy2.responseContexts), 0)
        
    def testCancelAfter180(self):
        #Section 3.8
        self.inviteAnd180()
        self.sip1.datagramReceived(aliceCancel, ('10.0.0.1', 5060))
        reactor.iterate()
        self.sip2.datagramReceived(bobCancel200, ('10.0.0.2', 5060))
        reactor.iterate()
        self.assertEquals(len(self.proxy1SendQueue), 2)
        self.assertEquals(len(self.proxy2SendQueue), 2)
        self.assertMsgEqual(self.proxy1SendQueue[0], aliceCancel200)
        self.assertMsgEqual(self.proxy1SendQueue[1], interproxyCancel)
        self.assertMsgEqual(self.proxy2SendQueue[0], interproxyCancel200)
        self.assertMsgEqual(self.proxy2SendQueue[1], bobCancel)
        self.resetq()

        self.sip2.datagramReceived(bob487, ('10.0.0.2', 5060))
        reactor.iterate()
        self.assertEquals(len(self.proxy2SendQueue), 2)
        self.assertEquals(len(self.proxy1SendQueue), 2)
        #This order is opposite from RFC3665's diagram
        #there, the ACK is sent before the 487. I don't know if this matters.
        self.assertMsgEqual(self.proxy2SendQueue[0], interproxy487)
        self.assertMsgEqual(self.proxy2SendQueue[1], bob487Ack)
        self.assertMsgEqual(self.proxy1SendQueue[0], alice487)
        self.assertMsgEqual(self.proxy1SendQueue[1], interproxy487Ack)
        self.resetq()
        self.sip1.datagramReceived(alice487Ack, ('10.0.0.1', 5060))
        self.assertEquals(len(self.proxy1SendQueue), 0)
        self.clock.advance(33)
        reactor.iterate()
        reactor.iterate()
        self.clock.advance(10)  # twisted trunk requires this second .advance()
        reactor.iterate()       # for some reason...?  different timing
        reactor.iterate()       # algorithm?

        self.assertEquals(len(self.sip1.serverTransactions), 0)
        self.assertEquals(len(self.sip2.serverTransactions), 0)
        self.assertEquals(len(self.sip1.clientTransactions), 0)
        self.assertEquals(len(self.sip2.serverTransactions), 0)

    def resetq(self):
        del self.proxy1SendQueue[:]
        del self.proxy2SendQueue[:]


    def testNoResponse(self):
        #this test is a piece of crap, really, there need to be a lot more asserts
        #but at least the code path gets exercised =/
        self.invite()
        for x in range(330):
            self.clock.advance(0.1)
            reactor.iterate()
        #self.assertEquals(len(self.proxy2SendQueue), 7)
        self.failUnless(len(self.proxy2SendQueue) > 6) # close enough
        self.sip1.datagramReceived(alice408Ack, ('10.0.0.1',5060))
        self.clock.advance(32) #wait for timer D
        reactor.iterate()
        reactor.iterate()
        self.resetq()


