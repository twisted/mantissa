from axiom.store import Store

from nevow.livetrial.testcase import TestCase
from nevow.athena import expose

from xmantissa import prefs

class GeneralPrefs(TestCase):
    jsClass = 'Mantissa.Test.GeneralPrefs'

    def getWidgetDocument(self):
        s = Store()

        self.dpc = prefs.DefaultPreferenceCollection(store=s)
        self.dpc.installOn(s)

        f = prefs.PreferenceCollectionFragment(self.dpc)
        f.setFragmentParent(self)
        return f

    def checkPersisted(self, itemsPerPage, timezone):
        self.assertEquals(self.dpc.itemsPerPage, itemsPerPage)
        self.assertEquals(self.dpc.timezone, timezone)
    expose(checkPersisted)
