
from axiom.store import Store
from axiom.userbase import LoginSystem

from xmantissa.webadmin import DeveloperSite, DeveloperApplication, DONTUSETHISBenefactor
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite
from xmantissa.signup import FreeTicketSignup, TicketBooth

s = Store("autoapp.axiom")
def _():
    # Install a user database so that people can log in.
    ls = LoginSystem(store=s)
    ls.installOn(s)
    s.checkpoint()
    # Install an HTTP server and root resource so we have some way to
    # access it through the web: point it at port 8080.
    WebSite(store=s, portno=8080).installOn(s)
    # Install static resources required for DeveloperApplication
    # below.  This is installed 'sessionlessly', meaning for everyone,
    # because although only developers will have access to the
    # *server* component of the Python command line, there is no
    # security reason to restrict access to the browser parts of it
    # (and it's faster that way)
    DeveloperSite(store=s).installOn(s)

    # Add an account for our administrator, so they can log in through
    # the web.
    la = ls.addAccount('admin', 'localhost', 'password')
    # Here we open their private database, where their personal
    # applications will be installed.  Personal applications show up
    # in the tab-based navigation under the '/private' URL.
    s2 = la.avatars.open()

    # XXX delete this eventually, broken dependency (required by the
    # next line, but should not be)
    LoginSystem(store=s2).installOn(s)

    # Install a web site for the individual user as well.  This is
    # necessary because although we have a top-level website for
    # everybody, not all users should be allowed to log in through the
    # web (like UNIX's "system users", "nobody", "database", etc.)
    # Note, however, that there is no port number, because the
    # WebSite's job in this case is to be a web *resource*, not a web
    # *server*.
    WebSite(store=s2).installOn(s2)

    # Now we install the 'private application' plugin for 'admin', on
    # admin's private store, This provides the URL "/private", but
    # only when 'admin' is logged in.  It is a hook to hang other
    # applications on.  (XXX Rename: PrivateApplication should
    # probably be called PrivateAppShell)
    PrivateApplication(store=s2).installOn(s2)

    # This is a plugin *for* the PrivateApplication; it publishes an
    # object via the tab-based navigation which is a Python
    # interactive interpreter.
    DeveloperApplication(store=s2).installOn(s2)

    # Testing a broken user; XXX ignore
    brok = ls.addAccount('broken', 'localhost', 'password')

    s3 = brok.avatars.open()
    LoginSystem(store=s3).installOn(s3)
    WebSite(store=s3).installOn(s3)

    PrivateApplication(store=s3).installOn(s3)

    # This is a plugin for the top-level store, which provides
    # ticket-based invitations and account creation in a generic way.
    # It is a prerequiste for ...
    bth = TicketBooth(store=s)
    bth.installOn(s)

    # A "benefactor" is an object that will grant a set of features to
    # a user when they are signed up; DONTUSETHISBenefactor is named
    # because it is a benefactor which will grant users it is bestowed
    # upon access to a Python interpreter, so DON'T USE IT in
    # production applications, or even test applications that will be
    # exposed beyond a small local network.

    ben = DONTUSETHISBenefactor(store=s)

    # FreeTicketSignup is a web-based signup system that will e-mail a
    # user a ticket, which they can then confirm and create their
    # account.  prefixURL here specifies where it will show up, so the
    # first URL you can hit with the application created with autoapp
    # is /admin-signup.
    
    fre = FreeTicketSignup(store=s,
                           benefactor=ben,
                           prefixURL=u'admin-signup',
                           booth=bth)
    fre.installOn(s)



s.transact(_)
