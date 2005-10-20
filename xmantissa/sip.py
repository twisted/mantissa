# Copyright 2005 Divmod, Inc.  See LICENSE file for details
# -*- test-case-name: mantissa.test.test_sip -*-

# "I have always wished that my computer would be as easy to use as my
# telephone. My wish has come true. I no longer know how to use my
# telephone." - Bjarne Stroustrup

import socket, random, md5, sys, urllib

from twisted.python import log, util
from twisted.internet import protocol, defer, reactor, abstract
from twisted.names import client

from twisted.cred import credentials
from twisted.cred.error import UnauthorizedLogin
from twisted.protocols import basic

from zope.interface import  Interface, implements

from axiom.userbase  import Preauthenticated
from axiom.errors import NoSuchUser

from epsilon.modal import mode, ModalType

debuggingEnabled=0

def debug(txt):
    if debuggingEnabled:
        print (txt)

VIA_COOKIE = "z9hG4bK"
PORT = 5060
DEFAULT_REGISTRATION_LIFETIME = 3600

# SIP headers have short forms
shortHeaders = {"call-id": "i",
                "contact": "m",
                "content-encoding": "e",
                "content-length": "l",
                "content-type": "c",
                "from": "f",
                "subject": "s",
                "to": "t",
                "via": "v",
                }

longHeaders = {}
for k, v in shortHeaders.items():
    longHeaders[v] = k
del k, v

statusCodes = {
    100: "Trying",
    180: "Ringing",
    181: "Call Is Being Forwarded",
    182: "Queued",

    200: "OK",

    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Moved Temporarily",
    303: "See Other",
    305: "Use Proxy",
    380: "Alternative Service",

    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    413: "Request Entity Too Large",
    414: "Request-URI Too Large",
    415: "Unsupported Media Type",
    420: "Bad Extension",
    480: "Temporarily not available",
    481: "Call Leg/Transaction Does Not Exist",
    482: "Loop Detected",
    483: "Too Many Hops",
    484: "Address Incomplete",
    485: "Ambiguous",
    486: "Busy Here",
    487: "Request Cancelled",

    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Time-out",
    505: "SIP Version not supported",

    600: "Busy Everywhere",
    603: "Decline",
    604: "Does not exist anywhere",
    606: "Not Acceptable",
}
# some headers change case strangely.
specialCases = {
    'cseq': 'CSeq',
    'call-id': 'Call-ID',
    'www-authenticate': 'WWW-Authenticate',
    'proxy-authenticate': 'Proxy-Authenticate',
    'proxy-authorization':'Proxy-Authorization',
    'record-route':'Record-Route',
}



def DigestCalcHA1(
    pszAlg,
    pszUserName,
    pszRealm,
    pszPassword,
    pszNonce,
    pszCNonce,
):
    m = md5.md5()
    m.update(pszUserName)
    m.update(":")
    m.update(pszRealm)
    m.update(":")
    m.update(pszPassword)
    HA1 = m.digest()
    if pszAlg == "md5-sess":
        m = md5.md5()
        m.update(HA1)
        m.update(":")
        m.update(pszNonce)
        m.update(":")
        m.update(pszCNonce)
        HA1 = m.digest()
    return HA1.encode('hex')

def DigestCalcResponse(
    HA1,
    pszNonce,
    pszNonceCount,
    pszCNonce,
    pszQop,
    pszMethod,
    pszDigestUri,
    pszHEntity,
):
    m = md5.md5()
    m.update(pszMethod)
    m.update(":")
    m.update(pszDigestUri)
    if pszQop == "auth-int":
        m.update(":")
        m.update(pszHEntity)
    HA2 = m.digest().encode('hex')

    m = md5.md5()
    m.update(HA1)
    m.update(":")
    m.update(pszNonce)
    m.update(":")
    if pszNonceCount and pszCNonce: # pszQop:
        m.update(pszNonceCount)
        m.update(":")
        m.update(pszCNonce)
        m.update(":")
        m.update(pszQop)
        m.update(":")
    m.update(HA2)
    hash = m.digest().encode('hex')
    return hash

class Via:
    """A SIP Via header."""

    def __init__(self, host, port=PORT, transport="UDP", ttl=None, hidden=False,
                 received=None, rport=None, branch=None, maddr=None):
        self.transport = transport
        self.host = host
        self.port = port
        self.ttl = ttl
        self.hidden = hidden
        self.received = received
        self.rport = rport
        self.branch = branch
        self.maddr = maddr

    def toString(self):
        s = "SIP/2.0/%s %s:%s" % (self.transport, self.host, self.port)
        if self.hidden:
            s += ";hidden"
        for n in "ttl", "branch", "maddr", "received", "rport":
            value = getattr(self, n)
            if value == True:
                s += ";" + n
            elif value != None:
                s += ";%s=%s" % (n, value)
        return s


def parseViaHeader(value):
    """Parse a Via header, returning Via class instance."""
    try:
        parts = value.split(";")
        sent, params = parts[0], parts[1:]
        protocolinfo, by = sent.split(" ", 1)
        result = {}
        pname, pversion, transport = protocolinfo.split("/")
        if pname != "SIP" or pversion != "2.0":
            raise SIPError(400, "wrong protocol or version: %r" % value)
        result["transport"] = transport
        if ":" in by:
            host, port = by.split(":")
            result["port"] = int(port)
            result["host"] = host
        else:
            result["host"] = by
        for p in params:
            # it's the comment-striping dance!
            p = p.strip().split(" ", 1)
            if len(p) == 1:
                p, comment = p[0], ""
            else:
                p, comment = p
            if p == "hidden":
                result["hidden"] = True
                continue
            parts = p.split("=", 1)
            if len(parts) == 1:
                name, value = parts[0], True
            else:
                name, value = parts
                if name in ("rport", "ttl"):
                    value = int(value)
            result[name] = value
        return Via(**result)
    except:
        raise SIPError(400)

class URL:
    """A SIP URL."""

    def __init__(self, host, username=None, password=None, port=None,
                 transport=None, usertype=None, method=None,
                 ttl=None, maddr=None, tag=None, other=None, headers=None):
        self.username = username
        self.host = host
        self.password = password
        self.port = port
        self.transport = transport
        self.usertype = usertype
        self.method = method
        self.tag = tag
        self.ttl = ttl
        self.maddr = maddr
        if other == None:
            self.other = {}
        else:
            self.other = other
        if headers == None:
            self.headers = {}
        else:
            self.headers = headers

    def toCredString(self):
        return '%s@%s' % (self.username, self.host)

    def toString(self):
        l = []; w = l.append
        w("sip:")
        if self.username != None:
            w(urllib.quote(self.username))
            if self.password != None:
                w(":%s" % (urllib.quote(self.password)))
            w("@")
        w(self.host)
        if self.port != None:
            w(":%d" % self.port)
        if self.usertype != None:
            w(";user=%s" % self.usertype)
        for n in ("transport", "ttl", "maddr", "method", "tag"):
            v = getattr(self, n)
            if v != None:
                w(";%s=%s" % (urllib.quote(n), urllib.quote(v)))
        for k, v in self.other.iteritems():
            if v:
                w(";%s=%s" % (urllib.quote(k), urllib.quote(v)))
            else:
                w(";%s" % k)
        if self.headers:
            w("?")
            w("&".join([("%s=%s" % (specialCases.get(h) or urllib.quote(h).capitalize(), urllib.quote(v))) for (h, v) in self.headers.items()]))
        return "".join(l)

    def __str__(self):
        return self.toString()

    def __repr__(self):
        return '<sip.URL %s>' % self.toString()

    def __cmp__(self, other):
        return cmp(self.__dict__, other.__dict__)

    def __hash__(self):
        #I could include the other stuff but what's the point?
        #this is the most usual stuff and python is very kind to collisions
        return hash((self.host, self.username, self.port, tuple(self.headers.items())))

def parseURL(url, host=None, port=None):
    """Return string into URL object.

    URIs are of of form 'sip:user@example.com'.
    """
    d = {}
    if not url.startswith("sip:"):
        raise SIPError(416, "Unsupported URI scheme: " + url[:4])
    parts = url[4:].split(";")
    userdomain, params = parts[0], parts[1:]
    udparts = userdomain.split("@", 1)
    if len(udparts) == 2:
        userpass, hostport = udparts
        upparts = userpass.split(":", 1)
        if len(upparts) == 1:
            d["username"] = urllib.unquote(upparts[0])
        else:
            d["username"] = urllib.unquote(upparts[0])
            d["password"] = urllib.unquote(upparts[1])
    else:
        hostport = udparts[0]
    hpparts = hostport.split(":", 1)
    if len(hpparts) == 1:
        d["host"] = hpparts[0]
    else:
        d["host"] = hpparts[0]
        d["port"] = int(hpparts[1])
    if host != None:
        d["host"] = host
    if port != None:
        d["port"] = port
    for p in params:
        if p == params[-1] and "?" in p:
            d["headers"] = h = {}
            p, headers = p.split("?", 1)
            for header in headers.split("&"):
                k, v = header.split("=")
                h[urllib.unquote(k)] = urllib.unquote(v)
        nv = p.split("=", 1)
        if len(nv) == 1:
            d.setdefault("other", {})[urllib.unquote(p)] = ''
            continue
        name, value = map(urllib.unquote, nv)
        if name == "user":
            d["usertype"] = value
        elif name in ("transport", "ttl", "maddr", "method", "tag"):
            if name == "ttl":
                value = int(value)
            d[name] = value
        else:
            d.setdefault("other", {})[name] = value
    return URL(**d)


def cleanRequestURL(url):
    """Clean a URL from a Request line."""
    url.transport = None
    url.maddr = None
    url.ttl = None
    url.headers = {}


def parseAddress(address, host=None, port=None, clean=0):
    """Return (name, uri, params) for From/To/Contact header.

    @param clean: remove unnecessary info, usually for From and To headers.

    Although many headers such as From can contain any valid URI, even those
    with schemes other than 'sip', this function raises SIPError if the scheme
    is not 'sip' because the upper layers do not support it.
    """
    def splitParams(paramstring):
        params = {}
        paramstring = paramstring.strip()
        if paramstring:
            for l in paramstring.split(";"):
                if not l:
                    continue
                x = l.split("=")
                if len(x) > 1:
                    params[x[0]] = x[1]
                else:
                    params [x[0]] = ''
        return params
    try:
        address = address.strip()
        # simple 'sip:foo' case
        if not '<' in address:
            i = address.rfind(";tag=")
            if i > -1:

                params = splitParams(address[i:])
                address = address[:i]
            else:
                params = {}
            return "", parseURL(address, host=host, port=port), params
        params = {}
        name, url = address.split("<", 1)
        name = name.strip()
        if name.startswith('"'):
            name = name[1:]
        if name.endswith('"'):
            name = name[:-1]
        import re
        name = re.sub(r'\\(.)', r'\1', name)
        url, paramstring = url.split(">", 1)
        url = parseURL(url, host=host, port=port)
        params = splitParams(paramstring)
        if clean:
            # rfc 2543 6.21
            url.ttl = None
            url.headers = {}
            url.transport = None
            url.maddr = None
        return name.decode('utf8','replace'), url, params
    except:
        log.err()
        raise SIPError(400)
    
class Message:
    """A SIP message."""

    length = None

    def __init__(self, version):
        self.headers = util.OrderedDict() # map name to list of values
        self.body = ""
        self.finished = 0
        self.version = version

    def copy(self):
        c = Message(self.version)
        c.headers = self.headers.copy()
        c.body = self.body
        c.finished = self.finished
        return c

    def __eq__(self, other):
        return (other.__class__ == self.__class__
                and self.version == other.version
                and dict([(k,v) for k,v in self.headers.items() if v]) == dict([(k,v) for k,v in other.headers.items() if v])
                and self.body == other.body)
    
    def addHeader(self, name, value):
        name = name.lower()
        name = longHeaders.get(name, name)
        if name == "content-length":
            self.length = int(value)
        self.headers.setdefault(name,[]).append(value)

    def bodyDataReceived(self, data):
        self.body += data

    def creationFinished(self):
        if (self.length != None) and (self.length != len(self.body)):
            raise ValueError, "wrong body length"
        self.finished = 1

    def toString(self):
        s = "%s\r\n" % self._getHeaderLine()
        for n, vs in self.headers.items():
            for v in vs:
                s += "%s: %s\r\n" % (specialCases.get(n) or n.capitalize(), v)
        s += "\r\n"
        s += self.body
        return s

    def _getHeaderLine(self):
        raise NotImplementedError


class Request(Message):
    """A Request for a URI"""


    def __init__(self, method, uri, version="SIP/2.0"):
        Message.__init__(self, version)
        self.method = method
        if isinstance(uri, URL):
            self.uri = uri
        else:
            self.uri = parseURL(uri)
            cleanRequestURL(self.uri)

    def copy(self):
        c = Message.copy(self)
        c.__class__ = Request
        c.method = self.method
        c.uri = self.uri
        return c

    def __eq__(self, other):
        return Message.__eq__(self, other) and self.method == other.method and self.uri == other.uri

    def __repr__(self):
        return "<SIP Request %d:%s %s>" % (id(self), self.method, self.uri.toString())

    def _getHeaderLine(self):
        return "%s %s %s" % (self.method, self.uri.toString(), self.version)


class Response(Message):
    """A Response to a URI Request"""

    def __init__(self, code, phrase=None, version="SIP/2.0"):
        Message.__init__(self, version)
        self.code = code
        if phrase == None:
            phrase = statusCodes[code]
        self.phrase = phrase

    def __eq__(self, other):
        return Message.__eq__(self, other) and self.code == other.code

    def __repr__(self):
        return "<SIP Response %d:%s>" % (id(self), self.code)

    def _getHeaderLine(self):
        return "SIP/2.0 %s %s" % (self.code, self.phrase)

def splitMultiHeader(s):
    "Split a header on commas, ignoring commas in quotes and escaped quotes."
    headers = []
    last = 0
    quoted = False
    for i in xrange(len(s)):
        if s[i] == '"':
            quoted = ~quoted
            if i == 0: continue
            j = i-1
            while s[j] == '\\':
                quoted = ~quoted
                j = j-1
        if not quoted and s[i] == ',':
            headers.append(s[last:i])
            last = i+1
    headers.append(s[last:])
    return headers



class MessagesParser(basic.LineReceiver):
    """A SIP messages parser.

    Expects dataReceived, dataDone repeatedly,
    in that order. Shouldn't be connected to actual transport.
    """

    version = "SIP/2.0"
    acceptResponses = 1
    acceptRequests = 1
    state = "firstline" # or "headers", "body" or "invalid"
    multiheaders = ['accept','accept-encoding', 'accept-language', 'alert-info', 'allow', 'authentication-info', 'call-info',  'content-encoding', 'content-language', 'error-info', 'in-reply-to', 'proxy-require',  'require',  'supported', 'unsupported', 'via', 'warning']
    multiAddressHeaders = ['route', 'record-route', 'contact']
    debug = 0

    def __init__(self, messageReceivedCallback):
        self.messageReceived = messageReceivedCallback
        self.reset()

    def reset(self, remainingData=""):
        self.state = "firstline"
        self.length = None # body length
        self.bodyReceived = 0 # how much of the body we received
        self.message = None
        self.setLineMode(remainingData)

    def invalidMessage(self, exc=None):
        self.dataDone()
        if isinstance(exc, SIPError):
            raise exc
        else:
            raise SIPError(400)

    def dataDone(self):
        # clear out any buffered data that may be hanging around
        self.clearLineBuffer()
        if self.state == "firstline":
            return
        if self.state != "body":
            self.reset()
            return
        if self.length == None:
            # no content-length header, so end of data signals message done
            self.messageDone()
        elif self.length < self.bodyReceived:
            # aborted in the middle
            self.reset()
        else:
            # we have enough data and message wasn't finished? something is wrong
            raise RuntimeError, "corrupted or overflowed SIP packet"

    def dataReceived(self, data):
        try:
            basic.LineReceiver.dataReceived(self, data)
        except Exception, e:
            log.err()
            self.invalidMessage(e)

    def handleFirstLine(self, line):
        """Expected to create self.message."""
        raise NotImplementedError

    def lineLengthExceeded(self, line):
        self.invalidMessage()

    def lineReceived(self, line):
        if self.state == "firstline":
            while line.startswith("\n") or line.startswith("\r"):
                line = line[1:]
            if not line:
                return
            try:
                a, b, c = line.split(" ", 2)
            except ValueError:
                self.invalidMessage()
                return
            if a == "SIP/2.0" and self.acceptResponses:
                # response
                try:
                    code = int(b)
                except ValueError:
                    self.invalidMessage()
                    return
                self.message = Response(code, c)
            elif c == "SIP/2.0" and self.acceptRequests:
                self.message = Request(a, b)
            else:
                self.invalidMessage()
                return
            self.state = "headers"
            self.prevline = None
            return
        else:
            assert self.state == "headers"
        if line:
            x = line.lstrip()
            if line != x:
                #leading whitespace: this is a continuation line.
                self.prevline += x
            else:
                #new header
                if self.prevline:
                    try:
                        self.processHeaderLine(self.prevline)
                    except ValueError:
                        self.invalidMessage()
                        return
                self.prevline = line

        else:
            # CRLF, we now have message body until self.length bytes,
            # or if no length was given, until there is no more data
            # from the connection sending us data.
            self.state = "body"
            try:
                self.processHeaderLine(self.prevline)
            except ValueError:
                self.invalidMessage()
                return
            if self.length == 0:
                self.messageDone()
                return
            self.setRawMode()

    def processHeaderLine(self, line):
        name, value = line.split(":", 1)
        name, value = name.rstrip().lower(), value.lstrip()

        if name in self.multiheaders:
            multi = value.split(',')
            if multi:
                for v in multi:
                    self.message.addHeader(name, v.strip())
            else:
                self.message.addHeader(v)
        elif name in self.multiAddressHeaders:
            for val in splitMultiHeader(value):
                self.message.addHeader(name, val)
        else:
            self.message.addHeader(name, value)
        if name.lower() == "content-length":
            self.length = int(value.lstrip())

    def messageDone(self, remainingData=""):
        assert self.state == "body"
        self.message.creationFinished()
        self.messageReceived(self.message)
        self.reset(remainingData)

    def rawDataReceived(self, data):
        if self.length == None:
            self.message.bodyDataReceived(data)
        else:
            dataLen = len(data)
            expectedLen = self.length - self.bodyReceived
            if dataLen > expectedLen:
                self.message.bodyDataReceived(data[:expectedLen])
                self.messageDone(data[expectedLen:])
                return
            else:
                self.bodyReceived += dataLen
                self.message.bodyDataReceived(data)
                if self.bodyReceived == self.length:
                    self.messageDone()



class SIPError(Exception):
    def __init__(self, code, phrase=None):
        if phrase is None:
            phrase = statusCodes[code]
        Exception.__init__(self, "SIP error (%d): %s" % (code, phrase))
        self.code = code
        self.phrase = phrase

class SIPLookupError(SIPError):
    """An error raised specifically for SIP lookup errors.
    """
    def __init__(self, code=404, phrase=None):
        SIPError.__init__(self, code=code, phrase=phrase)

class RegistrationError(SIPError):
    """Registration was not possible."""

class ISIPEvent(Interface):
    "A log message concerning SIP"


class IAuthorizer(Interface):
    def getChallenge(peer):
        """Generate a challenge the client may respond to.

        @type peer: C{tuple}
        @param peer: The client's address

        @rtype: C{str}
        @return: The challenge string
        """

    def decode(response):
        """Create a credentials object from the given response.

        @type response: C{str}
        """



class BasicAuthorizer:
    """Authorizer for insecure Basic (base64-encoded plaintext) authentication.

    This form of authentication is broken and insecure.  Do not use it.
    """

    implements(IAuthorizer)

    def getChallenge(self, peer):
        return None

    def decode(self, response):
        # At least one SIP client improperly pads its Base64 encoded messages
        for i in range(3):
            try:
                creds = (response + ('=' * i)).decode('base64')
            except:
                pass
            else:
                break
        else:
            # Totally bogus
            raise SIPError(400)
        p = creds.split(':', 1)
        if len(p) == 2:
            return credentials.UsernamePassword(*p)
        raise SIPError(400)

class DigestedCredentials(credentials.UsernameHashedPassword):
    """Yet Another Simple Digest-MD5 authentication scheme"""

    def __init__(self, username, fields, challenges):
        self.username = username
        self.fields = fields
        self.challenges = challenges

    def checkPassword(self, password):
        method = 'REGISTER'
        response = self.fields.get('response')
        uri = self.fields.get('uri')
        nonce = self.fields.get('nonce')
        cnonce = self.fields.get('cnonce')
        nc = self.fields.get('nc')
        algo = self.fields.get('algorithm', 'MD5')
        qop = self.fields.get('qop', 'auth')
        opaque = self.fields.get('opaque')

        if opaque not in self.challenges:
            return False
        del self.challenges[opaque]

        user, domain = self.username.split('@', 1)
        if uri is None:
            uri = 'sip:' + domain

        expected = DigestCalcResponse(
            DigestCalcHA1(algo, user, domain, password, nonce, cnonce),
            nonce, nc, cnonce, qop, method, uri, None,
        )

        return expected == response

class DigestAuthorizer:
    CHALLENGE_LIFETIME = 15

    implements(IAuthorizer)

    def __init__(self):
        self.outstanding = {}

    def generateNonce(self):
        c = tuple([random.randrange(sys.maxint) for _ in range(3)])
        c = '%d%d%d' % c
        return c

    def generateOpaque(self):
        return str(random.randrange(sys.maxint))

    def getChallenge(self, peer):
        c = self.generateNonce()
        o = self.generateOpaque()
        self.outstanding[o] = c
        return ','.join((
            'nonce="%s"' % c,
            'opaque="%s"' % o,
            'qop="auth"',
            'algorithm="MD5"',
        ))

    def decode(self, response):
        def unq(s):
            if s[0] == s[-1] == '"':
                return s[1:-1]
            return s
        response = ' '.join(response.splitlines())
        parts = response.split(',')
        auth = dict([(k.strip(), unq(v.strip())) for (k, v) in [p.split('=', 1) for p in parts]])
        try:
            username = auth['username']
        except KeyError:
            raise SIPError(401)
        try:
            return DigestedCredentials(username, auth, self.outstanding)
        except:
            raise SIPError(400)

def responseFromRequest(code, request):
       response = Response(code)
       for name in ("via", "to", "from", "call-id", "cseq"):
           response.headers[name] = request.headers.get(name, [])[:]

       return response

def computeBranch(msg):
        """Create a branch tag to uniquely identify this message.  See
        RFC3261 sections 8.1.1.7 and 16.6.8."""
        if msg.headers.has_key('via') and msg.headers['via']:
            oldvia = msg.headers['via'][0]
        else:
            oldvia = ''
        return VIA_COOKIE + md5.new((parseAddress(msg.headers['to'][0])[2].get('tag','') +
                                    parseAddress(msg.headers['from'][0])[2].get('tag','')+
                                   msg.headers['call-id'][0] +
                                   msg.uri.toString() +
                                   oldvia +  
                                   msg.headers['cseq'][0].split(' ')[0])
                                  ).hexdigest()

class IContact(Interface):
    """A user of a registrar or proxy"""

    def registerAddress(physicalURL, expiry):
        """Register the physical address of a logical URL.

        @return: Deferred of C{Registration} or failure with RegistrationError.
        """

    def unregisterAddress():
        """Unregister the physical address of a logical URL.

        @return: Deferred of C{Registration} or failure with RegistrationError.
        """

    def getRegistrationInfo():
        """Get registration info for logical URL.

        @return: Deferred of C{Registration} object or failure of SIPLookupError.
        """

    def callIncoming(name, callerURI, callerContact):
        """Record an incoming call with a user's name, the incoming
        SIP URI, and, if they are registered with our system, their
        caller IContact implementor.

        You may *decline* an incoming call by raising an exception in
        this method.  A SIPError is preferred.
        """

    def callOutgoing(name, calleeURI):
        """Record an outgoing call.
        """


T1 = 0.5
T2 = 4
T4 = 5

class ClientInviteTransaction(object):
    __metaclass__ = ModalType
    initialMode = 'calling'
    modeAttribute = 'mode'
    
    def __init__(self, transport, tu, invite, peerURL):
        self.transport = transport
        self.tu = tu
        self.request = invite
        self.peer = peerURL
        self.response = None
        self.waitingToCancel = False
        self.branch = computeBranch(invite)
        self.transport.clientTransactions[self.branch] = self
        self.start()
        
    def transitionTo(self, stateName):
        self.end()
        self.mode = stateName
        self.start()

    def sendInvite(self):
        self.transport.sendRequest(self.request, self.peer)

    def transportError(self, err):
        self.tu.transportError(self, err)
        self.transitionTo('terminated')
        

    def ack(self, msg):        
        "Builds an ACK according to the rules in 17.1.1.3, RFC3261."
        ack = Request('ACK',self.request.uri)
        for name in ("from", "call-id", 'route'):
            ack.headers[name] = self.request.headers.get(name, [])[:]
        ack.addHeader('cseq', "%s ACK" % self.request.headers['cseq'][0].split(' ',1)[0])
        ack.headers['to'] = msg.headers['to']
        ack.headers['max-forwards'] = ['70']
        ack.addHeader('via', Via(self.transport.host,
                                  self.transport.port,
                                  rport=True,
                                  branch=self.branch).toString())
        self.transport.sendRequest(ack, self.peer)

    def sendCancel(self):
        cancel = Request("CANCEL", self.request.uri)
        for hdr in ('from','to','call-id'):
            cancel.addHeader(hdr, self.request.headers[hdr][0])
        cancel.addHeader('max-forwards','70')
        cancel.addHeader('cseq', "%s CANCEL" % self.request.headers['cseq'][0].split(' ',1)[0])
        cancel.addHeader('via', Via(self.transport.host,
                                    self.transport.port,
                                    rport=True,
                                    branch=self.branch).toString())
        self.transport.sendRequest(cancel, self.peer)

    
    class calling(mode):

        def start(self):
            debug("ClientInvite %s transitioning to 'calling'" % (self.peer,))
            self.timerATries = 0

            def timerARetry():
                self.timerATries +=1
                self.sendInvite()
                self.timerA = reactor.callLater(self.timerATries*T1,
                                                timerARetry)
            timerARetry()
            
            self.timerB = reactor.callLater(64*T1, self.timeout)

        def messageReceived(self, msg):
            self.response = msg
            self.tu.responseReceived(msg,self)
            if 100 <= msg.code < 200:
                if self.waitingToCancel:
                    self.sendCancel()
                    return
                self.transitionTo('proceeding')
            elif 200 <= msg.code < 300:
                self.transitionTo('terminated')
            elif 300 <= msg.code < 700:
                self.ack(msg)
                self.transitionTo('completed')


        def end(self):
            if self.timerA.active():
                self.timerA.cancel()
            if self.timerB.active():
                self.timerB.cancel()

        def timeout(self):
            if self.waitingToCancel:
                self.response = responseFromRequest(487, self.request)
            else:
                self.response = responseFromRequest(408, self.request)
            self.transitionTo('terminated')

        def cancel(self):
            self.waitingToCancel = True
            
    class proceeding(mode):
        def start(self):
            debug("ClientInvite %s transitioning to 'proceeding'" % (self.peer,))

        def messageReceived(self, msg):
            self.response = msg
            self.tu.responseReceived(msg, self)
            if 100 <= msg.code < 200:
                pass
            elif 200 <= msg.code < 300:
                self.transitionTo('terminated')
            elif 300 <= msg.code < 700:
                self.ack(msg)
                self.transitionTo('completed')

        def end(self):
            if self.timerB.active():
                self.timerB.cancel()

        def cancel(self):
            self.sendCancel()
            #not exactly timer B but it oughta ba
            self.timerB = reactor.callLater(64*T1, self.cancel)



        def timeout(self):
            if self.waitingToCancel:
                self.response = responseFromRequest(487, self.request)
            else:
                self.response = responseFromRequest(408, self.request)
            self.transitionTo('terminated')
            
    class completed(mode):

        def start(self):
            debug("ClientInvite %s transitioning to 'completed'" % (self.peer,))
            self.timerD = reactor.callLater(32, self.transitionTo,
                                            'terminated')

        def messageReceived(self, msg):
            if 300 <= msg.code:
                self.ack(msg)                

        def end(self):
            if self.timerD.active():
                self.timerD.cancel()

        def cancel(self):
            pass

    class terminated(mode):

        def start(self):
            debug("ClientInvite %s transitioning to 'terminated'" % (self.peer,))
            #XXX brutal
            for k, v in self.transport.clientTransactions.iteritems():
                if v == self:
                    del self.transport.clientTransactions[k]
                    break
            self.tu.clientTransactionTerminated(self)
            
        def messageReceived(self, msg):
            pass

        def end(self):
            raise RuntimeError, "can't unterminate a transaction"
        
        def cancel(self):
            pass
        


class ClientTransaction(object):
    __metaclass__ = ModalType
    initialMode = 'trying'
    modeAttribute = 'mode'
    def __init__(self, transport, tu, request, peerURL):
        self.tu = tu
        self.transport = transport
        self.request = request
        self.peer = peerURL
        self.response = None
        branch = computeBranch(request)
        self.transport.clientTransactions[branch] = self
        self.start()
        
    def transitionTo(self, stateName):
        self.end()
        self.mode = stateName
        self.start()

    def transportError(self, err):
        self.tu.transportError(self, err)
        self.transitionTo('terminated')

    def sendRequest(self):
        self.transport.sendRequest(self.request, self.peer)

    class trying(mode):

        def start(self):
            debug("Client %s transitioning to 'trying'" % (self.peer,))
            self.timerETries = 0
            def timerERetry():                
                self.timerETries += 1
                self.sendRequest()
                self.timerE = reactor.callLater(min((2**self.timerETries)*T1, T2),
                                  timerERetry)
            timerERetry()
            self.timerF = reactor.callLater(64*T1, self.transitionTo, 'terminated')
        
        def messageReceived(self, msg):
            if 200 <= msg.code:
                self.response = msg
                self.transitionTo('completed')
            else:
                self.transitionTo('proceeding')
            self.tu.responseReceived(msg, self)

        
        def end(self):
            if self.timerE.active():
                self.timerE.cancel()
            if self.timerF.active():
                self.timerF.cancel()
            
    class proceeding(mode):

        def start(self):
            debug("Client %s transitioning to 'proceeding'" % (self.peer,))
            self.timerETries = 0
            def timerERetry():                
                self.timerETries += 1
                self.sendRequest()
                reactor.callLater(T2, timerERetry)
            timerERetry()
            self.timerF = reactor.callLater(64*T1, self.transitionTo, 'terminated')
            
        def messageReceived(self, msg):                            
            if 200 <= msg.code:
                self.transitionTo('completed')
                self.response = msg
            self.tu.responseReceived(msg, self)
            
        def end(self):
            if self.timerE.active():
                self.timerE.cancel()
            if self.timerF.active():
                self.timerF.cancel()
            
    class completed(mode):

        def start(self):
            debug("Client %s transitioning to 'completed'" % (self.peer,))
            self.timerK = reactor.callLater(T4, self.transitionTo,
                                            'terminated')

        def messageReceived(self, msg):
            """
            The "Completed" state exists to buffer any additional response
            retransmissions that may be received (which is why the client
            transaction remains there only for unreliable transports).
            """
        def end(self):
            if self.timerK.active():
                self.timerK.cancel()
                

    class terminated(mode):
        def start(self):
            debug("Client %s transitioning to 'terminated'" % (self.peer,))
            #XXX brutal
            for k, v in self.transport.clientTransactions.iteritems():
                if v == self:
                    del self.transport.clientTransactions[k]
                    break
            self.tu.clientTransactionTerminated(self)

        def messageReceived(self, msg):
            pass

        def end(self):
            raise RuntimeError("can't unterminate a transaction")

class ServerInviteTransaction(object):
    __metaclass__ = ModalType
    initialMode = 'proceeding'
    modeAttribute = 'mode'
    
    def __init__(self, transport, tu, message, peerURL):
        self.message = message
        self.tu = tu
        self.transport = transport
        self.peer = peerURL
        self.lastResponse = None

    def sentFinalResponse(self):
        return self.lastResponse.code >= 200
    
    def transitionTo(self, stateName):
        self.end()
        self.mode = stateName
        self.start()

    def send100(self, msg):
        self.sendResponse(responseFromRequest(100, msg))

    def respond(self, msg):
        self.lastResponse = msg
        self.transport.sendResponse(msg)

    def repeatLastResponse(self):
        self.transport.sendResponse(self.lastResponse)

    class proceeding(mode):

        def start(self):
            debug("ServerInvite %s transitioning to 'proceeding'" % (self.peer,))

        def end(self):
            pass
        
        def messageReceived(self, msg):
            if msg.method == "INVITE":
                self.repeatLastResponse()
                
        def messageReceivedFromTU(self, msg):
            self.respond(msg)
            if 200 <= msg.code < 300:
                self.transitionTo('terminated')
            elif 300 <= msg.code < 700:
                self.transitionTo('completed')
    

    class completed(mode):

        def start(self):
            debug("ServerInvite %s transitioning to 'completed'" % (self.peer,))
            self.timerGTries = 1
            def timerGRetry():
                self.timerGTries +=1
                self.repeatLastResponse()
                self.timerG = reactor.callLater(min((2**self.timerGTries)*T1,
                                                    T2), timerGRetry)
            self.timerG = reactor.callLater(T1, timerGRetry)
            self.timerH = reactor.callLater(64*T1,
                                            self.transitionTo, 'terminated')


        def messageReceived(self, msg):
            if msg.method == "INVITE":
                self.repeatLastResponse()
            elif msg.method == "ACK":
                self.transitionTo('confirmed')

        def messageReceivedFromTU(self, msg):
            pass

        def end(self):
            if self.timerG.active():
                self.timerG.cancel()
            if self.timerH.active():
                self.timerH.cancel()


    class confirmed(mode):

        def start(self):
            debug("ServerInvite %s transitioning to 'confirmed'" % (self.peer,)) 
            self.timerI = reactor.callLater(T4, self.transitionTo,
                                            'terminated')

        def messageReceived(self, msg):
            pass

        def messageReceivedFromTU(self, msg):
            pass

        def end(self):
            pass
        

    class terminated(mode):

        def start(self):
            debug("ServerInvite %s transitioning to 'terminated'" % (self.peer,))
            self.transport.serverTransactionTerminated(self)
        
        def messageReceived(self, msg):
            pass

        def messageReceivedFromTU(self, msg):
            pass

        def end(self):
            pass
        


class ServerTransaction(object):
    __metaclass__ = ModalType
    initialMode = 'trying'
    modeAttribute = 'mode'

    def __init__(self, transport, tu, message, peerURL):
        self.message = message
        self.transport = transport
        self.tu = tu
        self.peer = peerURL
        self.lastResponse = None

    def transitionTo(self, stateName):
        self.end()
        self.mode = stateName
        self.start()

    def repeatLastResponse(self):
        self.transport.sendResponse(self.lastResponse)

    def respond(self, msg):
        self.lastResponse = msg
        self.transport.sendResponse(msg)

    class trying(mode):

        def start(self):
            debug("Server %s transitioning to 'trying'" % (self.peer,))

        def messageReceived(self, msg):
            pass

        def messageReceivedFromTU(self, msg):
            self.respond(msg)
            if 100 <= msg.code < 200:
                self.transitionTo('proceeding')
            else:
                self.transitionTo('completed')

        def end(self):
            pass        

    class proceeding(mode):

        def start(self):
            debug("Server %s transitioning to 'proceeding'" % (self.peer,))

        def messageReceived(self, msg):
            self.repeatLastResponse()
            
        def messageReceivedFromTU(self, msg):
            self.respond(msg)
            if 200 <= msg.code < 700:                
                self.transitionTo('completed')    


        def end(self):
            pass        

    class completed(mode):

        def start(self):
            debug("Server %s transitioning to 'completed'" % (self.peer,))
            self.timerJ = reactor.callLater(64*T1,
                                            self.transitionTo, 'terminated')

        def messageReceived(self, msg):
            self.repeatLastResponse()

        def messageReceivedFromTU(self, msg):
            pass

        def end(self):
            if self.timerJ.active():
                self.timerJ.cancel()


    class terminated(mode):

        def start(self):
            debug("Server %s transitioning to 'terminated'" % (self.peer,))
            self.transport.serverTransactionTerminated(self)
        
        def messageReceived(self, msg):
            pass

        def messageReceivedFromTU(self, msg):
            pass

        def end(self):
            pass
        

    
    
###############################################################################

class SIPTransport(protocol.DatagramProtocol):

    PORT = PORT
    debug = debuggingEnabled

    def __init__(self, tu, hosts, port):
        """tu: an implementor of ITransactionUser.
           hosts: A sequence of hostnames this element is
                  authoritative for. The first is used as the name for
                  outgoing messages. If empty, socket.getfqdn() is
                  used instead.                  
           port: The port this element listens on."""
        
        self.messages = []
        self.parser = MessagesParser(self.addMessage)
        self.tu = tu
        self.hosts = hosts or [socket.getfqdn()]
        self.host = self.hosts[0]
        self.port = port
        self.serverTransactions = {}
        self.clientTransactions = {}
        tu.start(self)
        
    def addMessage(self, msg):
        self.messages.append(msg)

    def datagramReceived(self, data, addr):
        try:
            self.parser.dataReceived(data)
            self.parser.dataDone()
            try:
                for m in self.messages:
                    if self.debug:
                        if isinstance(m, Request):
                            id = m.method
                        else:
                            id = m.code
                        debug("Received %r from %r." % (id, addr))
                    if isinstance(m, Request):
                        self._fixupNAT(m, addr)
                        self.handle_request(m, addr)
                    else:
                        self.handle_response(m, addr)
            finally:
                del self.messages[:]
        except Exception, e:
            log.err()
            if debuggingEnabled:
                raise
            else:
                self._badRequest(addr, e)
            
    def _badRequest(self, addr, e):
        #request parsing failed, we're going to have to make stuff up

        if isinstance(e, SIPError):
            code = e.code
        else:
            code = 500
        r = Response(code)

        r.addHeader("to", "%s:%s" % (addr))
        # see RFC3261 8.1.1.7, 16.6.8
        r.addHeader("via", Via(host=self.host, port=self.port, branch=VIA_COOKIE+ md5.new(repr(addr)).hexdigest()).toString())
        self.transport.write(r, addr)

    def _fixupNAT(self, message, (srcHost, srcPort)):
        # RFC 3581
        senderVia = parseViaHeader(message.headers["via"][0])
        senderVia.received = srcHost
        if senderVia.rport == True:
            senderVia.rport = srcPort
        message.headers["via"][0] = senderVia.toString()

    def handle_request(self, msg, addr):
        #RFC 3261 17.2.3
        via = parseViaHeader(msg.headers['via'][0])
        
        if not (via.branch and via.branch.startswith(VIA_COOKIE)):
            via.branch = computeBranch(msg)
        method = msg.method
        if method == "ACK":
            method = "INVITE"
        st = self.serverTransactions.get((via.branch, via.host,
                                          via.port, method))
        if st:
            st.messageReceived(msg)
        else:
            def addNewServerTransaction(st):
                if st:
                    self.serverTransactions[(via.branch, via.host,
                                             via.port, msg.method)] = st
            return defer.maybeDeferred(self.tu.requestReceived, msg, addr
                                       ).addCallback(addNewServerTransaction)
    

    def serverTransactionTerminated(self, st):
        #Brutal, but simple
        for k,v in self.serverTransactions.iteritems():
            if st == v:
                del self.serverTransactions[k]
                break


    def handle_response(self, msg, addr):
        #RFC 3261 18.1.2
        via = parseViaHeader(msg.headers['via'][0])
        if not (via.host in self.hosts and via.port == self.port):
            #drop silently
            return
        
        #RFC 3261 17.1.3
        ct = self.clientTransactions.get(via.branch)        
        if ct and msg.headers['cseq'][0].split(' ')[1] == ct.request.headers['cseq'][0].split(' ')[1]:
            ct.messageReceived(msg)
        else:
            self.tu.responseReceived(msg)

    
    def sendRequest(self, msg, target):
        """Add a Via header to this message and send it to the (host,
        port) target."""
        
        #CANCEL & ACK requires the same Via branch as the thing it is
        #cancelling/acking so it has to be added by the txn            
        if msg.method not in ("ACK", "CANCEL"):
            #raaaaa this is so we don't add the same via header on resends
            msg = msg.copy()
            if msg.headers.get('via'):
                msg.headers['via'] = msg.headers['via'][:]
            #RFC 3261 18.1.1
            #RFC 3581 3            
            msg.headers.setdefault('via', []).insert(0, Via(self.host, self.port,
                                            rport=True,
                                            branch=computeBranch(msg)).toString())
        txt = msg.toString()
        if len(txt) > 1300:
            raise NotImplementedError, "Message too big for UDP. You're boned."
        debug("Sending %r to %r" % (msg.method, target))
        self._resolveA(target[0]).addCallback(
            lambda ip: self.sendMessage(msg, (ip, (target[1] or self.PORT))))
        
    
    def sendResponse(self, msg):
        """Determine the target for the response and send it."""
        
        #RFC 3261 18.2.2
        #RFC 3581 4
        via = parseViaHeader(msg.headers['via'][0])
        host = via.received or via.host
        port = via.rport or via.port or self.PORT
        
        debug("Sending %r to %r" % (msg.code, (host, port)))
        self._resolveA(host).addCallback(
            lambda ip: self.sendMessage(msg, (ip, port)))

    def sendMessage(self, msg, (host, port)):
        #for easier testing
        self.transport.write(msg.toString(), (host, port))

    def _resolveA(self, addr):
            return reactor.resolve(addr)


class ITransactionUser(Interface):
    def start(transport):
        """Connects the transport to the TU."""

    def requestReceived(msg, addr):
        """Processes a message, after the transport and transaction
        layer are finished with it. May return a ServerTransaction (or
        ServerInviteTransaction), which will handle subsequent
        messages from that SIP transaction."""

    def responseReceived(msg, ct=None):
        """Processes a response received from the transport, along
        with the client transaction it is a part of, if any."""


    def clientTransactionTerminated(ct):
        """Called when a client transaction created by this TU
        transitions to the 'terminated' state."""
        
#from resiprocate's proxy
responsePriorities = {                  428: 24, 429: 24, 494: 24, 
    412: 1,                             413: 25, 414: 25, 
    484: 2,                             421: 26, 
    422: 3, 423: 3,                     486: 30, 
    407: 4, 401: 4,                     480: 31, 
    402: 6,                             410: 32,                       
    493: 10,                            436: 33, 437: 33, 
    420: 12,                            403: 32, 
    406: 13, 415: 13, 488: 13,          404: 35, 
    416: 20, 417: 20,                   487: 36, 
    405: 21, 501: 21,                   503: 40, 
    580: 22,                            483: 41, 482: 41, 
    485: 23,                            408: 49} 
                                        

class Proxy:
    implements(ITransactionUser)

    def __init__(self, portal):
        self.portal = portal
        self.sessions = {}
        self.responseContexts = {}
        self.finalResponses = {}
        self.registrar = Registrar(portal)

    def start(self, transport):
        self.transport = transport
        self.registrar.start(transport)
        self.recordroute = URL(host=transport.host,
                               port=transport.port, other={'lr':''})

    def requestReceived(self, msg, addr):
        #RFC 3261 16.4
        if msg.uri == self.recordroute:
            msg.uri = msg.headers['route'].pop()
            
        if msg.headers.get('route',None):
            route = parseAddress(msg.headers['route'][0])[1]
            if (route.host in self.transport.hosts and
                (route.port or PORT) == self.transport.port):
                del msg.headers['route'][0]

        #RFC 3261 16.5
        if msg.uri.host in self.transport.hosts: 
            if msg.method == 'REGISTER':
                return self.registrar.requestReceived(msg, addr)
            elif msg.method == 'OPTIONS' and msg.uri.username is None:
                st = ServerTransaction(self.transport, self, msg, addr)
                st.messageReceivedFromTU(responseFromRequest(200, msg))
                return st

                
        def _cb(x, st):
            return self.findTargets(msg.uri).addCallback(
                self.forwardRequest, msg, st)
            
        def _eb(err):
            if err.check(SIPError):
                errcode = err.value.code
                err = None
            else:
                if debuggingEnabled:
                    import pdb; pdb.set_trace()
                errcode = 500
                log.err(err)
            st.messageReceivedFromTU(
                responseFromRequest(errcode, msg))
            
        if msg.method == 'INVITE':            
            st = ServerInviteTransaction(self.transport, self, msg, addr)
            st.messageReceivedFromTU(responseFromRequest(100, msg))
            return self.checkInviteAuthorization(msg).addCallback(
                _cb, st).addErrback(_eb).addCallback(
                lambda _: st)
        elif msg.method == 'CANCEL':
            via = parseViaHeader(msg.headers['via'][0])
            self.transport.sendResponse(responseFromRequest(200, msg))
            #RFC 3261 9.2
            for k, t in self.transport.serverTransactions.iteritems():
                if (isinstance(t, (ServerTransaction,ServerInviteTransaction))
                    and (via.branch, via.host, via.port) == k[:3]):
                    self.cancelPendingClients(t)
                    break
            else:
                self.proxyRequestStatelessly(msg)        
                return None
        elif msg.method == 'ACK':
            msg.headers['via'].insert(0,Via(self.transport.host, self.transport.port,
                                            rport=True,
                                            branch=computeBranch(msg)).toString())
            self.proxyRequestStatelessly(msg)
            return None
        else:
            st = ServerTransaction(self.transport, self, msg, addr)
            _cb(None, st)
            
            if msg.method == 'BYE':
                self.untrackSession(msg)
            return st
        
    def proxyRequestStatelessly(self, originalMsg):        
        def _cb(addrs):
            msg, addr = self.processRouting(originalMsg, addrs[0])
            self.transport.sendRequest(msg, (addr.host, addr.port))
        self.findTargets(originalMsg.uri).addCallback(_cb)

    def findTargets(self, addr):
        d = self.portal.login(Preauthenticated(addr.toCredString()),
                              None, IContact)

        def lookedUpSuccessful((ifac, contact, logout)):
            return defer.maybeDeferred(contact.getRegistrationInfo
                                       ).addCallback(
                lambda x: [i[0] for i in x])        
        def failedLookup(err):
            e = err.trap(NoSuchUser, UnauthorizedLogin)
            if e == UnauthorizedLogin:
                return [addr]
            elif e == NoSuchUser:
                raise SIPLookupError(604)
        return d.addCallback(lookedUpSuccessful).addErrback(failedLookup)
        
    def forwardRequest(self, targets, originalMsg, st):
        fs = []
        if len(targets) == 0:
            raise SIPLookupError(480)
        for addr in targets:
            msg, addr = self.processRouting(originalMsg, addr)
            
            fs.append(self._lookupURI(addr).addCallback(self._forward,msg, st))
        return defer.DeferredList(fs)

    def processRouting(self, originalMsg, addr):
        #16.6
        msg = originalMsg.copy()
        msg.uri = addr
        if msg.headers.get('max-forwards'):                
            msg.headers['max-forwards'][0] = str(int(
                msg.headers['max-forwards'][0]) - 1)
        else:
            msg.headers['max-forwards'] = ['70']
        msg.headers.setdefault('record-route',
                               []).insert(0, self.recordroute.toString())
        if msg.headers.get('route', None):
            if 'lr' not in parseAddress(msg.headers['route'][0])[1].other:
                #more coping with strict routers
                msg.headers['route'].append(msg.uri.toString())
                msg.uri = parseAddress(msg.headers['route'].pop())[1]
            else:
                addr = parseAddress(msg.headers['route'][0])[1]
        return msg, addr
    
    def _forward(self, addresses, msg, st):
        for address in addresses:
            #16.6.8
            if msg.method == 'INVITE':
                ct = ClientInviteTransaction(self.transport,
                                             self, msg, address)
                timerC = reactor.callLater(181, ct.timeout)
            else:
                ct = ClientTransaction(self.transport, self, msg, address)
                timerC=None

            self.responseContexts[ct] = (st, timerC)
            self.responseContexts.setdefault(st, []).append(ct)
    def _lookupURI(self, userURI):
        """Leave this method: it is hooked by the tests.
        """
        #RFC 3263 4.2
        if abstract.isIPAddress(userURI.host):
            # it is an IP not a hostname
            if not userURI.port:
                userURI.port = 5060
            return defer.succeed([(userURI.host, userURI.port)])
        else:
            if userURI.port is not None:
                return defer.succeed([(userURI.host, userURI.port)])
            d = client.lookupService('_sip._udp.' + userURI.host)
            d.addCallback(self._resolveSRV, userURI)
            return d

    def _resolveSRV(self, (answers, _, __), userURI):

        if answers:
            answers = [(a.payload.priority, str(a.payload.target), a.payload.port) for a in answers]
            answers.sort()
            return [(answer[1], answer[2]) for answer in answers]
        else:
            #just do an A lookup
            return [(userURI.host, 5060)]
    
    def checkInviteAuthorization(self, message):
        name, uri, tags = parseAddress(message.headers["to"][0], clean=1)
        fromname, fromuri, ignoredTags = parseAddress(message.headers["from"][0], clean=1)
        somebodyWasAuthorized = []
        def recordIt(oururi, theiruri, method, *extra):            
            #XXX XXX totally need to check to see if the invite is
            #from a registered address
            d = self.portal.login(Preauthenticated('%s@%s' % (oururi.username, oururi.host)), None, IContact)
            def success((iface, contact, logout), theiruri=theiruri, method=method):
                somebodyWasAuthorized.append(contact)
                getattr(contact,method)(name, theiruri, *extra)
                return contact
            def ignoreUnauthorized(failure):
                failure.trap(UnauthorizedLogin)
                return None

            return d.addCallbacks(success, ignoreUnauthorized)

        # this is a somewhat, uh, "compact" (some would say
        # obfuscated) representation of a series of unfortunate
        # events, so here is some prose to guide you through it:

        # First, we tell the caller (if they're registered with us) that
        # they're making a call, to give them the opportunity to record it on
        # the server.  they don't yet know whether their callee is registered
        # or not, and in fact it doesn't matter to them (they _made_ the call
        # without such information, after all).  A caller can potentially
        # cancel the call at this point by raising an exception but I can't
        # think of a reason to do that which isn't an error.

        # then, we tell the callee (if they're registered with us) that they're
        # receiving a call.  At this point, they may *decline* the call by
        # raising a SIPError of some kind in callIncoming.  This is the way
        # you'll implement call screening.  ( TODO: You *also* ought to be able
        # to implement a redirect on an incoming call by raising an appropriate
        # SIPError, but there is not currently a way to get the URL for the
        # redirect all the way back up the call chain. )

        # Before we relay this to the rest of the SIP logic, we make sure that
        # at least ONE of the participants was authorized to make or receive
        # this call through this server.  We don't want to proxy arbitrary
        # third-party INVITE requests.

        def makeSureSomebodyWasAuthorized(value):
            if not somebodyWasAuthorized:
                raise SIPError(401)
            return value

        return recordIt(fromuri, uri, 'callOutgoing').addCallback(
            lambda caller:
            recordIt(uri, fromuri, 'callIncoming', caller)
            ).addCallback(makeSureSomebodyWasAuthorized)


    def clientTransactionTerminated(self, ct):
        st = self.responseContexts[ct]
        #XXX kluge?
        if not isinstance(st, ServerTransaction):
            st, timerC = st
        else:
            timerC = None
        cts = self.responseContexts[st]
        for ct in cts:
            if ct.mode != "terminated":
                break
        else:

            if not self.finalResponses.get(st, None):
                response = self.chooseFinalResponse(st)
                self.finalResponses[st] = response
                st.messageReceivedFromTU(response)
            del self.responseContexts[st]
            if timerC: timerC.cancel()
            for ct in cts:
                del self.responseContexts[ct]


            
    def chooseFinalResponse(self, st):
        cts = self.responseContexts[st]
        noResponses = True
        responses = [(ct.response and ct.response.code, ct) for ct in cts]
        for code, ct in responses:
            if code is not None and code >= 200:
                noResponses = False
                break
        assert not noResponses, "BROKEN. chooseFinalResponse was called before any final responses occurred." 

        prioritizedResponses = []
        for code, ct in responses:
            prio = responsePriorities.get(code, None)
            if prio:
                prioritizedResponses.append((prio, ct.response))
            elif 300 <= code < 400:
                prioritizedResponses.append((5, ct.response))
            elif 500 <= code < 600:
                prioritizedResponses.append((42, ct.response))
            else:
                prioritizedResponses.append((43, ct.response))
        prioritizedResponses.sort()
        finalResponse = prioritizedResponses[0][1]

        #XXX need to process 3xx messages ourselves
        #instead of forwarding them
        if 300 <= finalResponse.code < 400:
            for code, ct in responses:
                if 300 <= code < 400:
                    finalResponse.headers['contact'].extend(
                        ct.response.headers['contact'])
            finalResponse.code = 300

        elif finalResponse.code in (401, 407):
            #RFC 3261 16.7.7                
            authHeaders = {}
            for code, ct in responses:
                if code == 401:
                    finalResponse.headers['www-authenticate'].extend(
                        r.headers.get("www-authenticate", []))


                elif code == 407:
                    finalResponse.headers['proxy-authenticate'].extend(
                        r.headers.get("proxy-authenticate",[]))
                    finalResponse.code = 407
        return finalResponse


            
    def responseReceived(self, msg, ct=None):
        #RFC 3261 16.7
        if msg.code == 100:
            return
        via = msg.headers['via'][0]
        msg.headers['via'] = msg.headers['via'][1:]
        
        if len(msg.headers['via']) == 0:
            if not msg.headers['cseq'][0].endswith('CANCEL'):
                #ignore CANCEL/200s, process the rest
                self.processLocalResponse(msg, ct)
            return
        if (not ct and msg.headers['cseq'][0].endswith('INVITE')
            and 200 <= msg.code < 300): 
            self.transport.sendResponse(msg)
            return
        else:
            st, timerC = self.responseContexts.get(ct, (None, None))
            if not st:
                #staaaaateless
                self.transport.sendResponse(msg)

        if 100 < msg.code < 200:
            if isinstance(ct, ClientInviteTransaction):
                timerC.reset(181)
            st.messageReceivedFromTU(msg)
            return
        
        #TODO: Catch 3xx responses, add their redirects to the target set
        if 200 <= msg.code < 300:
            self.finalResponses[st] = msg
            reactor.callLater(0, self.cancelPendingClients, st)
            if isinstance(ct, ClientInviteTransaction):
                self.trackSession(msg)
        elif 600 <= msg.code:
            self.cancelPendingClients(st)            
        else:
            #might as well leave the message there, sans our via header
            ct.response = msg
        
        st.messageReceivedFromTU(msg)
        
    def processLocalResponse(self, msg, ct):
        if getattr(self.originator, None):
            self.originator.responseReceived(msg, ct)
                    
    def cancelPendingClients(self, st):
        if isinstance(st, ServerInviteTransaction):
            cts = self.responseContexts.get(st, [])
            for ct in cts:
                ct.cancel()

    def trackSession(self, msg):
        pass

    def untrackSession(self, msg):
        pass

    
class Registrar:
    authorizers = {
        'digest': DigestAuthorizer(),
        }
    def __init__(self, portal):
        self.portal = portal

    def start(self, transport):
        self.transport = transport
        
    def getRegistrationInfo(self, url):
        #XXX Need to think about impact of all these cred lookups in a
        #cluster environment
        def _cbRegInfo((i,a,l)):
            return a.getRegistrationInfo()
        def _ebRegInfo(failure):
            failure.trap(UnauthorizedLogin)
            return None        
        return self.portal.login(Preauthenticated('%s@%s' % (url.username,
                                                            url.host)),
                                 None, IContact).addCallback(
            _cbRegInfo).addErrback(
            _ebRegInfo)

    
    def requestReceived(self, msg, addr):
        st = ServerTransaction(self.transport, self, msg, addr)
        if msg.method == "REGISTER":
            self.registrate(msg, addr).addCallback(st.messageReceivedFromTU)
        else:
            st.messageReceivedFromTU(responseFromRequest(501, msg))
        return st
            
    def registrate(self, message, addr):
        name, toURL, params = parseAddress(message.headers["to"][0], clean=1)
        if not message.headers.has_key("authorization"):
            creds = credentials.UsernamePassword(toURL.toCredString(),'')
        else:
            parts = message.headers['authorization'][0].split(None, 1)
            a = self.authorizers.get(parts[0].lower())
            if a:
                creds = a.decode(parts[1])                
                # IGNORE the authorization username - take that, SIP
                # configuration UIs!!!                
                creds.username = toURL.toCredString()

        return self.portal.login(creds, None, IContact
            ).addCallback(self._cbLogin, message, addr
            ).addErrback(self._ebLogin, message, addr)

    def _cbLogin(self, (i, a, l), message, addr):
        return self.register(a, message, addr)

    def _ebLogin(self, failure, message, addr):
        failure.trap(UnauthorizedLogin)
        return self.unauthorized(message, addr)

    def register(self, avatar, message, addr):
        def _cbRegister(regdata, message):
            response = responseFromRequest(200, message)            
            #for old times' sake I will send a separate Expires header
            #if there is only one contact            
            if len(regdata) == 1:
                contactURL, expiry = regdata[0]
                response.addHeader("contact", contactURL.toString())
                response.addHeader("expires", str(expiry))
            else:
                for contactURL, expiry in regdata:
                    response.addHeader("contact", "%s;expires=%s" %
                                       (contactURL.toString(), expiry))
            response.addHeader("content-length", "0")
            return response

        def _cbUnregister(regdata, message):

            msg = responseFromRequest(200, message)
            #More backwards combatibility
            if len(regdata) == 1:
                contactURL, expiry = regdata[0]
                msg.addHeader("contact", contactURL.toString())
                msg.addHeader("expires", "0")
            else:
                for contactURL, expiry in regdata:
                    msg.addHeader("contact", "%s;expires=%s" %
                                  (contactURL.toString(), 0))
            return msg

        def _ebUnregister(registration, message):
            pass

        name, toURL, params = parseAddress(message.headers["to"][0], clean=1)
        contact = None
        if message.headers.has_key("contact"):
            contact = message.headers["contact"][0]

        expires = message.headers.get("expires", [None])[0]
        if expires == "0":
            if contact == "*":
                return defer.maybeDeferred(avatar.unregisterAllAddresses).addCallback(
                    _cbUnregister, message
                    ).addErrback(_ebUnregister, message)
            else:
                name, contactURL, params = parseAddress(contact) #host=addr.host, port=addr.port)
                return defer.maybeDeferred(avatar.unregisterAddress,
                                    contactURL).addCallback(
                    _cbUnregister, message).addErrback(
                    _ebUnregister, message)
        else:
            name, contactURL, params = parseAddress(contact)# host=addr.host, port=addr.port)
            if contact is not None:
                if expires:
                    expiresInt = int(expires)
                else:
                    expiresInt = DEFAULT_REGISTRATION_LIFETIME
                d = defer.maybeDeferred(avatar.registerAddress,
                                        contactURL, expiresInt)
            else:
                d = defer.maybeDeferred(avatar.getRegistrationInfo)
            d.addCallback(_cbRegister, message).addErrback(self._ebLogin,
                                                           message, addr)
            return d

    def unauthorized(self, message, addr):
        # log.msg("Failed registration attempt for %s from %s" %
        # (message.headers.get('from'), message.headers.get('contact')))
        m = responseFromRequest(401, message)
        for (scheme, auth) in self.authorizers.iteritems():
            chal = auth.getChallenge(addr)
            if chal is None:
                value = '%s realm="%s"' % (scheme.title(), self.transport.host)
            else:
                value = '%s %s,realm="%s"' % (scheme.title(), chal,
                                              self.transport.host)
            m.headers.setdefault('www-authenticate', []).append(value)
        return m

    


class Originator:

    def start(self, transport):
        self.transport = transport

    def originate(self, fromURL, toURL):        
        # Call fromURL, wait for pickup, then call toURL and connect
        # them (reinvite?)
        pass
