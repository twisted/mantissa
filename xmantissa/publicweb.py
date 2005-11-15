
"""
Support for the public-facing portion of web applications.
"""

from zope.interface import implements

from twisted.internet import defer

from nevow import inevow, rend

from axiom import item, attributes, upgrade

from xmantissa import ixmantissa, website, publicresource

class PublicWeb(item.Item, website.PrefixURLMixin):
    """
    Fixture for site-wide public-facing content.

    I implement ISiteRootPlugin and use PrefixURLMixin; see the documentation
    for each of those for a detailed explanation of my usage.

    I adapt another object to IPublicPage, call the public page's
    createResource() method, and display that resource.

    This is designed to be installed on a user who has some public facing
    content.  There are two contexts where a public page is useful: at the top
    level of a site, via a 'system user', and for the public facing view of a
    user's store who has a private view of that data using
    L{webapp.PrivateApplication}.

    For the former case, for example to put some dynamic content on the root
    page of a public site, the convention is to create an avatar (with a
    substore) to represent the public portion of your application and then wrap
    a PublicWeb around it as the plugin in the top-level store.  Example::

        s = Store("my-site.axiom")
        # Install login database
        ls = LoginSystem(store=s)
        # Install HTTP server
        WebSite(store=s, portNumber=8080, securePortNumber=8443,
                certificateFile='server.pem').installOn(s)

        # Add 'system user' to hold data that will be displayed on the public page.
        mySiteSystemUser = ls.addAccount('my-site', 'my-site.example.com', None)
        # Open the substore that was automatically created for us
        substore = mySiteSystemUser.avatars.open()
        # Install your custom application public page on the substore, so that
        # PublicWeb will find the IPublicPage implementor when it adapts
        substore.powerUp(MySitePublicPage(store=substore),
                         IPublicPage)
        # Install the PublicWeb on the top-level store, as a plugin for the
        # WebSite installed above.
        PublicWeb(store=s,
                  sessionless=True,  # Alternatively, sessioned=True
                  prefixURL=u'path/to/my-site',
                  application=mySiteSystemUser).installOn(s)


    @ivar application: An Item which implements L{ixmantissa.IPublicPage}.
    """
    implements(ixmantissa.ISiteRootPlugin,
               ixmantissa.ISessionlessSiteRootPlugin)

    typeName = 'mantissa_public_web'
    schemaVersion = 3

    prefixURL = attributes.text(allowNone=False)
    application = attributes.reference(allowNone=False)

    installedOn = attributes.reference()

    sessioned = attributes.boolean(default=False)
    sessionless = attributes.boolean(default=False)

    def resourceFactory(self, segments):
        if not segments[0].startswith('__'):
            return super(PublicWeb, self).resourceFactory(segments)
        return None

    def createResource(self):
        # XXX Don't like this - shouldn't need IPublicPage interface
        # at all.
        return ixmantissa.IPublicPage(self.application).getResource()


def upgradePublicWeb1To2(oldWeb):
    newWeb = oldWeb.upgradeVersion(
        'mantissa_public_web', 1, 2,
        prefixURL=oldWeb.prefixURL,
        application=oldWeb.application,
        installedOn=oldWeb.installedOn)
    newWeb.installedOn.powerUp(newWeb, ixmantissa.ICustomizablePublicPage)
    return newWeb
upgrade.registerUpgrader(upgradePublicWeb1To2, 'mantissa_public_web', 1, 2)

def upgradePublicWeb2To3(oldWeb):
    newWeb = oldWeb.upgradeVersion(
        'mantissa_public_web', 2, 3,
        prefixURL=oldWeb.prefixURL,
        application=oldWeb.application,
        installedOn=oldWeb.installedOn,
        # There was only one PublicWeb before, and it definitely
        # wanted to be sessioned.
        sessioned=True)
    newWeb.installedOn.powerDown(newWeb, ixmantissa.ICustomizablePublicPage)
    other = newWeb.installedOn
    newWeb.installedOn = None
    newWeb.installOn(other)
    return newWeb
upgrade.registerUpgrader(upgradePublicWeb2To3, 'mantissa_public_web', 2, 3)


class CustomizingResource(object):
    implements(inevow.IResource)

    def __init__(self, topResource, forWho):
        # assume that this is a root resource and locateChild will be
        # called at least once: otherwise do adaptation here too
        self.currentResource = topResource
        self.forWho = forWho

    def locateChild(self, ctx, path):
        D = defer.maybeDeferred(
            self.currentResource.locateChild, ctx, path)

        def finishLocating((nextRes, nextPath)):
            custom = ixmantissa.ICustomizable(nextRes, None)
            if custom is not None:
                return (custom.customizeFor(self.forWho), nextPath)
            self.currentResource = nextRes
            return (self, nextPath)

        return D.addCallback(finishLocating)

    def renderHTTP(self, ctx):
        # We never got customized.
        if self.currentResource is None:
            return rend.FourOhFour()
        return self.currentResource.renderHTTP(ctx)


class CustomizedPublicPage(item.Item, item.InstallableMixin):
    """
    Per-avatar hook at '/' which finds the real public-page and asks
    it to customize itself for a particular user.
    """

    typeName = 'mantissa_public_customized'
    schemaVersion = 2

    installedOn = attributes.reference(
        '''The Avatar for which this item will attempt to retrieve a
        customized page.''')

    def installOn(self, other):
        super(CustomizedPublicPage, self).installOn(other)
        # See irc://freenode.net/divmod conversation between exarkun
        # and glyph of Sat Oct 29, 2005 regarding the correctness of
        # the priority modifier of -256.
        other.powerUp(self, ixmantissa.ISiteRootPlugin, -257)

    def resourceFactory(self, segments):
        topResource = inevow.IResource(self.installedOn.store.parent, None)
        if topResource is not None:
            return (CustomizingResource(topResource, self.installedOn), segments)
        return None

def customizedPublicPage1To2(oldPage):
    newPage = oldPage.upgradeVersion(
        'mantissa_public_customized', 1, 2,
        installedOn=oldPage.installedOn)
    newPage.installedOn.powerDown(newPage, ixmantissa.ISiteRootPlugin)
    newPage.installedOn.powerUp(newPage, ixmantissa.ISiteRootPlugin, -257)
    return newPage
upgrade.registerUpgrader(customizedPublicPage1To2, 'mantissa_public_customized', 1, 2)

class PublicFrontPage(publicresource.PublicPage):
    implements(ixmantissa.ICustomizable)

    def __init__(self, original, staticContent, forUser=None):
        fragment = publicresource.getLoader('front-page')
        publicresource.PublicPage.__init__(
            self, original, fragment, staticContent, forUser)

    def child_(self, ctx):
        return self

    def customizeFor(self, forUser):
        return PublicFrontPage(self.original, self.staticContent, forUser)

    def renderHTTP(self, ctx):
        if self.username:
            self.original.publicViews += 1
        else:
            self.original.privateViews += 1
        return publicresource.PublicPage.renderHTTP(self, ctx)

class FrontPage(item.Item, website.PrefixURLMixin):
    """
    I am a factory for the dynamic resource L{PublicFrontPage}
    """
    implements(ixmantissa.ISiteRootPlugin)
    typeName = 'mantissa_front_page'
    schemaVersion = 1

    sessioned = True

    publicViews = attributes.integer(default=0)
    privateViews = attributes.integer(default=0)

    prefixURL = attributes.text(default=u'',
                                allowNone=False)


    def createResource(self):
        return PublicFrontPage(self, None)
