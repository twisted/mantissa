# -*- test-case-name: xmantissa.test.historic.test_website5to6 -*-

from axiom.test.historic.stubloader import saveStub

from axiom.plugins.mantissacmd import Mantissa
from axiom.userbase import LoginSystem
from axiom.dependency import installOn

from xmantissa.port import TCPPort, SSLPort
from xmantissa.website import WebSite

from xmantissa.test.historic.stub_website4to5 import cert

def createDatabase(store):
    """
    Initialize the given Store for use as a Mantissa webserver.
    """
    Mantissa().installSite(store, u'example.net')
    site = store.findUnique(WebSite)
    site.httpLog = store.filesdir.child('httpd.log').path
    site.hitCount = 123
    site.hostname = u'example.net'
    tcp = store.findUnique(TCPPort, TCPPort.factory == site)
    tcp.portNumber = 8088
    ssl = store.findUnique(SSLPort, SSLPort.factory == site)
    ssl.portNumber = 6443
    ssl.certificatePath.setContent(cert)
    loginSystem = store.findUnique(LoginSystem)
    account = loginSystem.addAccount(u'testuser', u'localhost', None)
    subStore = account.avatars.open()
    installOn(WebSite(store=subStore), subStore)

if __name__ == '__main__':
    saveStub(createDatabase, 14982)
