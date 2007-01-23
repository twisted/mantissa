# -*- test-case-name: xmantissa.test.historic.test_website4to5 -*-

from axiom.test.historic.stubloader import saveStub

from axiom.plugins.mantissacmd import Mantissa
from axiom.userbase import LoginSystem
from axiom.dependency import installOn

from xmantissa.website import WebSite

def createDatabase(store):
    """
    Initialize the given Store for use as a Mantissa webserver.
    """
    Mantissa().installSite(store, u'')
    site = store.findUnique(WebSite)
    site.portNumber = 8088
    site.securePortNumber = 6443
    site.certificateFile = 'server.pem'
    store.dbdir.child('server.pem').setContent('--- PEM ---\n')
    site.httpLog = 'path/to/httpd.log'
    site.hitCount = 123
    site.hostname = u'example.net'
    loginSystem = store.findUnique(LoginSystem)
    account = loginSystem.addAccount(u'testuser', u'localhost', None)
    subStore = account.avatars.open()
    installOn(WebSite(store=subStore), subStore)


if __name__ == '__main__':
    saveStub(createDatabase, 11023)
