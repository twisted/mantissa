
"""
Support for the public-facing portion of web applications.
"""

from zope.interface import implements

from axiom import item, attributes, userbase, upgrade

from xmantissa import ixmantissa, website

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
        PublicWeb(store=s, prefixURL=u'path/to/my-site', application=mySiteSystemUser
                  ).installOn(s)


    @ivar application: An Item which implements L{ixmantissa.IPublicPage}.
    """
    implements(ixmantissa.ISiteRootPlugin,
               ixmantissa.ICustomizablePublicPage)

    typeName = 'mantissa_public_web'
    schemaVersion = 2

    prefixURL = attributes.text(allowNone=False)
    application = attributes.reference(allowNone=False)

    installedOn = attributes.reference()

    def installOn(self, other):
        """
        Install this as an ISiteRootPlugin.
        """
        super(PublicWeb, self).installOn(other)
        other.powerUp(self, ixmantissa.ICustomizablePublicPage)

    def createResource(self):
        return ixmantissa.IPublicPage(self.application).anonymousResource()

    def getPublicPageFactory(self):
        return ixmantissa.IPublicPage(self.application).getPublicPageFactory()

def upgradePublicWeb1To2(oldWeb):
    newWeb = oldWeb.upgradeVersion(
        'mantissa_public_web', 1, 2,
        prefixURL=oldWeb.prefixURL,
        application=oldWeb.application,
        installedOn=oldWeb.installedOn)
    newWeb.installedOn.powerUp(newWeb, ixmantissa.ICustomizablePublicPage)
    return newWeb
upgrade.registerUpgrader(upgradePublicWeb1To2, 'mantissa_public_web', 1, 2)

class CustomizedPublicPage(item.Item, website.PrefixURLMixin):
    """
    Per-avatar hook at '/' which finds the real public-page and asks
    it to customize itself for a particular user.
    """

    sessioned = True

    typeName = 'mantissa_public_customized'
    schemaVersion = 1

    installedOn = attributes.reference(
        '''The Avatar for which this item will attempt to retrieve a
        customized page.''')

    prefixURL = attributes.text(allowNone=False)

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install CustomizedPublicPage on more than one thing (was installed on %r, tried to install on %r)" % (self.installedOn, other)
        super(CustomizedPublicPage, self).installOn(other)
        self.installedOn = other

    def createResource(self):
        superStore = self.installedOn.store.parent

        cust = ixmantissa.ICustomizablePublicPage(superStore, None)
        if cust is None:
            # There is no public page functionality in this system.
            # Don't give back any resource.
            return None

        ppf = cust.getPublicPageFactory()

        for (username, domain) in userbase.getAccountNames(self.installedOn.store):
            return ppf.resourceForUser('%s@%s' % (username, domain))
        assert False, "This case does not make any sense (How did you log in without having a name?)"
