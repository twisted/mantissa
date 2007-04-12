from axiom.test.historic.stubloader import saveStub
from axiom.userbase import LoginMethod

from xmantissa.people import Organizer

def createDatabase(s):
    LoginMethod(
        store=s,
        account=s,
        localpart=u'bob',
        domain=u'divmod.com',
        verified=False,
        internal=False,
        protocol=u'email')
    Organizer(store=s)

if __name__ == '__main__':
    saveStub(createDatabase, 11900)
