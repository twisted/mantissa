
import sys

from zope.interface import classProvides

from twisted.python import usage, util
from twisted.cred import portal
from twisted import plugin

from axiom import iaxiom, errors as eaxiom, userbase
from axiom.scripts import axiomatic

from xmantissa import website, webapp, signup, webadmin, offering, publicweb

from epsilon.asplode import splode


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


        publicURL = self.decodeCommandLine(self['public-url'])
        adminUser = self.decodeCommandLine(self['admin-user'])
        adminPassword = self['admin-password']

        s.transact(self.installSite, s, publicURL)
        s.transact(self.installAdmin, s, adminUser, adminPassword)

    def installSite(self, s, publicURL):
        # Install a user database so that people can log in.
        s.findOrCreate(userbase.LoginSystem).installOn(s)

        # Install an HTTP server and root resource so we have some way
        # to access it through the web: point it at port 8080.
        s.findOrCreate(website.WebSite, lambda ws: setattr(ws, 'portNumber', 8080)).installOn(s)

        # Install static resources required for DeveloperApplication
        # below.  This is installed 'sessionlessly', meaning for
        # everyone, because although only developers will have access
        # to the *server* component of the Python command line, there
        # is no security reason to restrict access to the browser
        # parts of it (and it's faster that way)
        s.findOrCreate(webadmin.DeveloperSite).installOn(s)

        # Install a front page on the top level store so that the
        # developer will have something to look at when they start up
        # the server.
        fp = s.findOrCreate(publicweb.FrontPage, prefixURL=u'')
        fp.installOn(s)

        # Create a benefactor, by way of which we will be able to
        # configure the abilities of our first administrative user, to
        # be created below.
        ab = s.findOrCreate(webadmin.AdministrativeBenefactor)
        self.administrativeBenefactor = ab

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
        accStore.transact(self.administrativeBenefactor.endow, None, accStore)


class Generate(usage.Options, axiomatic.AxiomaticSubCommandMixin):
    classProvides(plugin.IPlugin, iaxiom.IAxiomaticCommand)

    name = "project"

    # This will show up next to the name in --help output
    description = "Generate most basic skeleton of a Mantissa app"

    optParameters = [
        ('name', 'n', None, 'The name of the app to deploy'),
        ]

    def postOptions(self):
        proj = self.decodeCommandLine(self['name'])
        proj = proj.lower()
        capproj = proj.capitalize()
        print "Creating", capproj, "in", capproj

        fObj = file(util.sibpath(__file__, 'template.txt'))

        splode(fObj.readlines(), proj, capproj)
