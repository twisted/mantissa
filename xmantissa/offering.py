# -*- test-case-name: xmantissa.test.test_offering -*-

import os

from zope.interface import implements

from twisted import plugin
from twisted.python import util
from twisted.python.components import registerAdapter

from nevow import rend, tags

from axiom import item, userbase, attributes, substore

from xmantissa import ixmantissa, webnav, plugins, website

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
            substoreItem = substore.SubStore(s, ('app', offering.name + '.axiom'))
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

    def getTabs(self):
        return [webnav.Tab('Admin', self.storeID, 0.3,
                           [webnav.Tab('Offerings', self.storeID, 0.5)],
                           authoritative=False)]

class OfferingFragment(rend.Fragment):
    fragmentName = 'site-offerings'
    live = 'athena'

    def head(self):
        return tags.script(type='text/javascript', src='/static/mantissa/js/offerings.js')

    def data_offerings(self, ctx, data):
        i = dict.fromkeys(self.original.store.parent.query(InstalledOffering).getColumn("offeringName"))
        for p in plugin.getPlugins(ixmantissa.IOffering, plugins):
            yield {
                'name': p.name,
                'description': p.description,
                'installed': (('un' * (p.name not in i)) + 'installed')
                }

    # Remote API!
    iface = {'installOffering': True}
    def installOffering(self, offeringName):
        for p in plugin.getPlugins(ixmantissa.IOffering, plugins):
            if p.name == offeringName:
                for off in self.original.store.query(InstalledOffering, InstalledOffering.offeringName == offeringName):
                    raise Exception("That Offering is already installed.")
                else:
                    self.original.installOffering(p, None)
                    break

registerAdapter(OfferingFragment, OfferingConfiguration, ixmantissa.INavigableFragment)
