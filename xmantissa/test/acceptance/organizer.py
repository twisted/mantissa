"""
An interactive demonstration of L{xmantissa.people.EditPersonView}.

Run this test like this::
    $ twistd -n athena-widget --element=xmantissa.test.acceptance.organizer.editperson
    $ firefox http://localhost:8080/

This will display an address book.
"""

from axiom.store import Store
from axiom.dependency import installOn

from xmantissa.people import Organizer, EditPersonView

store = Store()
organizer = Organizer(store=store)
installOn(organizer, store)
person = organizer.createPerson(u'alice')

def editperson():
    """
    Create a database with a Person in it and return the L{EditPersonView} for
    that person.
    """
    return EditPersonView(person)

