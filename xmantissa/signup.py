# -*- test-case-name: xmantissa.test.test_signup -*-

import os, rfc822, md5, time, random

from zope.interface import Interface, implements

from twisted.cred.portal import IRealm
from twisted.python.components import registerAdapter
from twisted.mail import smtp, relaymanager
from twisted.python.util import sibpath
from twisted.python import log, reflect
from twisted import plugin

from epsilon import extime

from axiom.item import Item, InstallableMixin, transacted, declareLegacyItem
from axiom.attributes import integer, reference, text, timestamp, inmemory, AND
from axiom.iaxiom import IBeneficiary
from axiom import userbase, upgrade

from nevow.rend import Page, NotFound
from nevow.url import URL
from nevow.inevow import IResource, ISession
from nevow import inevow, tags, athena, loaders

from xmantissa.ixmantissa import (
    IBenefactor, ISiteRootPlugin, IStaticShellContent, INavigableElement,
    INavigableFragment, ISignupMechanism)
from xmantissa.website import PrefixURLMixin, WebSite
from xmantissa.publicresource import PublicAthenaLivePage, PublicPage, getLoader
from xmantissa.webnav import Tab
from xmantissa.webapp import PrivateApplication
from xmantissa.offering import getInstalledOfferings
from xmantissa import plugins, liveform
from xmantissa.websession import PersistentSession

class PasswordResetResource(Page):
    """
    I handle the user-facing parts of password reset -
    the web form junk and sending of emails
    """

    attempt = None

    def __init__(self, original):
        Page.__init__(self, original, docFactory=getLoader('reset'))

    def locateChild(self, ctx, segments):
        if len(segments) == 1:
            attempt = self.original.attemptByKey(unicode(segments[0]))
            if attempt is not None:
                self.attempt = attempt
                return (self, ())
        return NotFound

    def renderHTTP(self, ctx):
        req = inevow.IRequest(ctx)

        if req.method == 'POST':
            if 'username' in req.args:
                (user,) = req.args['username']

                att = self.original.newAttemptForUser(unicode(user))
                if self.original.accountByAddress(user) is not None:
                    self._sendEmail(ctx, att)
                else:
                    # do we want to disclose this to the user?
                    pass
                self.docFactory = loaders.stan(tags.h1['Check your email'])
            else:
                (password,) = req.args['password1']
                self.original.resetPassword(self.attempt, unicode(password))
                self.docFactory = loaders.stan(tags.h1['Password reset, you can now ',
                                                       tags.a(href='/login')['Login']])
        elif self.attempt:
            self.docFactory = getLoader('reset-step-two')

        return Page.renderHTTP(self, ctx)

    def _sendEmail(self, ctx, attempt):
        url = URL.fromContext(ctx)
        netloc = url.netloc.split(':')
        host = netloc.pop(0)
        if netloc:
            (port,) = netloc
        else:
            port = 80

        body = file(sibpath(__file__, 'reset.rfc2822')).read()
        body %= {'from': 'reset@' + host,
                 'to': attempt.username,
                 'date': rfc822.formatdate(),
                 'message-id': smtp.messageid(),
                 'link': 'http://%s:%s/%s/%s' % (host, port, self.prefixURL, attempt.key)}

        _sendEmail('reset@' + host, attempt.username, body)

class _PasswordResetAttempt(Item):
    """
    I represent as as-yet incomplete attempt at password reset
    """

    typeName = 'password_reset_attempt'
    schemaVersion = 1

    key = text()
    username = text()
    timestamp = timestamp()

class PasswordReset(Item, PrefixURLMixin):
    typeName = 'password_reset'
    schemaVersion = 1

    sessioned = False
    sessionless = True

    prefixURL = 'reset-password'
    installedOn = reference()
    loginSystem = inmemory()

    def activate(self):
        self.loginSystem = self.store.findUnique(userbase.LoginSystem, default=None)

    def createResource(self):
        return PasswordResetResource(self)

    def attemptByKey(self, key):
        """
        Locate the L{_PasswordResetAttempt} that corresponds to C{key}
        """

        return self.store.findUnique(_PasswordResetAttempt,
                                     _PasswordResetAttempt.key == key,
                                     default=None)

    def _makeKey(self, usern):
        return unicode(md5.new(str((usern, time.time(), random.random()))).hexdigest())

    def newAttemptForUser(self, user):
        """
        Create an L{_PasswordResetAttempt} for the user whose username is C{user}
        @param user: C{unicode} username
        """
        # we could query for other attempts by the same
        # user within some timeframe and raise an exception,
        # if we wanted
        return _PasswordResetAttempt(store=self.store,
                                     username=user,
                                     timestamp=extime.Time(),
                                     key=self._makeKey(user))

    def accountByAddress(self, username):
        """
        @return: L{userbase.LoginAccount} for C{username} or None
        """
        return self.loginSystem.accountByAddress(*username.split('@', 1))

    def resetPassword(self, attempt, newPassword):
        """
        @param attempt: L{_PasswordResetAttempt}

        reset the password of the user who initiated C{attempt} to C{newPassword},
        and afterward, delete the attempt and any persistent sessions that belong
        to the user
        """

        self.accountByAddress(attempt.username).password = newPassword

        self.store.query(PersistentSession,
                         PersistentSession.authenticatedAs == str(attempt.username)).deleteFromStore()

        attempt.deleteFromStore()

class NoSuchFactory(Exception):
    """
    An attempt was made to create a signup page using the name of a benefactor
    factory which did not correspond to anything in the database.
    """

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

    def issueViaEmail(self, issuer, email, benefactor, templateData,
                      domainName, httpPort=80):
        """
        Send a ticket via email to the supplied address, which, when claimed, will
        create an avatar and allow the given benefactor to endow it with
        things.

        @param issuer: An object, preferably a user, to track who issued this
        ticket.

        @param email: a str, formatted as an rfc2821 email address
        (user@domain) -- source routes not allowed.

        @param benefactor: an implementor of L{IBenefactor}

        @param domainName: a domain name, used as the domain part of the
        sender's address, and as the web server to generate a link to within
        the email.

        @param httpPort: a port number for the web server running on domainName

        @param templateData: A string containing an rfc2822-format email
        message, which will have several python values interpolated into it
        dictwise:

            %(from)s: To be used for the From: header; will contain an
             rfc2822-format address.

            %(to)s: the address that we are going to send to.

            %(date)s: an rfc2822-format date.

            %(message-id)s: an rfc2822 message-id

            %(link)s: an HTTP URL that we are generating a link to.

        """

        ticket = self.createTicket(issuer,
                                   unicode(email, 'ascii'),
                                   benefactor)
        nonce = ticket.nonce

        signupInfo = {'from': 'signup@'+domainName,
                      'to': email,
                      'date': rfc822.formatdate(),
                      'message-id': smtp.messageid(),
                      'link': self.ticketLink(domainName, httpPort, nonce)}

        msg = templateData % signupInfo

        return ticket, _sendEmail(signupInfo['from'], email, msg)

def _sendEmail(_from, to, msg):

    def gotMX(mx):
        return smtp.sendmail(str(mx.name), _from, [to], msg)

    return getMX().getMX(to.split('@', 1)[1]).addCallback(gotMX)

def _generateNonce():
    return unicode(os.urandom(16).encode('hex'), 'ascii')

class ITicketIssuer(Interface):
    def issueTicket(emailAddress):
        pass

class SignupMechanism(object):
    implements(ISignupMechanism, plugin.IPlugin)
    def __init__(self, name, description, itemClass, configuration):
        self.name = name
        self.description = description
        self.itemClass = itemClass
        self.configuration = configuration

freeTicketSignupConfiguration = [
    liveform.Parameter('prefixURL',
                       liveform.TEXT_INPUT,
                       unicode,
                       u'The web location at which users will be able to request tickets.',
                       u'signup')]

class FreeTicketSignup(Item, PrefixURLMixin):
    implements(ISiteRootPlugin)

    typeName = 'free_signup'
    schemaVersion = 5

    sessioned = True

    prefixURL = text(allowNone=False)
    booth = reference()
    benefactor = reference()
    emailTemplate = text()
    prompt = text()

    def createResource(self):
        return PublicAthenaLivePage(
            self.store,
            getLoader("signup"),
            IStaticShellContent(self.store, None),
            None,
            iface = ITicketIssuer,
            rootObject = self)

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
                self.emailTemplate,
                domain,
                port)

            issueDeferred.addCallback(
                lambda result: u'Please check your email for a ticket!')

            return issueDeferred

def freeTicketSignup1To2(old):
    return old.upgradeVersion('free_signup', 1, 2,
                              prefixURL=old.prefixURL,
                              booth=old.booth,
                              benefactor=old.benefactor)

upgrade.registerUpgrader(freeTicketSignup1To2, 'free_signup', 1, 2)

def freeTicketSignup2To3(old):
    emailTemplate = file(sibpath(__file__, 'signup.rfc2822')).read()
    emailTemplate %= {'blurb': u'',
                      'subject': 'Welcome to a Generic Axiom Application!',
                      'linktext': "Click here to claim your 'generic axiom application' account"}

    return old.upgradeVersion('free_signup', 2, 3,
                              prefixURL=old.prefixURL,
                              booth=old.booth,
                              benefactor=old.benefactor,
                              emailTemplate=emailTemplate)

upgrade.registerUpgrader(freeTicketSignup2To3, 'free_signup', 2, 3)

declareLegacyItem(typeName='free_signup',
                  schemaVersion=3,
                  attributes=dict(prefixURL=text(),
                                  booth=reference(),
                                  benefactor=reference(),
                                  emailTemplate=text()))

def freeTicketSignup3To4(old):
    return old.upgradeVersion('free_signup', 3, 4,
                              prefixURL=old.prefixURL,
                              booth=old.booth,
                              benefactor=old.benefactor,
                              emailTemplate=old.emailTemplate,
                              prompt=u'Sign Up')

upgrade.registerUpgrader(freeTicketSignup3To4, 'free_signup', 3, 4)

declareLegacyItem(typeName='free_signup',
                  schemaVersion=4,
                  attributes=dict(prefixURL=text(),
                                  booth=reference(),
                                  benefactor=reference(),
                                  emailTemplate=text(),
                                  prompt=text()))

def freeTicketSignup4To5(old):
    PasswordReset(store=old.store).installOn(old.store)

    return old.upgradeVersion('free_signup', 4, 5,
                              prefixURL=old.prefixURL,
                              booth=old.booth,
                              benefactor=old.benefactor,
                              emailTemplate=old.emailTemplate,
                              prompt=old.prompt)

upgrade.registerUpgrader(freeTicketSignup4To5, 'free_signup', 4, 5)

class InitializerBenefactor(Item, InstallableMixin):
    typeName = 'initializer_benefactor'
    schemaVersion = 1

    realBenefactor = reference()

    def endow(self, ticket, beneficiary):
        beneficiary.findOrCreate(WebSite).installOn(beneficiary)
        beneficiary.findOrCreate(PrivateApplication).installOn(beneficiary)

        # They may have signed up in the past - if so, they already
        # have a password, and we should skip the initializer phase.
        substore = beneficiary.store.parent.getItemByID(beneficiary.store.idInParent)
        for acc in self.store.query(userbase.LoginAccount,
                                    userbase.LoginAccount.avatars == substore):
            if acc.password:
                self.realBenefactor.endow(ticket, beneficiary)
            else:
                beneficiary.findOrCreate(Initializer).installOn(beneficiary)
            break

    def resumeSignup(self, ticket, avatar):
        self.realBenefactor.endow(ticket, avatar)

def freeTicketPasswordSignup(prefixURL=None, store=None, booth=None,
                             benefactor=None, emailTemplate=None, prompt=None):

    ibene = store.findOrCreate(InitializerBenefactor, realBenefactor=benefactor)

    return FreeTicketSignup(store=store,
                            benefactor=ibene,
                            booth=booth,
                            prefixURL=prefixURL,
                            emailTemplate=emailTemplate,
                            prompt=prompt)


class Initializer(Item, InstallableMixin):
    implements(INavigableElement)

    typeName = 'password_initializer'
    schemaVersion = 1

    installedOn = reference()

    def installOn(self, other):
        super(Initializer, self).installOn(other)
        other.powerUp(self, INavigableElement)

    def getTabs(self):
        # This won't ever actually show up
        return [Tab('Preferences', self.storeID, 1.0)]

    def setPassword(self, password):
        substore = self.store.parent.getItemByID(self.store.idInParent)
        for acc in self.store.parent.query(userbase.LoginAccount,
                                           userbase.LoginAccount.avatars == substore):
            acc.password = password
            self._delegateToBenefactor(acc)
            return

    def _delegateToBenefactor(self, loginAccount):
        site = self.store.parent
        ticket = site.findUnique(Ticket, Ticket.avatar == loginAccount)
        benefactor = ticket.benefactor
        benefactor.resumeSignup(ticket, self.store)

        self.store.powerDown(self, INavigableElement)
        self.deleteFromStore()

class InitializerPage(PublicPage):

    def __init__(self, original):
        for resource, domain in userbase.getAccountNames(original.installedOn):
            username = '%s@%s' % (resource, domain)
            break
        else:
            username = None
        PublicPage.__init__(self, original, original.store, getLoader('initialize'),
                            IStaticShellContent(original.installedOn, None),
                            username)

    def render_head(self, ctx, data):
        tag = PublicPage.render_head(self, ctx, data)
        return tag[tags.script(src='/Mantissa/js/initialize.js')]

    def renderHTTP(self, ctx):
        req = inevow.IRequest(ctx)
        password = req.args.get('password', [None])[0]

        if password is None:
            return Page.renderHTTP(self, ctx)

        self.original.store.transact(self.original.setPassword,
                                     unicode(password)) # XXX TODO: select
                                                        # proper decoding
                                                        # strategy.
        return URL.fromString('/')

registerAdapter(InitializerPage,
                Initializer,
                inevow.IResource)

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


class _DelegatedBenefactor(Item):
    typeName = 'mantissa_delegated_benefactor'
    schemaVersion = 1

    benefactor = reference(allowNone=False)
    multifactor = reference(allowNone=False)
    order = integer(allowNone=False, indexed=True)


class Multifactor(Item):
    """
    A benefactor with no behavior of its own, but which collects
    references to other benefactors and delegates endowment
    responsibility to them.
    """
    implements(IBenefactor)

    typeName = 'mantissa_multi_benefactor'
    schemaVersion = 1

    order = integer(default=0)

    def benefactors(self, order):
        for deleg in self.store.query(_DelegatedBenefactor,
                                      _DelegatedBenefactor.multifactor == self,
                                      sort=getattr(_DelegatedBenefactor.order, order)):
            yield deleg.benefactor

    def briefMultifactorDescription(self):
        """
        Generate a string which will allow an administrator to identify what
        this multifactor provides.  Currently it's raw.
        """
        return ', '.join(reflect.qual(x.__class__)
                         for x in self.benefactors('ascending'))


    def add(self, benefactor):
        """
        Add the given benefactor to the list of those which will be used to
        endow or deprive beneficiaries.

        This should only be done when creating the multifactor.  Adding
        benefactors to a multifactor that has already endowed a beneficiary
        will most likely have dire consequences.
        """
        _DelegatedBenefactor(store=self.store, multifactor=self, benefactor=benefactor, order=self.order)
        self.order += 1


    # IBenefactor
    def endow(self, ticket, beneficiary):
        for benefactor in self.benefactors('ascending'):
            benefactor.endow(ticket, beneficiary)


    def deprive(self, ticket, beneficiary):
        for benefactor in self.benefactors('descending'):
            benefactor.deprive(ticket, beneficiary)



class _SignupTracker(Item):
    """
    Signup-system private Item used to track which signup mechanisms
    have been created.
    """
    signupItem = reference()
    createdOn = timestamp()
    createdBy = text()


class SignupConfiguration(Item, InstallableMixin):
    """
    Provide administrative configuration tools for the signup options
    available on a Mantissa server.
    """
    typeName = 'mantissa_signup_configuration'
    schemaVersion = 1

    installedOn = reference()

    def installOn(self, other):
        super(SignupConfiguration, self).installOn(other)
        other.powerUp(self, INavigableElement)


    def getTabs(self):
        return [Tab('Admin', self.storeID, 0.5,
                    [Tab('Signup', self.storeID, 0.7)],
                    authoritative=False)]


    def getSignupSystems(self):
        return dict((p.name, p) for p in plugin.getPlugins(ISignupMechanism, plugins))


    def createSignup(self, creator, signupClass, signupConf, benefactorFactoryConfigurations, emailTemplate, prompt):
        siteStore = self.store.parent

        multifactor = Multifactor(store=siteStore)

        for factory in dependencyOrdered(benefactorFactoryConfigurations):
            benefactor = factory.instantiate(store=siteStore,
                                             **benefactorFactoryConfigurations[factory])
            multifactor.add(benefactor)

        booth = siteStore.findOrCreate(TicketBooth)
        booth.installOn(siteStore)
        signupItem = signupClass(
            store=siteStore,
            booth=booth,
            benefactor=multifactor,
            emailTemplate=emailTemplate,
            prompt=prompt,
            **signupConf)
        signupItem.installOn(siteStore)
        _SignupTracker(store=siteStore,
                       signupItem=signupItem,
                       createdOn=extime.Time(),
                       createdBy=creator)


def _insertDep(dependent, ordered):
    for dependency in dependent.dependencies():
        _insertDep(dependency, ordered)
    if dependent not in ordered:
        ordered.append(dependent)

def dependencyOrdered(coll):
    ordered = []
    for dependent in coll:
        _insertDep(dependent, ordered)
    return ordered


class BenefactorFactoryConfigMixin:
    def makeBenefactorCoercer(self, benefactorFactory):
        """
        Return a function that converts a selected flag and a set of
        keyword arguments into either None (if not selected) or a 2-tuple
        of (IBenefactorFactory provider, kwargs)
        """
        def benefactorCoercer(selectedBenefactor, **benefactorFactoryConfiguration):
            """
            Receive coerced values from the form post, massage them as
            described above.
            """
            if selectedBenefactor:
                return benefactorFactory, benefactorFactoryConfiguration
            return None
        return benefactorCoercer


    def makeBenefactorSelector(self, description):
        return liveform.Parameter('selectedBenefactor',
                                  liveform.CHECKBOX_INPUT,
                                  bool,
                                  description)


    def coerceBenefactor(self, **kw):
        return dict(filter(None, kw.values()))


    def getBenefactorFactories(self):
        for installedOffering in getInstalledOfferings(self.original.store.parent).itervalues():
            for beneFac in installedOffering.benefactorFactories:
                yield beneFac


    def benefactorFactoryConfigurationParameter(self, beneFac):
        return liveform.Parameter(
            beneFac.name,
            liveform.FORM_INPUT,
            liveform.LiveForm(self.makeBenefactorCoercer(beneFac),
                              [self.makeBenefactorSelector(beneFac.description)] + beneFac.parameters(),
                              beneFac.name))

    def makeBenefactorFactoryConfigurationForm(self):
        return liveform.LiveForm(
            self.coerceBenefactor,
            [self.benefactorFactoryConfigurationParameter(beneFac)
             for beneFac in self.getBenefactorFactories()],
            u"Benefactors for Signup")


class SignupFragment(athena.LiveFragment, BenefactorFactoryConfigMixin):
    fragmentName = 'signup-configuration'
    live = 'athena'

    def head(self):
        # i think this is the lesser evil.
        # alternatives being:
        #  * mangle form element names so we can put these in mantissa.css
        #    without interfering with similarly named things
        #  * put the following line of CSS into it's own file that is included
        #    by only this page
        #  * remove these styles entirely (makes the form unusable, the
        #    type="text" inputs are *tiny*)
        return tags.style(type='text/css')['''
        input[name=linktext], input[name=subject], textarea[name=blurb] { width: 40em }
        ''']

    def render_signupConfigurationForm(self, ctx, data):
        benefactorFactoryConfigurations = self.makeBenefactorFactoryConfigurationForm()

        def makeSignupCoercer(signupPlugin):
            """
            Return a function that converts a selected flag and a set of
            keyword arguments into either None (if not selected) or a 2-tuple
            of (signupClass, kwargs).  signupClass is a callable which takes
            the kwargs as keyword arguments and returns an Item (a signup
            mechanism plugin gizmo).
            """
            def signupCoercer(selectedSignup, **signupConf):
                """
                Receive coerced values from the form post, massage them as
                described above.
                """
                if selectedSignup:
                    return signupPlugin.itemClass, signupConf
                return None
            return signupCoercer

        def coerceSignup(**kw):
            return filter(None, kw.values())[0]

        signupMechanismConfigurations = liveform.LiveForm(
            # makeSignupCoercer sets it up, we knock it down. (Nones returned
            # are ignored, there will be exactly one selected).
            coerceSignup,
            [liveform.Parameter(
                signupMechanism.name,
                liveform.FORM_INPUT,
                liveform.LiveForm(
                    makeSignupCoercer(signupMechanism),
                    [liveform.Parameter(
                        'selectedSignup',
                        liveform.RADIO_INPUT,
                        bool,
                        signupMechanism.description)] + signupMechanism.configuration,
                    signupMechanism.name))
             for signupMechanism
             in self.original.getSignupSystems().itervalues()],
            u"Signup Type")

        def coerceEmailTemplate(**k):
            return file(sibpath(__file__, 'signup.rfc2822')).read() % k

        emailTemplateConfiguration = liveform.LiveForm(
            coerceEmailTemplate,
            [liveform.Parameter('subject',
                                liveform.TEXT_INPUT,
                                unicode,
                                u'Email Subject',
                                'Welcome to a Generic Axiom Application!'),
             liveform.Parameter('blurb',
                                liveform.TEXTAREA_INPUT,
                                unicode,
                                u'Blurb',
                                ''),
             liveform.Parameter('linktext',
                                liveform.TEXT_INPUT,
                                unicode,
                                u'Link Text',
                                "Click here to claim your 'generic axiom application' account")],
             description='Email Template')
        emailTemplateConfiguration.docFactory = getLoader('liveform-compact')

        existing = list(self.original.store.parent.query(FreeTicketSignup))
        if 0 < len(existing):
            deleteSignupForm = liveform.LiveForm(
                lambda **kw: self.deleteSignups(k for (k, v) in kw.itervalues() if v),
                [liveform.Parameter('signup-' + str(i),
                                    liveform.CHECKBOX_INPUT,
                                    lambda wasSelected, signup=signup: (signup, wasSelected),
                                    u'"%s" at /%s' % (signup.prompt, signup.prefixURL))
                    for (i, signup) in enumerate(existing)],
                description='Delete Existing Signups')
            deleteSignupForm.setFragmentParent(self)
        else:
            deleteSignupForm = ''

        createSignupForm = liveform.LiveForm(
            self.createSignup,
            [liveform.Parameter('signupPrompt',
                                liveform.TEXT_INPUT,
                                unicode,
                                u'Descriptive, user-facing prompt for this signup',
                                u'Sign Up'),
             liveform.Parameter('benefactorFactoryConfigurations',
                                liveform.FORM_INPUT,
                                benefactorFactoryConfigurations,
                                u'Pick some dude'),
             liveform.Parameter('signupTuple',
                                liveform.FORM_INPUT,
                                signupMechanismConfigurations,
                                u'Pick just one dude'),
             liveform.Parameter('emailTemplate',
                                liveform.FORM_INPUT,
                                emailTemplateConfiguration,
                                u'You know you want to')],
             description='Create Signup')
        createSignupForm.setFragmentParent(self)

        return [deleteSignupForm, createSignupForm]


    def data_configuredSignupMechanisms(self, ctx, data):
        for _signupTracker in self.original.store.parent.query(_SignupTracker):
            yield {
                'typeName': _signupTracker.signupItem.__class__.__name__,
                'createdBy': _signupTracker.createdBy,
                'createdOn': _signupTracker.createdOn.asHumanly()}


    allowedMethods = iface = {'createSignup': True,
                              'deleteSignup': True}
    def createSignup(self,
                     signupPrompt,
                     signupTuple,
                     benefactorFactoryConfigurations,
                     emailTemplate):
        (signupMechanism, signupConfig) = signupTuple
        t = self.original.store.transact
        t(self.original.createSignup,
          self.page.username,
          signupMechanism,
          signupConfig,
          benefactorFactoryConfigurations,
          emailTemplate,
          signupPrompt)
        return u'Great job.'

    def deleteSignups(self, signups):
        """
        delete the given signups.  this, and some of the
        other code in this module and elsewhere that expects
        everything to be a L{FreeTicketSignup} should eventually
        be changed to use a more extensible mechanism for signup
        location, like searching by interface or something (b/c
        we claim to support user defined signup types)

        @param signups: sequence of L{FreeTicketSignup}
        """

        for signup in signups:
            if signup.store is None:
                # we're not updating the list of live signups
                # client side, so we might get a signup that has
                # already been deleted
                continue

            signup.store.findUnique(_SignupTracker,
                                    _SignupTracker.signupItem == signup).deleteFromStore()

            for iface in signup.store.interfacesFor(signup):
                signup.store.powerDown(signup, iface)
            signup.deleteFromStore()

registerAdapter(SignupFragment, SignupConfiguration, INavigableFragment)
