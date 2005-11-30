
import sys

from zope.interface import classProvides

from twisted.python import usage, util
from twisted.cred import portal
from twisted import plugin

from axiom import iaxiom, errors as eaxiom, userbase
from axiom.scripts import axiomatic

from xmantissa import website, webapp, signup, webadmin, offering, publicweb


def gtpswd(prompt, confirmPassword):
    """
    Temporary wrapper for Twisted's getPassword until a version that supports
    customizing the 'confirm' prompt is released.
    """
    try:
        return util.getPassword(prompt=prompt,
                                confirmPrompt=confirmPassword,
                                confirm=True)
    except TypeError:
        return util.getPassword(prompt=prompt,
                                confirm=True)

class Mantissa(usage.Options, axiomatic.AxiomaticSubCommandMixin):
    """
    Create all the moving parts necessary to begin interactively developing a
    Mantissa application component of your own.
    """

    # Throughout here we use findOrCreate rather than raw creation so that
    # duplicate installations of these components do not create garbage
    # objects.

    classProvides(plugin.IPlugin, iaxiom.IAxiomaticCommand)

    name = 'mantissa'
    description = 'Blank Mantissa service <for development>'

    longdesc = __doc__

    optParameters = [
        ('admin-user', 'a', 'admin@localhost',
         'Account name for the administrative user.'),
        ('admin-password', 'p', None,
         'Password for the administrative user '
         '(if omitted, will be prompted for).'),
        ('public-url', None, '',
         'URL at which to publish the public front page.')]

    def postOptions(self):
        s = self.parent.getStore()
        if self['admin-password'] is None:
            pws = u'Divmod\u2122 Mantissa\u2122 password for %r: ' % (self['admin-user'],)
            self['admin-password'] = gtpswd((u'Enter ' + pws).encode(sys.stdout.encoding, 'ignore'),
                                            (u'Confirm ' + pws).encode(sys.stdout.encoding, 'ignore'))

        self.installSite(s, self.decodeCommandLine(self['public-url']))
        self.installAdmin(
            s,
            self.decodeCommandLine(self['admin-user']),
            self['admin-password'])

    def installSite(self, s, publicURL):
        # Install a user database so that people can log in.
        s.findOrCreate(userbase.LoginSystem).installOn(s)

        # Install an HTTP server and root resource so we have some way to
        # access it through the web: point it at port 8080.
        s.findOrCreate(website.WebSite, lambda ws: setattr(ws, 'portNumber', 8080)).installOn(s)

        # Install static resources required for DeveloperApplication below.
        # This is installed 'sessionlessly', meaning for everyone, because
        # although only developers will have access to the *server* component
        # of the Python command line, there is no security reason to restrict
        # access to the browser parts of it (and it's faster that way)
        s.findOrCreate(webadmin.DeveloperSite).installOn(s)

        # Install a front page on the top level store so that the developer
        # will have something to look at when they start up the server.
        fp = s.findOrCreate(publicweb.FrontPage, prefixURL=u'')
        fp.installOn(s)

    def installAdmin(self, s, username, password):
        # Add an account for our administrator, so they can log in through the
        # web.
        r = portal.IRealm(s)
        username, domain = username.split('@')
        try:
            acc = r.addAccount(username, domain, password)
        except eaxiom.DuplicateUser:
            acc = r.accountByAddress(username, domain)

        accStore = acc.avatars.open()

        for cls in (

            # Install a web site for the individual user as well.  This is
            # necessary because although we have a top-level website for
            # everybody, not all users should be allowed to log in through the
            # web (like UNIX's "system users", "nobody", "database", etc.)
            # Note, however, that there is no port number, because the
            # WebSite's job in this case is to be a web *resource*, not a web
            # *server*.
            website.WebSite,

            # Now we install the 'private application' plugin for 'admin', on
            # admin's private store, This provides the URL "/private", but only
            # when 'admin' is logged in.  It is a hook to hang other
            # applications on.  (XXX Rename: PrivateApplication should probably
            # be called PrivateAppShell)
            webapp.PrivateApplication,

            # These are plugins *for* the PrivateApplication; they publish
            # objects via the tab-based navigation: a statistics page and a
            # Python interactive interpreter, respectively.
            webadmin.AdminStatsApplication,
            webadmin.DeveloperApplication,

            # This is another PrivateApplication plugin.  It allows the
            # administrator to configure the services offered here.
            offering.OfferingConfiguration,

            # And another one: SignupConfiguration allows the
            # administrator to add signup forms which grant various
            # kinds of account.
            signup.SignupConfiguration):

            accStore.findOrCreate(cls).installOn(accStore)
