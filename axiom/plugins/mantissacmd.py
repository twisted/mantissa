
import sys

from twisted.python import util
from twisted.cred import portal

from axiom import errors as eaxiom, userbase
from axiom.scripts import axiomatic
from axiom.attributes import AND

from xmantissa import website, webadmin, publicweb, stats

from epsilon.asplode import splode
from epsilon.scripts import certcreate

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

class Mantissa(axiomatic.AxiomaticCommand):
    """
    Create all the moving parts necessary to begin interactively developing a
    Mantissa application component of your own.
    """

    # Throughout here we use findOrCreate rather than raw creation so that
    # duplicate installations of these components do not create garbage
    # objects.

    name = 'mantissa'
    description = 'Blank Mantissa service'

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
        certPath = s.dbdir.child("server.pem")
        if not certPath.exists():
            certcreate.main(['--filename', certPath.path, '--quiet'])
        # Install a user database so that people can log in.
        s.findOrCreate(userbase.LoginSystem).installOn(s)

        # Install an HTTP server and root resource so we have some way
        # to access it through the web: point it at port 8080.
        s.findOrCreate(website.WebSite, lambda ws: (setattr(ws,
                                                            'portNumber',
                                                            8080),
                                                    setattr(ws,
                                                            'securePortNumber',
                                                            8443),
                                                    setattr(ws,
                                                            'certificateFile',
                                                            certPath.path))
                       ).installOn(s)

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
            acc = r.addAccount(username, domain, password, internal=True, verified=True)
        except eaxiom.DuplicateUser:
            acc = r.accountByAddress(username, domain)

        accStore = acc.avatars.open()
        accStore.transact(self.administrativeBenefactor.endow, None, accStore)


class Generate(axiomatic.AxiomaticCommand):
    name = "project"

    # This will show up next to the name in --help output
    description = "Generate most basic skeleton of a Mantissa app"

    optParameters = [
        ('name', 'n', None, 'The name of the app to deploy'),
        ]

    def postOptions(self):
        if self['name'] is None:
            proj = ''
            while( proj == ''):
                try:
                    proj = raw_input("Please provide the name of the app to deploy: " )
                except KeyboardInterrupt:
                    raise SystemExit()
        else:
            proj = self.decodeCommandLine(self['name'])
        proj = proj.lower()
        capproj = proj.capitalize()
        print "Creating", capproj, "in", capproj

        fObj = file(util.sibpath(__file__, 'template.txt'))

        splode(fObj.readlines(), proj, capproj)

class RemoteStatsAdd(axiomatic.AxiomaticSubCommand):

    optParameters = [
        ("host", "h", None, "The host accepting statistical data."),
        ("port", "p", None, "The port to connect to."),
        ]

    def postOptions(self):
        s = self.parent.parent.getStore()
        s.transact(self.installCollector, s, self['host'], int(self['port']))

    def installCollector(self, s, host, port):
        ss = portal.IRealm(s).accountByAddress(u'mantissa',
                                               None).avatars.open()
        obs = stats.RemoteStatsObserver(store=ss, hostname=host, port=port)

class RemoteStatsList(axiomatic.AxiomaticSubCommand):
    def postOptions(self):
        s = self.parent.parent.getStore()
        ss = portal.IRealm(s).accountByAddress(u'mantissa',
                                               None).avatars.open()
        for i, obs in enumerate(ss.query(stats.RemoteStatsObserver)):
            print "%s) %s:%s" % (i, obs.hostname, obs.port)

class RemoteStatsRemove(axiomatic.AxiomaticSubCommand):
    optParameters = [
        ("host", "h", None, "The hostname of the observer to remove."),
        ("port", "p", None, "The port of the observer to remove."),
        ]
    def postOptions(self):
        s = self.parent.parent.getStore()
        ss = portal.IRealm(s).accountByAddress(u'mantissa',
                                               None).avatars.open()
        for obs in ss.query(stats.RemoteStatsObserver,
                            AND(stats.RemoteStatsObserver.hostname==self['host'], stats.RemoteStatsObserver.port==int(self['port']))):
            obs.deleteFromStore()

class RemoteStats(axiomatic.AxiomaticCommand):
    name = "stats"
    description = "Control remote statistics collection"

    subCommands = [("add", None, RemoteStatsAdd, "Submit Mantissa statistical data to another server"),
                   ("list", None, RemoteStatsList, "List remote targets for stats delivery"),
                   ("remove", None, RemoteStatsRemove, "Remove a remote stats target")]
