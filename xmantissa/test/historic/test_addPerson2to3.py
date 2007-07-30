from axiom.test.historic import stubloader
from xmantissa.ixmantissa import INavigableElement
from xmantissa.people import AddPerson, Organizer


class AddPersonTest(stubloader.StubbedTest):
    """
    Test for upgrader removing AddPerson.
    """
    def testUpgrade(self):
        """
        Test that AddPerson is removed from the store and Organizer remains.
        """
        ap = self.store.findFirst(AddPerson, None)
        self.assertIdentical(ap, None)
        o = self.store.findUnique(Organizer, None)
        self.assertNotEqual(o, None)
