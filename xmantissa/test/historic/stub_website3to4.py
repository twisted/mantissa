# -*- test-case-name: xmantissa.test.historic.test_website3to4 -*-

from axiom.test.historic.stubloader import saveStub

from axiom.plugins.mantissacmd import Mantissa

from xmantissa.website import WebSite


def createDatabase(s):
    """
    Initialize the given Store for use as a Mantissa webserver.
    """
    Mantissa().installSite(s, u'')
    ws = s.findUnique(WebSite)
    ws.portNumber = 80
    ws.securePortNumber = 443
    ws.certificateFile = 'path/to/cert.pem'
    ws.httpLog = 'path/to/httpd.log'
    ws.hitCount = 100

if __name__ == '__main__':
    saveStub(createDatabase, 7617)
