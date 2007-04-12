from axiom.test.historic import stubloader
from xmantissa import people, ixmantissa

class OrganizerTest(stubloader.StubbedTest):
    """
    Tests for L{people.Organizer} 2->3 upgrader
    """
    def test_upgrade(self):
        """
        Test that there is a I{me} person, and that the
        L{axiom.userbase.LoginMethod} was turned into a
        L{people.EmailAddress}, and there are no L{people.RealName} items
        """
        organizer = self.store.findUnique(people.Organizer)
        self.assertIdentical(
            organizer.ownerPerson, self.store.findUnique(people.Person))
        self.assertEquals(
            self.store.count(people.RealName), 0)
        self.assertEquals(
            self.store.count(people.EmailAddress), 1)
        self.assertEquals(
            organizer.ownerPerson.getEmailAddress(), 'bob@divmod.com')

    def test_powerup(self):
        """
        Test that L{people.Organizer} is a L{ixmantissa.IOrganizer}
        powerup
        """
        self.assertIdentical(
            ixmantissa.IOrganizer(self.store),
            self.store.findUnique(people.Organizer))
