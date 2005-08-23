
from zope.interface import implements

from twisted.cred.portal import IRealm

from twisted.mail import smtp, relaymanager

from axiom.item import Item, transacted
from axiom.attributes import integer, reference, text, AND
from axiom.iaxiom import IBeneficiary

from nevow.rend import Page, NotFound
from nevow.url import URL
from nevow.livepage import LivePage, glue, set
from nevow.inevow import IResource, ISession
from nevow.flat.ten import flatten
from nevow import tags as t

from xmantissa.ixmantissa import ISiteRootPlugin

from xmantissa.website import PrefixURLMixin

from xmantissa.webtheme import getAllThemes

import os

class TicketClaimer(Page):
    def childFactory(self, ctx, name):
        for T in self.original.store.query(
            Ticket,
            AND(Ticket.booth == self.original,
                Ticket.nonce == unicode(name, 'ascii'))):
            res = IResource(T.claim())
            lgo = getattr(res, 'logout', lambda : None)
            ISession(ctx).setDefaultResource(res, lgo)
            break
        else:
            return NotFound


class TicketBooth(Item, PrefixURLMixin):
    implements(ISiteRootPlugin)

    typeName = 'ticket_powerup'
    schemaVersion = 1

    claimedTicketCount = integer(default=0)

    createdTicketCount = integer(default=0)

    prefixURL = 'ticket'

    def createResource(self):
        return TicketClaimer(self)

    def _generateNonce(self):
        return unicode(os.urandom(16).encode('hex'), 'ascii')

    def createTicket(self, issuer, email, benefactor):
        t = Ticket(store=self.store,
                   benefactor=benefactor,
                   booth=self,
                   avatar=None,
                   issuer=issuer,
                   email=email,
                   nonce=self._generateNonce())
        self.createdTicketCount += 1
        return t

    createTicket = transacted(createTicket)

    def ticketClaimed(self, ticket):
        self.claimedTicketCount += 1


def getLoader(n):
    # TODO: implement PublicApplication (?) in webapp.py, so we can make sure
    # that these go in the right order.  Right now we've only got the one
    # though.
    for t in getAllThemes():
        fact = t.getDocFactory(n, None)
        if fact is not None:
            return fact

    raise RuntimeError("No loader for %r anywhere" % (n,))

class FreeSignerUpper(LivePage):
    def __init__(self, original):
        Page.__init__(self, original, docFactory = getLoader('shell'))

    def render_title(self, ctx, data):
        return "Sign Up"

    def handle_issueTicket(self, ctx, emailAddress):
        def hooray(whatever):
            return set('signup-status',
                       flatten([
                        'Check your email, or ',
                        t.a(href=uuu)
                        ['click here.']]))
        def ono(err):
            return set(
                'signup-status',
                flatten('That did not work: ' + err.getErrorMessage()))
        emailAddress = unicode(emailAddress, 'ascii')

        nonce = self.original.booth.createTicket(
            self.original,
            emailAddress,
            self.original.benefactor).nonce

        uuu = '/'+self.original.booth.prefixURL+'/'+nonce

        msg = (
            "Subject: WElcome,.",
            "To: %s",
            "Date: Now",
            "Content-Type: text/html",
            "",
            "Hi.  Click on this link,.: <a href='%s'>now.</a>")

        msg = '\r\n'.join(msg) % (
            emailAddress, flatten(URL.fromContext(ctx).click(uuu)))

        def gotMX(mx):
            return smtp.sendmail(str(mx.name), 'signup@internet.host', [emailAddress], msg)
        mxc = relaymanager.MXCalculator()
        return mxc.getMX(emailAddress.split('@', 1)[1]).addCallback(gotMX).addCallbacks(hooray, ono)

    def render_content(self, ctx, data):
        return getLoader('signup').load()

    def render_head(self, ctx, data):
        return glue

    def render_navigation(self, ctx, data):
        return ''


class FreeTicketSignup(Item, PrefixURLMixin):
    implements(ISiteRootPlugin)

    typeName = 'free_signup'
    schemaVersion = 1

    prefixURL = text()
    booth = reference()
    benefactor = reference()

    issuedTicketCount = integer(default=0)

    claimedTicketCount = integer(default=0)

    def ticketClaimed(self, ticket):
        self.claimedTicketCount += 1

    def createResource(self):
        return FreeSignerUpper(self)


class Ticket(Item):
    schemaVersion = 1
    typeName = 'ticket'

    issuer = reference()
    booth = reference()
    avatar = reference()
    claimed = integer(default=0)
    benefactor = reference()

    email = text()
    nonce = text()

    def claim(self):
        if not self.claimed:
            username, domain = self.email.split('@', 1)
            realm = IRealm(self.store)
            acct = realm.accountByAddress(username, domain)
            if acct is None:
                acct = realm.addAccount(username, domain, None)
            self.avatar = acct
            self.claimed += 1
            self.issuer.ticketClaimed(self)
            self.booth.ticketClaimed(self)
            self.benefactor.endow(IBeneficiary(self.avatar))
        return self.avatar
    claim = transacted(claim)
