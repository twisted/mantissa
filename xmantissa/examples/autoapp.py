
from axiom.store import Store
from axiom.userbase import LoginSystem

from xmantissa.webadmin import DeveloperApplication, DONTUSETHISBenefactor
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite
from xmantissa.signup import FreeTicketSignup, TicketBooth

s = Store("test.axiom", debug=True)
def _():
    ls = LoginSystem(store=s)
    ls.install()
    s.checkpoint()
    WebSite(store=s, portno=8080).install()

    la = ls.addAccount('admin', 'localhost', 'password')
    s2 = la.avatars.open()
    LoginSystem(store=s2).install()
    WebSite(store=s2).install()

    PrivateApplication(store=s2).install()
    DeveloperApplication(store=s2).install()

    brok = ls.addAccount('broken', 'localhost', 'password')

    s3 = brok.avatars.open()
    LoginSystem(store=s3).install()
    WebSite(store=s3).install()

    PrivateApplication(store=s3).install()

    # MECHANISM
    bth = TicketBooth(store=s)
    bth.install()

    # POLICY
    ben = DONTUSETHISBenefactor(store=s)
    fre = FreeTicketSignup(store=s,
                           benefactor=ben,
                           prefixURL=u'admin-signup',
                           booth=bth)
    fre.install()



s.transact(_)
