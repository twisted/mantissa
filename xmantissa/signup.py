# -*- test-case-name: xmantissa.test.test_signup -*-

import os, rfc822

from zope.interface import Interface, implements

from twisted.cred.portal import IRealm
from twisted.python.components import registerAdapter
from twisted.mail import smtp, relaymanager
from twisted.python.util import sibpath
from twisted.python import log
from twisted import plugin

from epsilon import extime

from axiom.item import Item, InstallableMixin, transacted
from axiom.attributes import integer, reference, text, timestamp, AND
from axiom.iaxiom import IBeneficiary
from axiom import userbase, upgrade

from nevow.rend import Page
from nevow.url import URL
from nevow.inevow import IResource, ISession
from nevow import inevow, tags, athena

from xmantissa.ixmantissa import (
    IBenefactor, ISiteRootPlugin, IStaticShellContent, INavigableElement,
    INavigableFragment, ISignupMechanism)
from xmantissa.website import PrefixURLMixin, WebSite
from xmantissa.publicresource import PublicAthenaLivePage, PublicPage, getLoader
from xmantissa.webnav import Tab
from xmantissa.webapp import PrivateApplication
from xmantissa.offering import getInstalledOfferings
from xmantissa import plugins, liveform

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
    schemaVersion = 3

    sessioned = True

    prefixURL = text(allowNone=False)
    booth = reference()
    benefactor = reference()
    emailTemplate = text()

    def createResource(self):
        return PublicAthenaLivePage(
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

def freeTicketPasswordSignup(prefixURL=None, store=None, booth=None, benefactor=None, emailTemplate=None):
    ibene = store.findOrCreate(InitializerBenefactor, realBenefactor=benefactor)
    return FreeTicketSignup(store=store,
                            benefactor=ibene,
                            booth=booth,
                            prefixURL=prefixURL,
                            emailTemplate=emailTemplate)


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
        PublicPage.__init__(self, original, getLoader('initialize'),
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


    def createSignup(self, creator, signupClass, signupConf, benefactorFactoryConfigurations, emailTemplate):
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

        signupForm = liveform.LiveForm(
            self.createSignup,
            [liveform.Parameter('benefactorFactoryConfigurations',
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
                                u'You know you want to')])
        signupForm.setFragmentParent(self)
        return signupForm


    def data_configuredSignupMechanisms(self, ctx, data):
        for _signupTracker in self.original.store.parent.query(_SignupTracker):
            yield {
                'typeName': _signupTracker.signupItem.__class__.__name__,
                'createdBy': _signupTracker.createdBy,
                'createdOn': _signupTracker.createdOn.asHumanly()}


    allowedMethods = iface = {'createSignup': True}
    def createSignup(self,
                     signupTuple,
                     benefactorFactoryConfigurations,
                     emailTemplate):
        (signupMechanism, signupConfig) = signupTuple
        t = self.original.store.transact
        t(self.original.createSignup,
          self.page.username,
          signupMechanism, signupConfig,
          benefactorFactoryConfigurations,
          emailTemplate)
        return u'Great job.'

registerAdapter(SignupFragment, SignupConfiguration, INavigableFragment)
