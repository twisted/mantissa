# -*- test-case-name: xmantissa.test.test_publicweb -*-

"""
This module contains code for the publicly-visible areas of a Mantissa
server's web interface.
"""

from warnings import warn

from zope.interface import implements

from twisted.internet import defer
from twisted.python import util

from nevow import rend, tags, inevow, static
from nevow.inevow import IRequest, IResource
from nevow.url import URL

from axiom import item, attributes, upgrade, userbase

from xmantissa import ixmantissa, website, offering
from xmantissa.webtheme import getLoader, getInstalledThemes
from xmantissa.ixmantissa import IStaticShellContent
from xmantissa.webnav import startMenu, settingsLink, applicationNavigation


def _getLoader(store, fragmentName, getInstalledThemes=getInstalledThemes):
    """
    This is a temporary function to be used instead of
    xmantissa.webtheme.getLoader, as that is sometimes broken and will be
    deprecated soonish. _getLoader is a quick-fix until we have full support
    for ITemplateNameResolver. See tickets #2343, #2344, and #2345.
    """
    loader = None
    for theme in getInstalledThemes(store):
        loader = theme.getDocFactory(fragmentName)
        if loader is not None:
            return loader
    if loader is None:
        raise RuntimeError("No loader for %r anywhere" % (fragmentName,))



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

    prefixURL = attributes.text(
        doc="""
        The prefix of the URL where objects represented by this fixture will
        appear.  For the front page this is u'', for other pages it is their
        respective URLs.
        """, allowNone=False)

    application = attributes.reference(
        doc="""
        An Item which is adaptable to L{ixmantissa.IPublicPage}.
        """,
        allowNone=False)

    installedOn = attributes.reference(
        doc="""
        """)

    sessioned = attributes.boolean(
        doc="""
        Will this resource be provided to clients with a session?  Defaults to
        False.
        """,
        default=False)

    sessionless = attributes.boolean(
        doc="""
        Will this resource be provided without a session to clients without a
        session?  Defaults to False.
        """,
        default=False)


    def resourceFactory(self, segments):
        """
        Reserve names which begin with '__' for the framework (such as __login__,
        __logout__, __session__, etc), but delegate everything else to
        PrefixURLMixin (and createResource) as usual.
        """
        if not segments[0].startswith('__'):
            return super(PublicWeb, self).resourceFactory(segments)
        return None


    def createResource(self):
        """
        When invoked by L{PrefixURLMixin}, adapt my application object to
        L{IPublicPage} and call C{getResource} on it.
        """
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



class _CustomizingResource(object):
    """
    _CustomizingResource is a wrapping resource used to implement
    CustomizedPublicPage.

        There is an implementation assumption here, which is that the top
        _CustomizingResource is always at "/", and locateChild will always be
        invoked at least once.  If this doesn't hold, this render method might
        be invoked on the top level _CustomizingResource, which would cause it
        to be rendered without customization.  If you're going to use this
        class directly for some reason, please keep this in mind.
    """
    implements(inevow.IResource)

    def __init__(self, topResource, forWho):
        """
        Create a _CustomizingResource.

        @param topResource: an L{inevow.IResource} provider, who may also
        provide L{ixmantissa.ICustomizable} if it wishes to be customized.

        @param forWho: the external ID of the currently logged-in user.
        @type forWho: unicode
        """
        self.currentResource = topResource
        self.forWho = forWho


    def locateChild(self, ctx, path):
        """
        Return a Deferred which will fire with the customized version of the
        resource being located.
        """
        D = defer.maybeDeferred(
            self.currentResource.locateChild, ctx, path)

        def finishLocating((nextRes, nextPath)):
            custom = ixmantissa.ICustomizable(nextRes, None)
            if custom is not None:
                return (custom.customizeFor(self.forWho), nextPath)
            self.currentResource = nextRes
            if nextRes is None:
                return (nextRes, nextPath)
            return (_CustomizingResource(nextRes, self.forWho), nextPath)

        return D.addCallback(finishLocating)


    def renderHTTP(self, ctx):
        """
        Render the resource I was provided at construction time.
        """
        if self.currentResource is None:
            return rend.FourOhFour()
        return self.currentResource # nevow will automatically adapt to
                                    # IResource and call rendering methods.


class CustomizedPublicPage(item.Item):
    """
    A CustomizedPublicPage is a powerup for users which is installed on their
    stores at the URL '/'.  It finds the real site's public-page and asks it to
    customize itself for the user that its store belongs to.

    This works because when users are logged in, their top level resource is
    their own store, and so this powerup has a chance to intercept any hit to
    any URL on the entire site before it is actually rendered to the user.

    While this technique for logging in requires a user store, the only
    information it communicates to other stores is a string via the
    C{customizeFor} method, so other implementations of this technique could
    simply be drawing that string from a cookie, from OpenID, etc.  Those
    interested in implementing distributed security mechanisms for mantissa
    should familiarize themselves with this code.
    """

    typeName = 'mantissa_public_customized'
    schemaVersion = 2

    installedOn = attributes.reference(
        doc="""
        The Avatar for which this item will attempt to retrieve a customized
        page.
        """)

    powerupInterfaces = [(ixmantissa.ISiteRootPlugin, -257)]

    def resourceFactory(self, segments):
        """
        Implementation of L{ixmantissa.ISiteRootPlugin.resourceFactory}.

        This will look in this powerup's store to discover the currently active
        username, look for the parent store's top-level resource (the top-level
        resource of the site) and then return a L{_CustomizingResource} which
        wraps that resource and customizes any of the customizable children.

        @return: a 2-tuple of a customizing resource and the given list of
        segments, or, if no resource is provided by the site store, None.
        """
        topResource = inevow.IResource(self.store.parent, None)
        if topResource is not None:
            for resource, domain in userbase.getAccountNames(self.store):
                username = '%s@%s' % (resource, domain)
                break
            else:
                username = None
            return (_CustomizingResource(topResource, username), segments)
        return None



def customizedPublicPage1To2(oldPage):
    newPage = oldPage.upgradeVersion(
        'mantissa_public_customized', 1, 2,
        installedOn=oldPage.installedOn)
    newPage.installedOn.powerDown(newPage, ixmantissa.ISiteRootPlugin)
    newPage.installedOn.powerUp(newPage, ixmantissa.ISiteRootPlugin, -257)
    return newPage
upgrade.registerUpgrader(customizedPublicPage1To2, 'mantissa_public_customized', 1, 2)



class PublicPageMixin(object):
    """
    Mixin for use by C{Page} or C{LivePage} subclasses that are visible to
    unauthenticated clients.

    @ivar needsSecure: whether this page requires SSL to be rendered.
    """
    fragment = None
    username = None
    needsSecure = False

    def renderHTTP(self, ctx):
        """
        Issue a redirect to an HTTPS URL for this resource if one
        exists and the page demands it.
        """
        req = inevow.IRequest(ctx)
        securePort = inevow.IResource(self.store).securePort
        if self.needsSecure and not req.isSecure() and securePort is not None:
            return URL.fromContext(
                ctx).secure(port=securePort.getHost().port)
        else:
            return super(PublicPageMixin, self).renderHTTP(ctx)


    def _getViewerPrivateApplication(self):
        ls = self.store.findUnique(userbase.LoginSystem)
        substore = ls.accountByAddress(*self.username.split('@')).avatars.open()
        from xmantissa.webapp import PrivateApplication
        return substore.findUnique(PrivateApplication)


    def render_authenticateLinks(self, ctx, data):
        """
        For unauthenticated users, add login and signup links to the given tag.
        For authenticated users, remove the given tag from the output.

        When necessary, the I{signup-link} pattern will be loaded from the tag.
        Each copy of it will have I{prompt} and I{url} slots filled.  The list
        of copies will be added as children of the tag.
        """
        if self.username is not None:
            return ''
        # there is a circular import here which should probably be avoidable,
        # since we don't actually need signup links on the signup page.  on the
        # other hand, maybe we want to eventually put those there for
        # consistency.  for now, this import is easiest, and although it's a
        # "friend" API, which I dislike, it doesn't seem to cause any real
        # problems...  -glyph
        from xmantissa.signup import _getPublicSignupInfo

        IQ = inevow.IQ(ctx.tag)
        signupPattern = IQ.patternGenerator('signup-link')

        signups = []
        for (prompt, url) in _getPublicSignupInfo(self.store):
            signups.append(signupPattern.fillSlots(
                    'prompt', prompt).fillSlots(
                    'url', url))

        return ctx.tag[signups]


    def render_startmenu(self, ctx, data):
        """
        For authenticated users, add the start-menu style navigation to the
        given tag.  For unauthenticated users, remove the given tag from the
        output.

        @see L{xmantissa.webnav.startMenu}
        """
        if self.username is None:
            return ''
        translator = self._getViewerPrivateApplication()
        pageComponents = translator.getPageComponents()
        return startMenu(translator, pageComponents.navigation, ctx.tag)


    def render_settingsLink(self, ctx, data):
        """
        For authenticated users, add the URL of the settings page to the given
        tag.  For unauthenticated users, remove the given tag from the output.
        """
        if self.username is None:
            return ''
        translator = self._getViewerPrivateApplication()
        return settingsLink(
            translator,
            translator.getPageComponents().settings,
            ctx.tag)


    def render_applicationNavigation(self, ctx, data):
        """
        For authenticated users, add primary application navigation to the
        given tag.  For unauthenticated users, remove the given tag from the
        output.

        @see L{xmantissa.webnav.applicationNavigation}
        """
        if self.username is None:
            return ''
        translator = self._getViewerPrivateApplication()
        return applicationNavigation(
            ctx,
            translator,
            translator.getPageComponents().navigation)


    def render_search(self, ctx, data):
        """
        Render some UI for performing searches, if we know about a search
        aggregator.
        """
        if self.username is None:
            return ''
        translator = self._getViewerPrivateApplication()
        searchAggregator = translator.getPageComponents().searchAggregator
        if searchAggregator is None or not searchAggregator.providers():
            return ''
        return ctx.tag.fillSlots(
            'form-action', translator.linkTo(searchAggregator.storeID))


    def render_username(self, ctx, data):
        if self.username is None:
            return ''
        return ctx.tag[self.username]


    def render_logout(self, ctx, data):
        if self.username is None:
            return ''
        return ctx.tag


    def render_title(self, ctx, data):
        """
        Return the current context tag containing C{self.fragment}'s C{title}
        attribute, or "Divmod".
        """
        return ctx.tag[getattr(self.fragment, 'title', 'Divmod')]


    def render_header(self, ctx, data):
        """
        Render any required static content in the header, from the C{staticContent}
        attribute of this page.
        """
        if self.staticContent is None:
            return ctx.tag

        header = self.staticContent.getHeader()
        if header is not None:
            return ctx.tag[header]
        else:
            return ctx.tag


    def render_footer(self, ctx, data):
        """
        Render any required static content in the footer, from the C{staticContent}
        attribute of this page.
        """
        if self.staticContent is None:
            return ctx.tag

        header = self.staticContent.getFooter()
        if header is not None:
            return ctx.tag[header]
        else:
            return ctx.tag


    def render_content(self, ctx, data):
        """
        This renderer, which is used for the visual bulk of the page, provides
        self.fragment renderer.
        """
        return ctx.tag[self.fragment]


    def head(self):
        """
        Override this method to insert additional content into the header.  By
        default, does nothing.
        """
        return None


    def getHeadContent(self, req):
        """
        Retrieve a list of header content from all installed themes on the site
        store.
        """
        website = inevow.IResource(self.store)
        for t in getInstalledThemes(self.store):
            yield t.head(req, website)


    def render_head(self, ctx, data):
        """
        This renderer calculates content for the <head> tag by concatenating the
        values from L{getHeadContent} and the overridden L{head} method.
        """
        req = inevow.IRequest(ctx)
        return ctx.tag[filter(None, list(self.getHeadContent(req)) + [self.head()])]



class PublicPage(PublicPageMixin, rend.Page):
    """
    PublicPage is a utility superclass for implementing static pages which have
    theme support and authentication trimmings.
    """

    def __init__(self, original, store, fragment, staticContent, forUser):
        """
        Create a public page.

        @param original: any object

        @param fragment: a L{rend.Fragment} to display in the content area of
        the page.

        @param staticContent: some stan, to include in the header of the page.

        @param forUser: a string, the external ID of a user to customize for.
        """
        super(PublicPage, self).__init__(original, docFactory=getLoader("shell"))
        self.store = store
        self.fragment = fragment
        self.staticContent = staticContent
        if forUser is not None:
            assert isinstance(forUser, unicode), forUser
        self.username = forUser



class _OfferingsFragment(rend.Fragment):
    """
    This fragment provides the list of installed offerings as a data generator.
    This is used to display the list of app stores on the default front page.
    """
    def __init__(self, original):
        """
        Create an _OfferingsFragment with an item from a site store.

        @param original: a L{FrontPage} item.
        """
        super(_OfferingsFragment, self).__init__(
            original, docFactory=_getLoader(original.store, 'front-page'))


    def data_offerings(self, ctx, data):
        """
        Generate a list of installed offerings.

        @return: a generator of dictionaries mapping 'name' to the name of an
        offering installed on the store.
        """
        for io in self.original.store.query(offering.InstalledOffering):
            pp = ixmantissa.IPublicPage(io.application, None)
            if pp is not None and getattr(pp, 'index', True):
                yield {
                    'name': io.offeringName,
                    }



class PublicFrontPage(PublicPage):
    """
    This is the implementation of the default Mantissa front page.  It renders
    a list of offering names, displays the user's name, and lists signup
    mechanisms.  It also provides various top-level URLs.
    """
    implements(ixmantissa.ICustomizable)

    def __init__(self, original, staticContent, forUser=None):
        """
        Create a PublicFrontPage.

        @param original: a L{FrontPage} item, which we use primarily to get at a Store.

        @param staticContent: additional data to embed in the header.

        @param forUser: an external ID of the logged in user, or None, if the
        user viewing this page is browsing anonymously.
        """
        PublicPage.__init__(
            self, original, original.store, _OfferingsFragment(original),
            staticContent, forUser)


    def locateChild(self, ctx, segments):
        """
        Look up children in the normal manner, but then customize them for the
        authenticated user if they support the L{ICustomizable} interface.  If
        the user is attempting to access a private URL, redirect them.
        """
        result = super(PublicFrontPage, self).locateChild(ctx, segments)
        if result is not rend.NotFound:
            child, segments = result
            if self.username is not None:
                cust = ixmantissa.ICustomizable(child, None)
                if cust is not None:
                    return cust.customizeFor(self.username), segments
            return child, segments

        # If the user is trying to access /private/*, then his session has
        # expired or he is otherwise not logged in. Redirect him to /login,
        # preserving the URL segments, rather than giving him an obscure 404.
        if segments[0] == 'private':
            u = URL.fromContext(ctx).click('/').child('login')
            for seg in segments:
                u = u.child(seg)
            return u, ()

        return rend.NotFound


    def childFactory(self, ctx, name):
        """
        Customize child lookup such that all installed offerings on the site store
        that this page is viewing are given an opportunity to display their own
        page.
        """
        offer = self.original.store.findFirst(
            offering.InstalledOffering,
            offering.InstalledOffering.offeringName == unicode(name, 'ascii'))
        if offer is not None:
            pp = ixmantissa.IPublicPage(offer.application, None)
            if pp is not None:
                return pp.getResource()
        return None


    def child_(self, ctx):
        """
        Return 'self' if the index is requested, since this page can render a
        simple index.
        """
        return self


    def child_Mantissa(self, ctx):
        """
        Serve files from C{xmantissa/static/} at the URL C{/Mantissa}.
        """
        # Cheating!  It *looks* like there's an app store, but there isn't
        # really, because this is the One Store To Bind Them All.
        return static.File(util.sibpath(__file__, "static"))


    def customizeFor(self, forUser):
        """
        Return a customized version of this page for a particular user.

        @param forUser: the external ID of a user.
        """
        return PublicFrontPage(self.original, self.staticContent, forUser)


    def renderHTTP(self, ctx):
        """
        If viewed by a logged in user, redirect them to their application at
        /private.  Otherwise, view the public index page.
        """
        if self.username:
            self.original.publicViews += 1
            return URL.fromContext(ctx).click('/').child('private')
        else:
            self.original.privateViews += 1
            return PublicPage.renderHTTP(self, ctx)



class LoginPage(PublicPage):
    """
    This is the page which presents a 'login' dialog to the user, at "/login".

    This does not perform the actual login, nevow.guard does that, at the URL
    /__login__; this resource merely provides the entry field and redirection
    logic.
    """

    def __init__(self, store, segments=(), arguments=None):
        """
        Create a login page.

        @param store: a site store which contains a WebSite item.

        @param segments: a list of strings.  For example, if you hit
        /login/private/stuff, you want to log in to /private/stuff, and the
        resulting LoginPage will have the segments of ['private', 'stuff']

        @param arguments: A dictionary mapping query argument names to lists of
        values for those arguments (see IRequest.args).
        """
        PublicPage.__init__(self, None, store, _getLoader(store, 'login'),
                            IStaticShellContent(store, None),
                            None)
        self.segments = segments
        if arguments is None:
            arguments = {}
        self.arguments = arguments


    def beforeRender(self, ctx):
        """
        Before rendering this page, identify the correct URL for the login to post
        to, and the error message to display (if any), and fill the 'login
        action' and 'error' slots in the template accordingly.
        """
        url = URL.fromContext(ctx).click('/')

        ws = self.store.findFirst(website.WebSite)

        if ws.securePort is not None:
            url = url.secure(port=ws.securePort.getHost().port)

        url = url.child('__login__')
        for seg in self.segments:
            url = url.child(seg)
        for queryKey, queryValues in self.arguments.iteritems():
            for queryValue in queryValues:
                url = url.add(queryKey, queryValue)

        req = inevow.IRequest(ctx)
        err = req.args.get('login-failure', ('',))[0]

        if 0 < len(err):
            error = inevow.IQ(
                        self.fragment).onePattern(
                                'error').fillSlots('error', err)
        else:
            error = ''

        ctx.fillSlots("login-action", url)
        ctx.fillSlots("error", error)


    def locateChild(self, ctx, segments):
        """
        Return a clone of this page that remembers its segments, so that URLs like
        /login/private/stuff will redirect the user to /private/stuff after
        login has completed.
        """
        arguments = IRequest(ctx).args
        return self.__class__(
            self.store, segments, arguments), ()


    def fromRequest(cls, store, request):
        """
        Return a L{LoginPage} which will present the user with a login prompt.

        @type store: L{Store}
        @param store: A I{site} store.

        @type request: L{nevow.inevow.IRequest}
        @param request: The HTTP request which encountered a need for
            authentication.  This will be effectively re-issued after login
            succeeds.

        @return: A L{LoginPage} and the remaining segments to be processed.
        """
        location = URL.fromRequest(request)
        segments = location.pathList(unquote=True, copy=False)
        segments.append(request.postpath[0])
        return cls(store, segments, request.args)
    fromRequest = classmethod(fromRequest)


class FrontPage(item.Item, website.PrefixURLMixin):
    """
    I am a factory for the dynamic resource L{PublicFrontPage}
    """
    implements(ixmantissa.ISiteRootPlugin)
    typeName = 'mantissa_front_page'
    schemaVersion = 1

    sessioned = True

    publicViews = attributes.integer(
        doc="""
        The number of times this object has been viewed in a public
        (non-authenticated) context.  This includes renderings of the front
        page only.
        """,
        default=0)

    privateViews = attributes.integer(
        doc="""
        The number of times this object has been viewed in a private
        (authenticated) context.  This only counts the number of times users
        have been redirected from "/" to "/private".
        """,
        default=0)

    prefixURL = attributes.text(
        doc="""
        See L{website.PrefixURLMixin}.
        """,
        default=u'',
        allowNone=False)


    def createResource(self):
        """
        Create a L{PublicFrontPage} resource wrapping this object.
        """
        return PublicFrontPage(self, None)



class PublicAthenaLivePage(PublicPageMixin, website.MantissaLivePage):
    """
    PublicAthenaLivePage is a publicly viewable Athena-enabled page which slots
    a single fragment into the center of the page.
    """
    fragment = None
    def __init__(self, store, fragment, staticContent=None, forUser=None,
                 *a, **k):
        """
        Create a PublicAthenaLivePage.

        @param store: a site store containing a L{WebSite}.
        @type store: L{axiom.store.Store}.

        @param fragment: The L{INavigableFragment} provider which will be
        displayed on this page.

        This page draws its HTML from the 'shell' template in the active theme.
        If loaded in a browser that does not support Athena, the page provided
        by the 'athena-unsupported' template will be displayed instead.
        """
        self.store = store
        super(PublicAthenaLivePage, self).__init__(
            IResource(store), docFactory=getLoader('shell'), *a, **k)
        if fragment is not None:
            self.fragment = fragment
            # everybody who calls this has a different idea of what 'fragment'
            # means - let's just be super-lenient for now
            if getattr(fragment, 'setFragmentParent', False):
                fragment.setFragmentParent(self)
            else:
                fragment.page = self
        self.staticContent = staticContent
        if forUser is not None:
            assert isinstance(forUser, unicode), forUser
        self.username = forUser
        resolver = ixmantissa.ITemplateNameResolver(self.store, None)
        if resolver is not None:
            self.unsupportedBrowserLoader = (resolver
                                         .getDocFactory("athena-unsupported"))
        else:
            self.unsupportedBrowserLoader = getLoader("athena-unsupported")


    def render_head(self, ctx, data):
        """
        Put liveglue content into the header of this page to activate it, but
        otherwise delegate to my parent's renderer for <head>.
        """
        ctx.tag[tags.invisible(render=tags.directive('liveglue'))]
        return PublicPageMixin.render_head(self, ctx, data)


    def locateChild(self, ctx, segments):
        """
        Delegate locateChild to my fragment.  Wrap the resulting fragment object in
        a new PublicAthenaLivePage and return it.
        """
        res = rend.NotFound

        if hasattr(self.fragment, 'locateChild'):
            res = self.fragment.locateChild(ctx, segments)

        if res is rend.NotFound:
            res = super(PublicAthenaLivePage, self).locateChild(ctx, segments)

        return res



class PublicNavAthenaLivePage(PublicAthenaLivePage):
    """
    DEPRECATED!  Use PublicAthenaLivePage.

    A L{PublicAthenaLivePage} which optionally includes a menubar and
    navigation if the viewer is authenticated.
    """
    def __init__(self, *a, **kw):
        PublicAthenaLivePage.__init__(self, *a, **kw)
        warn(
            "Use PublicAthenaLivePage instead of PublicNavAthenaLivePage",
            category=DeprecationWarning,
            stacklevel=2)
