# -*- test-case-name: xmantissa.test.historic.test_privateApplication3to4 -*-

"""
Generate a test database containing a L{PrivateApplication} installed on its
store without powering it up for L{ITemplateNameResolver}.
"""

from axiom.test.historic.stubloader import saveStub
from axiom.dependency import installOn

from xmantissa.webapp import PrivateApplication


PREFERRED_THEME = u'theme-preference'
HIT_COUNT = 8765
PRIVATE_KEY = 123456


def createDatabase(store):
    """
    Instantiate a L{PrivateApplication} in C{store} and install it.
    """
    app = PrivateApplication(
        store=store,
        preferredTheme=PREFERRED_THEME,
        hitCount=HIT_COUNT,
        privateKey=PRIVATE_KEY)
    installOn(app, store)


if __name__ == '__main__':
    saveStub(createDatabase, 12759)
