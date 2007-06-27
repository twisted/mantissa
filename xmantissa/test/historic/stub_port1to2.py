from axiom.item import Item
from axiom.attributes import text
from axiom.test.historic.stubloader import saveStub

from xmantissa.port import TCPPort, SSLPort
from xmantissa.website import WebSite



def createDatabase(s):
    """
    Populate the given Store with a TCPPort and SSLPort.
    """
    factory = WebSite(store=s)
    TCPPort(store=s, portNumber=80, factory=factory)
    SSLPort(store=s, portNumber=443,
            certificatePath=s.newFilePath('certificate'), factory=factory)



if __name__ == '__main__':
    saveStub(createDatabase, 12731)
