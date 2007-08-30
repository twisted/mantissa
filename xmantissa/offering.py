# -*- test-case-name: xmantissa.test.test_offering -*-

from zope.interface import implements

from twisted import plugin
from twisted.python.components import registerAdapter

from nevow import inevow, loaders, rend, athena
from nevow.athena import expose

from axiom import item, userbase, attributes, substore
from axiom.dependency import installOn

from xmantissa import ixmantissa, webnav, plugins

class OfferingAlreadyInstalled(Exception):
    """
    Tried to install an offering, but an offering by the same name was
    already installed.

    This may mean someone tried to install the same offering twice, or
    that two unrelated offerings picked the same name and therefore
    conflict!  Oops.
    """

class Benefactor(object):
    """
    I implement a method of installing and removing chunks of
    functionality from a user's store.
    """

class Offering(object):
    implements(plugin.IPlugin, ixmantissa.IOffering)

    def __init__(self,
                 name,
                 description,
                 siteRequirements,
                 appPowerups,
                 installablePowerups,
                 loginInterfaces,
                 themes,
                 version=None):
        self.name = name
        self.description = description
        self.siteRequirements = siteRequirements
        self.appPowerups = appPowerups
        self.installablePowerups = installablePowerups
        self.loginInterfaces = loginInterfaces
        self.themes = themes
        self.version = version

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
    """
    Create an app store for an Offering, possibly installing some powerups on
    it, after checking that the site store has the requisite powerups installed
    on it. Also create an InstalledOffering item referring to the app store.
    """
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
            s.findOrCreate(requiredPowerup, lambda p: installOn(p, s))

        ls = s.findOrCreate(userbase.LoginSystem)
        substoreItem = substore.SubStore.createNew(s, ('app', offering.name + '.axiom'))
        ls.addAccount(offering.name, None, None, internal=True,
                      avatars=substoreItem)
        ss = substoreItem.open()
        def appSetup():
            for pup in offering.appPowerups:
                installOn(pup(store=ss), ss)

        ss.transact(appSetup)
        # Woops, we need atomic cross-store transactions.
        io = InstalledOffering(store=s, offeringName=offering.name, application=substoreItem)

        #Some new themes may be available now. Clear the theme cache
        #so they can show up.
        #XXX This is pretty terrible -- there
        #really should be a scheme by which ThemeCache instances can
        #be non-global. Fix this at the earliest opportunity.
        from xmantissa import webtheme
        webtheme.theThemeCache.emptyCache()
    s.transact(siteSetup)


class OfferingConfiguration(item.Item):
    """
    Provide administrative configuration tools for the L{IOffering}s available
    in this Mantissa server.
    """
    typeName = 'mantissa_offering_configuration_powerup'
    schemaVersion = 1

    installedOfferingCount = attributes.integer(default=0)
    installedOn = attributes.reference()
    powerupInterfaces = (ixmantissa.INavigableElement,)

    def installOffering(self, offering, configuration):
        s = self.store.parent
        self.installedOfferingCount += 1
        installOffering(s, offering, configuration)


    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.3,
                           [webnav.Tab('Offerings', self.storeID, 1.0)],
                           authoritative=True)]



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

    def install(self, configuration):
        self.offeringConfig.installOffering(self.offeringPlugin, configuration)
    expose(install)


class OfferingConfigurationFragment(athena.LiveFragment):
    fragmentName = 'offering-configuration'
    live = 'athena'


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
