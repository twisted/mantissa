from twisted.python import usage
from axiom.scripts import axiomatic

from xmantissa import offering

class Install(axiomatic.AxiomaticSubCommand):
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

class List(axiomatic.AxiomaticSubCommand):
    def postOptions(self):
        for o in offering.getOfferings():
            print "%s: %s" % (o.name, o.description)

class OfferingCommand(axiomatic.AxiomaticCommand):
    name = "offering"
    description = "View and accept the offerings of puny mortals."

    subCommands = [
        ("install", None, Install, "Install an offering."),
        ("list", None, List, "List available offerings."),
        ]

    def getStore(self):
        return self.parent.getStore()
