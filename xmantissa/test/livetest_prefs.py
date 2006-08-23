from axiom.store import Store

from nevow.livetrial.testcase import TestCase
from nevow.athena import expose

from xmantissa import prefs

class GeneralPrefs(TestCase):
    """
    Test case which renders L{xmantissa.ixmantissa.DefaultPreferenceCollection}
    and ensures that values changed client-side are correctly persisted
    """
    jsClass = 'Mantissa.Test.GeneralPrefs'

    def getWidgetDocument(self):
        s = Store()

        self.dpc = prefs.DefaultPreferenceCollection(store=s)
        self.dpc.installOn(s)

        f = prefs.PreferenceCollectionFragment(self.dpc)
        class Tab:
            name = ''
            children = ()

        f.tab = Tab
        f.setFragmentParent(self)
        return f

    def checkPersisted(self, itemsPerPage, timezone):
        """
        Assert that our preference collection has had its C{itemsPerPage}
        and C{timezone} attributes set to C{itemsPerPage} and C{timezone}.
        Called after the deferred returned by the liveform controller's
        C{submit} method has fired
        """
        self.assertEquals(self.dpc.itemsPerPage, itemsPerPage)
        self.assertEquals(self.dpc.timezone, timezone)
    expose(checkPersisted)
