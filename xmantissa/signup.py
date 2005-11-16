
import os, rfc822

from zope.interface import Interface, implements

from twisted.cred.portal import IRealm

from twisted.mail import smtp, relaymanager
from twisted.python.util import sibpath
from twisted.python import log

from axiom.item import Item, transacted
from axiom.attributes import integer, reference, text, AND
from axiom.iaxiom import IBeneficiary

from nevow.rend import Page
from nevow.url import URL
from nevow.inevow import IResource, ISession

from xmantissa.ixmantissa import ISiteRootPlugin, IStaticShellContent
from xmantissa.website import PrefixURLMixin
from xmantissa.publicresource import PublicAthenaLivePage, getLoader

_theMX = None
def getMX():
    """
    Retrieve the single MXCalculator instance, creating it first if
    necessary.
    """
    global _theMX
    if _theMX is None:
        _theMX = relaymanager.MXCalculator()
    return _theMX


class TicketClaimer(Page):
    def childFactory(self, ctx, name):
        for T in self.original.store.query(
            Ticket,
            AND(Ticket.booth == self.original,
                Ticket.nonce == unicode(name, 'ascii'))):
            something = T.claim()
            res = IResource(something)
            lgo = getattr(res, 'logout', lambda : None)
            ISession(ctx).setDefaultResource(res, lgo)
            return URL.fromContext(ctx).click("/private")
        return None


class TicketBooth(Item, PrefixURLMixin):
    implements(ISiteRootPlugin)

    typeName = 'ticket_powerup'
    schemaVersion = 1

    sessioned = True

    claimedTicketCount = integer(default=0)
    createdTicketCount = integer(default=0)

    defaultTicketEmail = text(default=None)

    prefixURL = 'ticket'

    def createResource(self):
        return TicketClaimer(self)

    def createTicket(self, issuer, email, benefactor):
        t = self.store.findOrCreate(
            Ticket,
            benefactor=benefactor,
            booth=self,
            avatar=None,
            issuer=issuer,
            email=email)
        return t

    createTicket = transacted(createTicket)

    def ticketClaimed(self, ticket):
        self.claimedTicketCount += 1

    def ticketLink(self, domainName, httpPortNumber, nonce):
        httpPort = ''
        httpScheme = 'http'

        if httpPortNumber == 443:
            httpScheme = 'https'
        elif httpPortNumber != 80:
            httpPort = ':' + str(httpPortNumber)

        return '%s://%s%s/%s/%s' % (
            httpScheme, domainName, httpPort, self.prefixURL, nonce)

    def issueViaEmail(self, issuer, email, benefactor,
                      domainName, httpPort=80, templateFileObj=None):
        """
        Send a ticket via email to the supplied address, which, when claimed, will
        create an avatar and allow the given benefactor to endow it with
        things.

        @param issuer: An object, preferably a user, to track who issued this
        ticket.

        @param email: a str, formatted as an rfc2821 email address
        (user@domain) -- source routes not allowed.

        @param benefactor: an implementor of ixmantissa.IBenefactor

        @param domainName: a domain name, used as the domain part of the
        sender's address, and as the web server to generate a link to within
        the email.

        @param httpPort: a port number for the web server running on domainName

        @param templateFileObj: Optional, but suggested: an object with a
        read() method that returns a string containing an rfc2822-format email
        message, which will have several python values interpolated into it
        dictwise:

            %(from)s: To be used for the From: header; will contain an
             rfc2822-format address.

            %(to)s: the address that we are going to send to.

            %(date)s: an rfc2822-format date.

            %(message-id)s: an rfc2822 message-id

            %(link)s: an HTTP URL that we are generating a link to.

        """

        if templateFileObj is None:
            if self.defaultTicketEmail is None:
                templateFileObj = file(sibpath(__file__, 'signup.rfc2822'))
            else:
                templateFileObj = file(self.defaultTicketEmail)

        ticket = self.createTicket(issuer,
                                   unicode(email, 'ascii'),
                                   benefactor)
        nonce = ticket.nonce

        signupInfo = {'from': 'signup@'+domainName,
                      'to': email,
                      'date': rfc822.formatdate(),
                      'message-id': smtp.messageid(),
                      'link': self.ticketLink(domainName, httpPort, nonce)}

        msg = templateFileObj.read() % signupInfo
        templateFileObj.close()

        def gotMX(mx):
            return smtp.sendmail(str(mx.name),
                                 signupInfo['from'],
                                 [email],
                                 msg)

        mxc = getMX()
        return ticket, mxc.getMX(email.split('@', 1)[1]).addCallback(gotMX)


def _generateNonce():
    return unicode(os.urandom(16).encode('hex'), 'ascii')

class ITicketIssuer(Interface):
    def issueTicket(emailAddress):
        pass

class FreeTicketSignup(Item, PrefixURLMixin):
    implements(ISiteRootPlugin)

    typeName = 'free_signup'
    schemaVersion = 1

    sessioned = True

    prefixURL = text()
    booth = reference()
    benefactor = reference()

    def createResource(self):
        return PublicAthenaLivePage(
            ITicketIssuer, self,
            getLoader("signup"),
            IStaticShellContent(self.store, None),
            None)

    def issueTicket(self, url, emailAddress):
        domain, port = url.get('hostname'), int(url.get('port') or 80)
        if os.environ.get('CC_DEV'):
            ticket = self.booth.createTicket(self, emailAddress, self.benefactor)
            return '<a href="%s">Claim Your Account</a>' % (
                    self.booth.ticketLink(domain, port, ticket.nonce),)
        else:
            ticket, issueDeferred = self.booth.issueViaEmail(
                self,
                emailAddress.encode('ascii'), # heh
                self.benefactor,
                domain,
                port)

            issueDeferred.addCallback(
                lambda result: u'Please check your email for a ticket!')

            return issueDeferred

class Ticket(Item):
    schemaVersion = 1
    typeName = 'ticket'

    issuer = reference(allowNone=False)
    booth = reference(allowNone=False)
    avatar = reference()
    claimed = integer(default=0)
    benefactor = reference(allowNone=False)

    email = text()
    nonce = text()

    def __init__(self, **kw):
        super(Ticket, self).__init__(**kw)
        self.booth.createdTicketCount += 1
        self.nonce = _generateNonce()

    def claim(self):
        if not self.claimed:
            log.msg("Claiming a ticket for the first time for %r" % (self.email,))
            username, domain = self.email.split('@', 1)
            realm = IRealm(self.store)
            acct = realm.accountByAddress(username, domain)
            if acct is None:
                acct = realm.addAccount(username, domain, None)
            self.avatar = acct
            self.claimed += 1
            self.booth.ticketClaimed(self)
            self.benefactor.endow(self, IBeneficiary(self.avatar))
        else:
            log.msg("Ignoring re-claim of ticket for: %r" % (self.email,))
        return self.avatar
    claim = transacted(claim)
