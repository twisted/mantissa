
from axiom.store import Store
from axiom.userbase import LoginSystem

from xmantissa.webadmin import DeveloperApplication
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite

s = Store("test.axiom", debug=True)
ls = LoginSystem(store=s)
ls.install()
WebSite(store=s, portno=8080).install()

la = ls.addAccount('admin', 'localhost', 'password')
s2 = la.avatars.open()
LoginSystem(store=s2).install()

WebSite(store=s2).install()


PrivateApplication(store=s2).install()
DeveloperApplication(store=s2).install()
