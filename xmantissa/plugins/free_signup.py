
from xmantissa import signup

freeTicket = signup.SignupMechanism(
    name = 'free-ticket',
    description = '''
    Create a page which will allow anyone with a verified email
    address to sign up for the system.  When the user enters their
    email address, a confirmation email is sent to it containing a
    link which will allow signup to proceed.  When the link is
    followed, an account will be created and endowed by the
    benefactors associated with this instance.
    ''',
    itemClass = signup.FreeTicketSignup,
    configuration = signup.freeTicketSignupConfiguration)

freeTicketPassword = signup.SignupMechanism(
    name = 'free-ticket-password',
    description = '''
    Create a page which will allow anyone with a verified email address to
    sign up for the system.  When the user enters their email address, a
    confirmation email is sent to it containing a link which will allow
    signup to proceed.  When the link is followed, an account will be
    created and the user presented with a password prompt to set the initial
    value for their password.  After this has been completed, their account
    will be endowed by the benefactors associated with this instance.
    ''',
    itemClass = signup.freeTicketPasswordSignup,
    configuration = signup.freeTicketSignupConfiguration)
