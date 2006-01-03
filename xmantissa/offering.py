# -*- test-case-name: xmantissa.test.test_offering -*-

import os

from zope.interface import implements

from twisted import plugin
from twisted.python import util
from twisted.python.components import registerAdapter

from nevow import inevow, loaders, rend, tags, athena

from axiom import item, userbase, attributes, substore

from xmantissa import ixmantissa, webnav, plugins, website, webform, webtheme

class OfferingAlreadyInstalled(Exception):
    """
    Tried to install an offering, but an offering by the same name was
    already installed.

    This may mean someone tried to install the same offering twice, or
    that two unrelated offerings picked the same name and therefore
    conflict!  Oops.
    """

class Offering(object):
    implements(plugin.IPlugin, ixmantissa.IOffering)

    def __init__(self,
                 name,
                 description,
                 siteRequirements,
                 appPowerups,
                 benefactorFactories):
        self.name = name
        self.description = description
        self.siteRequirements = siteRequirements
        self.appPowerups = appPowerups
        self.benefactorFactories = benefactorFactories

class InstalledOffering(item.Item):
    typeName = 'mantissa_installed_offering'
    schemaVersion = 1

    offeringName = attributes.text(doc="""
    The name of the Offering to which this corresponds.
    """, allowNone=False)

    application = attributes.reference(doc="""
    A reference to the Application SubStore for this offering.
    """)


def getOfferings():
    """
    Return the IOffering plugins available on this system.
    """
    return plugin.getPlugins(ixmantissa.IOffering, plugins)


def getInstalledOfferingNames(s):
    """
    Return a list of the names of the Offerings which are installed on the
    given store.

    @param s: Site Store on which offering installations are tracked.
    """
    return list(s.query(InstalledOffering).getColumn("offeringName"))


def getInstalledOfferings(s):
    """
    Return a mapping from the names of installed IOffering plugins to
    the plugins themselves.

    @param s: Site Store on which offering installations are tracked.
    """
    d = {}
    installed = getInstalledOfferingNames(s)
    for p in getOfferings():
        if p.name in installed:
            d[p.name] = p
    return d


def installOffering(s, offering, configuration):
    for off in s.query(InstalledOffering,
                       InstalledOffering.offeringName == offering.name):
        raise Exception("That Offering is already installed.")

    def siteSetup():
        for (requiredInterface, requiredPowerup) in offering.siteRequirements:
            if requiredInterface is not None:
                nn = requiredInterface(s, None)
                if nn is not None:
                    continue
            if requiredPowerup is None:
                raise NotImplementedError(
                    'Interface %r required by %r but not provided by %r' %
                    (requiredInterface, offering, s))
            s.findOrCreate(requiredPowerup).installOn(s)

        ls = s.findOrCreate(userbase.LoginSystem)
        substoreItem = substore.SubStore.createNew(s, ('app', offering.name + '.axiom'))
        ls.addAccount(offering.name, None, None, internal=True,
                      avatars=substoreItem)
        ss = substoreItem.open()
        def appSetup():
            for pup in offering.appPowerups:
                pup(store=ss).installOn(ss)

        ss.transact(appSetup)
        # Woops, we need atomic cross-store transactions.
        io = InstalledOffering(store=s, offeringName=offering.name, application=substoreItem)
    s.transact(siteSetup)


class OfferingConfiguration(item.Item, item.InstallableMixin):
    """
    Provide administrative configuration tools for the L{IOffering}s available
    in this Mantissa server.
    """
    typeName = 'mantissa_offering_configuration_powerup'
    schemaVersion = 1

    installedOfferingCount = attributes.integer(default=0)
    installedOn = attributes.reference()

    def installOn(self, other):
        super(OfferingConfiguration, self).installOn(other)
        other.powerUp(self, ixmantissa.INavigableElement)

    def installOffering(self, offering, configuration):
        s = self.store.parent
        self.installedOfferingCount += 1
        installOffering(s, offering, configuration)


    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.3,
                           [webnav.Tab('Offerings', self.storeID, 0.5)],
                           authoritative=False)]



class UninstalledOfferingFragment(athena.LiveFragment):
    """
    Fragment representing a single Offering which has not been
    installed on the system.  It has a single remote method which will
    install it.
    """
    jsClass = u'Mantissa.Offering.UninstalledOffering'

    def __init__(self, original, offeringConfig, offeringPlugin, **kw):
        super(UninstalledOfferingFragment, self).__init__(original, **kw)
        self.offeringConfig = offeringConfig
        self.offeringPlugin = offeringPlugin

    allowedMethods = {'install': True}
    def install(self, configuration):
        self.offeringConfig.installOffering(self.offeringPlugin, configuration)



class OfferingConfigurationFragment(athena.LiveFragment):
    fragmentName = 'offering-configuration'
    live = 'athena'
    allowedMethods = {}


    def __init__(self, *a, **kw):
        super(OfferingConfigurationFragment, self).__init__(*a, **kw)
        self.installedOfferings = getInstalledOfferingNames(self.original.store.parent)
        self.offeringPlugins = dict((p.name, p) for p in plugin.getPlugins(ixmantissa.IOffering, plugins))

    def head(self):
        return None

    def render_offerings(self, ctx, data):
        iq = inevow.IQ(ctx.tag)
        uninstalled = iq.patternGenerator('uninstalled')
        installed = iq.patternGenerator('installed')

        def offerings():
            for p in self.offeringPlugins.itervalues():
                data = {'name': p.name, 'description': p.description}
                if p.name not in self.installedOfferings:
                    f = UninstalledOfferingFragment(data, self.original, p, docFactory=loaders.stan(uninstalled()))
                    f.page = self.page
                else:
                    f = rend.Fragment(data, docFactory=loaders.stan(installed()))
                yield f

        return ctx.tag[offerings()]

registerAdapter(OfferingConfigurationFragment, OfferingConfiguration, ixmantissa.INavigableFragment)


class EndowmentApplication(item.Item, item.InstallableMixin):
    """
    Gives the user it is installed upon the ability to invoke
    benefactors already configured on the system on arbitrary users.
    """
    implements(ixmantissa.INavigableElement)

    typeName = 'mantissa_endowment_app'
    schemaVersion = 1

    installedOn = attributes.reference()

    def installOn(self, other):
        super(EndowmentApplication, self).installOn(other)
        other.powerUp(self, ixmantissa.INavigableElement)

    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.0,
                           [webnav.Tab('Endow/Revoke', self.storeID, 0.2)],
                           authoritative=False)]

class EndowmentFragment(athena.LiveFragment):
    fragmentName = 'admin-endowment'

    live = 'athena'

    jsClass = u'Mantissa.Offering.SingleEndowment'

    def __init__(self, endowmentApp):
        self.endowmentApp = endowmentApp
        super(EndowmentFragment, self).__init__()

    def head(self):
        return None

    # XXX WHINE - I want a TDB.
    def render_benefactorFactories(self, ctx, data):
        self.benefactorFactories = {}
        for p in getInstalledOfferings(self.endowmentApp.store.parent).itervalues():
            for bf in p.benefactorFactories:
                self.benefactorFactories[p.name, bf.name] = bf
                yield BenefactorFactorySingleEndowment(bf)


    iface = allowedMethods = {'userExists': True, 'endow': True}
    def userExists(self, username):
        sitestore = self.endowmentApp.store.parent
        loginsystem = sitestore.findUnique(userbase.LoginSystem)
        account = loginsystem.accountByAddress(*username.split('@'))
        return account is not None


    def endow(self, user, configuration):
        sitestore = self.endowmentApp.store.parent
        loginsystem = sitestore.findUnique(userbase.LoginSystem)
        account = loginsystem.accountByAddress(*user.split('@', 1))
        substore = account.avatars.open()

        print configuration

#         benefactor = self.benefactorFactory.instantiate(store=store, **configuration)
#         benefactor.endow(None, substore)
#         benefactor.deleteFromStore()



class BenefactorFactorySingleEndowment(rend.Fragment):
    def __init__(self, benefactorFactory):
        super(BenefactorFactorySingleEndowment, self).__init__(self, docFactory=webtheme.getLoader('single-endowment'))
        self.benefactorFactory = benefactorFactory

    def render_name(self, ctx, data):
        return self.benefactorFactory.name

    def render_description(self, ctx, data):
        return self.benefactorFactory.description

    def render_configuration(self, ctx, data):
        return ctx.tag[webform.Form(self.benefactorFactory.parameters())]

registerAdapter(EndowmentFragment, EndowmentApplication, ixmantissa.INavigableFragment)
