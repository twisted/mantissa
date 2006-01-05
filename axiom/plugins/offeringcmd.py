from zope.interface import classProvides
from twisted.python import usage
from twisted import plugin
from axiom import iaxiom
from axiom.scripts import axiomatic

from xmantissa import offering

class Install(usage.Options, axiomatic.AxiomaticSubCommandMixin):
    synopsis = "<offering>"

    def parseArgs(self, offering):
        self["offering"] = self.decodeCommandLine(offering)

    def postOptions(self):
        for o in offering.getOfferings():
            if o.name == self["offering"]:
                offering.installOffering(self.store, o, None)
                break
        else:
            raise usage.UsageError("No such offering")

class List(usage.Options, axiomatic.AxiomaticSubCommandMixin):
    def postOptions(self):
        for o in offering.getOfferings():
            print "%s: %s" % (o.name, o.description)

class OfferingCommand(usage.Options, axiomatic.AxiomaticSubCommandMixin):
    classProvides(plugin.IPlugin, iaxiom.IAxiomaticCommand)

    name = "offering"
    description = "View and accept the offerings of puny mortals."

    subCommands = [
        ("install", None, Install, "Install an offering."),
        ("list", None, List, "List available offerings."),
        ]

    def getStore(self):
        return self.parent.getStore()
