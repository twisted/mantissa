# -*- test-case-name: xmantissa.test.test_webapp -*-

"""
This module is the basis for Mantissa-based web applications.  It provides
several basic pluggable application-level features, most notably Powerup-based
integration of the extensible hierarchical navigation system defined in
xmantissa.webnav
"""

import os

from zope.interface import implements

from epsilon.structlike import record

from axiom.item import Item, declareLegacyItem
from axiom.attributes import text, integer, reference
from axiom import upgrade
from axiom.dependency import dependsOn
from axiom.userbase import getAccountNames

from nevow.rend import Page, NotFound
from nevow import livepage, athena
from nevow.inevow import IRequest, IResource
from nevow import tags as t
from nevow import url

from xmantissa.publicweb import CustomizedPublicPage, renderShortUsername

from xmantissa.website import PrefixURLMixin, JUST_SLASH, WebSite, APIKey
from xmantissa.website import MantissaLivePage
from xmantissa.webtheme import getInstalledThemes
from xmantissa.webnav import getTabs, startMenu, settingsLink, applicationNavigation

from xmantissa._webidgen import genkey, storeIDToWebID, webIDToStoreID
from xmantissa.offering import getInstalledOfferings

from xmantissa.ixmantissa import (INavigableFragment, INavigableElement,
                                  ISiteRootPlugin, IWebTranslator,
                                  IStaticShellContent, ITemplateNameResolver)

from xmantissa.webgestalt import AuthenticationApplication
from xmantissa.prefs import PreferenceAggregator, DefaultPreferenceCollection
from xmantissa.search import SearchAggregator


def _reorderForPreference(themeList, preferredThemeName):
    """
    Re-order the input themeList according to the preferred theme.

    Returns None.
    """
    for theme in themeList:
        if preferredThemeName == theme.themeName:
            themeList.remove(theme)
            themeList.insert(0, theme)
            return

class _WebIDFormatException(TypeError):
    """
    An inbound web ID was not formatted as expected.
    """

class _ShellRenderingMixin(object):
    fragmentName = 'main'
    searchPattern = None

    def __init__(self, resolver, translator, pageComponents, username):
        self.resolver = resolver
        self.translator = translator
        self.pageComponents = pageComponents
        self.username = username


    def getDocFactory(self, fragmentName, default=None):
        """
        Retrieve a Nevow document factory for the given name. This
        implementation merely defers to the underlying L{PrivateApplication}.

        @param fragmentName: a short string that names a fragment template.

        @param default: value to be returned if the named template is not
        found.
        """
        return self.webapp.getDocFactory(fragmentName, default)


    def render_content(self, ctx, data):
        raise NotImplementedError("implement render_context in subclasses")

    def render_title(self, ctx, data):
        return ctx.tag[self.__class__.__name__]

    def render_head(self, ctx, data):
        return ctx.tag

    def render_header(self, ctx, data):
        staticShellContent = self.pageComponents.staticShellContent
        if staticShellContent is None:
            return ctx.tag
        header = staticShellContent.getHeader()
        if header is not None:
            return ctx.tag[header]
        else:
            return ctx.tag


    def render_startmenu(self, ctx, data):
        """
        Add start-menu style navigation to the given tag.

        @see {xmantissa.webnav.startMenu}
        """
        return startMenu(
            self.translator, self.pageComponents.navigation, ctx.tag)


    def render_settingsLink(self, ctx, data):
        """
        Add the URL of the settings page to the given tag.

        @see L{xmantissa.webnav.settingsLink}
        """
        return settingsLink(
            self.translator, self.pageComponents.settings, ctx.tag)


    def render_applicationNavigation(self, ctx, data):
        """
        Add primary application navigation to the given tag.

        @see L{xmantissa.webnav.applicationNavigation}
        """
        return applicationNavigation(
            ctx, self.translator, self.pageComponents.navigation)


    def render_urchin(self, ctx, data):
        """
        Render the code for recording Google Analytics statistics, if so
        configured.
        """
        key = APIKey.getKeyForAPI(self.webapp.store.parent, APIKey.URCHIN)
        if key is None:
            return ''
        return ctx.tag.fillSlots('urchin-key', key.apiKey)


    def render_search(self, ctx, data):
        searchAggregator = self.pageComponents.searchAggregator
        if searchAggregator is None or not searchAggregator.providers():
            return ''
        return ctx.tag.fillSlots(
            'form-action', self.translator.linkTo(searchAggregator.storeID))


    def render_username(self, ctx, data):
        return renderShortUsername(ctx, self.username)


    def render_logout(self, ctx, data):
        return ctx.tag


    def render_authenticateLinks(self, ctx, data):
        return ''


    def _getVersions(self):
        versions = []
        for (name, offering) in getInstalledOfferings(self.webapp.store.parent).iteritems():
            if offering.version is not None:
                v = offering.version
                versions.append(str(v).replace(v.package, name))
        return ' '.join(versions)

    def render_footer(self, ctx, data):
        footer = [self._getVersions()]
        staticShellContent = self.pageComponents.staticShellContent
        if staticShellContent is not None:
            f = staticShellContent.getFooter()
            if f is not None:
                footer.append(f)
        return ctx.tag[footer]

INSPECTROFY = os.environ.get('MANTISSA_DEV')

class FragmentWrapperMixin:
    def __init__(self, fragment, pageComponents):
        self.fragment = fragment
        fragment.page = self
        self.pageComponents = pageComponents

    def beforeRender(self, ctx):
        return getattr(self.fragment, 'beforeRender', lambda x: None)(ctx)

    def render_introspectionWidget(self, ctx, data):
        "Until we have eliminated everything but GenericAthenaLivePage"
        if INSPECTROFY:
            return ctx.tag['No debugging on crap-ass bad pages']
        else:
            return ''

    def render_head(self, ctx, data):
        req = IRequest(ctx)

        userStore = self.webapp.store
        siteStore = userStore.parent
        website = IResource(siteStore)

        l = self.pageComponents.themes
        _reorderForPreference(l, self.webapp.preferredTheme)
        extras = []
        for theme in l:
            extra = theme.head(req, website)
            if extra is not None:
                extras.append(extra)
        extra = self.fragment.head()
        if extra is not None:
            extras.append(extra)
        return ctx.tag[extras]

    def render_title(self, ctx, data):
        """
        Return the current context tag containing C{self.fragment}'s C{title}
        attribute, or "Divmod".
        """
        return ctx.tag[getattr(self.fragment, 'title', 'Divmod')]

    def render_content(self, ctx, data):
        return ctx.tag[self.fragment]

class GenericNavigationPage(FragmentWrapperMixin, Page, _ShellRenderingMixin):
    def __init__(self, webapp, fragment, pageComponents, username):
        self.webapp = webapp
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        _ShellRenderingMixin.__init__(self, webapp, webapp, pageComponents, username)
        FragmentWrapperMixin.__init__(self, fragment, pageComponents)


class GenericNavigationLivePage(FragmentWrapperMixin, livepage.LivePage, _ShellRenderingMixin):
    def __init__(self, webapp, fragment, pageComponents, username):
        self.webapp = webapp
        livepage.LivePage.__init__(self, docFactory=webapp.getDocFactory('shell'))
        _ShellRenderingMixin.__init__(self, webapp, webapp, pageComponents, username)
        FragmentWrapperMixin.__init__(self, fragment, pageComponents)

    # XXX TODO: support live nav, live fragments somehow
    def render_head(self, ctx, data):
        ctx.tag[t.invisible(render=t.directive("liveglue"))]
        return FragmentWrapperMixin.render_head(self, ctx, data)

    def goingLive(self, ctx, client):
        getattr(self.fragment, 'goingLive', lambda x, y: None)(ctx, client)

    def locateHandler(self, ctx, path, name):
        handler = getattr(self.fragment, 'locateHandler', None)

        if handler is None:
            return getattr(self.fragment, 'handle_' + name)
        else:
            return handler(ctx, path, name)



class GenericNavigationAthenaPage(MantissaLivePage,
                                  FragmentWrapperMixin,
                                  _ShellRenderingMixin):
    """
    This class provides the generic navigation elements for surrounding all
    pages navigated under the /private/ namespace.
    """
    def __init__(self, webapp, fragment, pageComponents, username):
        """
        Top-level container for Mantissa application views.

        @param webapp: a C{PrivateApplication}.
        @param fragment: The C{Element} or C{Fragment} to display as content.
        @param pageComponents a C{_PageComponent}.

        This page draws its HTML from the 'shell' template in the preferred
        theme for the store.  If loaded in a browser that does not support
        Athena, the page provided by the 'athena-unsupported' template will be
        displayed instead.

        @see: L{PrivateApplication.preferredTheme}
        """
        self.webapp = webapp
        userStore = webapp.store
        siteStore = userStore.parent

        MantissaLivePage.__init__(
            self, IResource(siteStore),
            getattr(fragment, 'iface', None),
            fragment,
            jsModuleRoot=None,
            docFactory=webapp.getDocFactory('shell'))
        _ShellRenderingMixin.__init__(self, webapp, webapp, pageComponents, username)
        FragmentWrapperMixin.__init__(self, fragment, pageComponents)
        self.unsupportedBrowserLoader = (webapp
                                         .getDocFactory("athena-unsupported"))


    def beforeRender(self, ctx):
        """
        Call the C{beforeRender} implementations on L{MantissaLivePage} and
        L{FragmentWrapperMixin}.
        """
        MantissaLivePage.beforeRender(self, ctx)
        return FragmentWrapperMixin.beforeRender(self, ctx)


    def render_head(self, ctx, data):
        ctx.tag[t.invisible(render=t.directive("liveglue"))]
        return FragmentWrapperMixin.render_head(self, ctx, data)


    def render_introspectionWidget(self, ctx, data):
        if INSPECTROFY:
            f = athena.IntrospectionFragment()
            f.setFragmentParent(self)
            return ctx.tag[f]
        else:
            return ''


    def locateChild(self, ctx, segments):
        res = NotFound

        if hasattr(self.fragment, 'locateChild'):
            res = self.fragment.locateChild(ctx, segments)

        if res is NotFound:
            try:
                self.webapp.fromWebID(segments[0])
            except TypeError:
                pass
            else:
                res = (self.webapp.createResource(), segments)

        if res is NotFound:
            res = super(GenericNavigationAthenaPage, self).locateChild(ctx, segments)

        return res




class PrivateRootPage(Page, _ShellRenderingMixin):
    """
    L{PrivateRootPage} is the resource present for logged-in users at
    "/private", providing a direct interface to the objects located in the
    user's personal user-store.

    It is created by L{PrivateApplication.createResource}.
    """
    addSlash = True

    def __init__(self, webapp, pageComponents, username):
        self.webapp = webapp
        self.username = username
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        _ShellRenderingMixin.__init__(self, webapp, webapp, pageComponents, username)

    def child_(self, ctx):
        navigation = self.pageComponents.navigation
        if not navigation:
            return self
        # /private/XXXX ->
        click = self.webapp.linkTo(navigation[0].storeID)
        return url.URL.fromContext(ctx).click(click)

    def render_content(self, ctx, data):
        return """
        You have no default root page set, and no navigation plugins installed.  I
        don't know what to do.
        """


    def render_title(self, ctx, data):
        return ctx.tag['Private Root Page (You Should Not See This)']


    def childFactory(self, ctx, name):
        try:
            o = self.webapp.fromWebID(name)
        except _WebIDFormatException:
            return None
        if o is None:
            return None
        res = IResource(o, None)
        if res is not None:
            return res
        fragment = INavigableFragment(o, None)
        if fragment is None:
            return None
        if fragment.fragmentName is not None:
            fragDocFactory = self.webapp.getDocFactory(fragment.fragmentName, None)
            if fragDocFactory is not None:
                fragment.docFactory = fragDocFactory
        if fragment.docFactory is None:
            raise RuntimeError("%r (fragment name %r) has no docFactory" % (fragment, fragment.fragmentName))

        if isinstance(fragment, (athena.LiveFragment, athena.LiveElement)):
            pageClass = GenericNavigationAthenaPage
        else:
            pageClass = {False: GenericNavigationPage,
                         True: GenericNavigationLivePage}.get(fragment.live)
        return pageClass(self.webapp, fragment, self.pageComponents, self.username)


class _PageComponents(record('navigation searchAggregator staticShellContent settings themes')):
    """
    I encapsulate various plugin objects that have some say
    in determining the available functionality on a given page
    """
    pass

class PrivateApplication(Item, PrefixURLMixin):
    """
    This is the root of a private, navigable web application.  It is designed
    to be installed on avatar stores after installing WebSite.

    To plug into it, install powerups of the type INavigableElement on the
    user's store.  Their tabs will be retrieved and items that are part of
    those powerups will be linked to; provide adapters for said items to either
    INavigableFragment or IResource.

    Note: IResource adapters should be used sparingly, for example, for
    specialized web resources which are not 'nodes' within the application; for
    example, that need to set a custom content/type or that should not display
    any navigation elements because they will be displayed only within IFRAME
    nodes.  Do _NOT_ use IResource adapters to provide a customized
    look-and-feel; instead use mantissa themes.  (XXX document webtheme.py more
    thoroughly)

    @ivar preferredTheme: A C{unicode} string naming the preferred theme for
    this application.  Templates and suchlike will be looked up for this theme
    first.

    @ivar hitCount: Number of page loads of this application.

    @ivar privateKey: A random integer used to deterministically but
    unpredictably perturb link generation to avoid being the target of XSS
    attacks.

    @ivar privateIndexPage: A reference to the Item whose IResource or
    INavigableFragment adapter will be displayed on login and upon viewing the
    'root' page, /private/.
    """

    implements(ISiteRootPlugin, IWebTranslator, ITemplateNameResolver)

    powerupInterfaces = (IWebTranslator, ITemplateNameResolver)

    typeName = 'private_web_application'
    schemaVersion = 4

    preferredTheme = text()
    hitCount = integer(default=0)
    privateKey = integer(defaultFactory=genkey)

    website = dependsOn(WebSite)

    customizedPublicPage = dependsOn(CustomizedPublicPage)
    authenticationApplication = dependsOn(AuthenticationApplication)
    preferenceAggregator = dependsOn(PreferenceAggregator)
    defaultPreferenceCollection = dependsOn(DefaultPreferenceCollection)
    searchAggregator = dependsOn(SearchAggregator)

    #XXX Nothing ever uses this
    privateIndexPage = reference()

    prefixURL = 'private'

    sessioned = True
    sessionless = False

    def getPageComponents(self):
        navigation = getTabs(self.store.powerupsFor(INavigableElement))

        staticShellContent = IStaticShellContent(self.store, None)

        return _PageComponents(navigation,
                               self.searchAggregator,
                               staticShellContent,
                               self.store.findFirst(PreferenceAggregator),
                               getInstalledThemes(self.store.parent))


    def _getUsername(self):
        """
        Return a localpart@domain style string naming the owner of our store.

        @rtype: C{unicode}
        """
        for (l, d) in getAccountNames(self.store):
            return l + u'@' + d


    def createResource(self):
        return PrivateRootPage(self, self.getPageComponents(), self._getUsername())


    # ISiteRootPlugin
    def resourceFactory(self, segments):
        if segments == JUST_SLASH:
            return self.createResource(), JUST_SLASH
        else:
            return super(PrivateApplication, self).resourceFactory(segments)


    # IWebTranslator
    def linkTo(self, obj):
        # currently obj must be a storeID, but other types might come eventually
        return '/%s/%s' % (self.prefixURL, storeIDToWebID(self.privateKey, obj))

    def linkToWithActiveTab(self, childItem, parentItem):
        """
        Return a URL which will point to the web facet of C{childItem},
        with the selected nav tab being the one that represents C{parentItem}
        """
        return self.linkTo(parentItem.storeID) + '/' + self.toWebID(childItem)

    def linkFrom(self, webid):
        return webIDToStoreID(self.privateKey, webid)

    def fromWebID(self, webID):
        storeID = self.linkFrom(webID)
        if storeID is None:
            # This is not a very good interface, but I don't want to change the
            # calling code right now as I'm neither confident in its test
            # coverage nor looking to go on a test-writing rampage through this
            # code for a minor fix.
            raise _WebIDFormatException("%r didn't look like a webID" % (webID,))
        webitem = self.store.getItemByID(storeID, None)
        return webitem

    def toWebID(self, item):
        return storeIDToWebID(self.privateKey, item.storeID)

    #ITemplateNameResolver
    def getDocFactory(self, fragmentName, default=None):
        """
        Retrieve a Nevow document factory for the given name.

        @param fragmentName: a short string that names a fragment template.

        @param default: value to be returned if the named template is not
        found.
        """
        themes = getInstalledThemes(self.store.parent)
        _reorderForPreference(themes, self.preferredTheme)
        for t in themes:
            fact = t.getDocFactory(fragmentName, None)
            if fact is not None:
                return fact
        return default

declareLegacyItem(PrivateApplication.typeName, 2, dict(
    installedOn = reference(),
    preferredTheme = text(),
    hitCount = integer(default=0),
    privateKey = integer(),
    privateIndexPage = reference(),
    ))

PrivateApplicationV3 = declareLegacyItem(PrivateApplication.typeName, 3, dict(
    preferredTheme=text(),
    hitCount=integer(default=0),
    privateKey=integer(),
    privateIndexPage=reference(),
    customizedPublicPage=reference("dependsOn(CustomizedPublicPage)"),
    authenticationApplication=reference("dependsOn(AuthenticationApplication)"),
    preferenceAggregator=reference("dependsOn(PreferenceAggregator)"),
    defaultPreferenceCollection=reference("dependsOn(DefaultPreferenceCollection)"),
    searchAggregator=reference("dependsOn(SearchAggregator)"),
    website=reference(),
    ))

def upgradePrivateApplication1To2(oldApp):
    newApp = oldApp.upgradeVersion(
        'private_web_application', 1, 2,
        installedOn=oldApp.installedOn,
        preferredTheme=oldApp.preferredTheme,
        hitCount=oldApp.hitCount,
        privateKey=oldApp.privateKey,
        privateIndexPage=oldApp.privateIndexPage)
    newApp.store.powerup(newApp.store.findOrCreate(
        CustomizedPublicPage), ISiteRootPlugin, -257)
    return newApp

upgrade.registerUpgrader(upgradePrivateApplication1To2, 'private_web_application', 1, 2)

def _upgradePrivateApplication2to3(old):
    pa = old.upgradeVersion(PrivateApplication.typeName, 2, 3,
        preferredTheme=old.preferredTheme,
        hitCount=old.hitCount,
        privateKey=old.privateKey,
        privateIndexPage=old.privateIndexPage)
    pa.customizedPublicPage = old.store.findOrCreate(CustomizedPublicPage)
    pa.authenticationApplication = old.store.findOrCreate(AuthenticationApplication)
    pa.preferenceAggregator = old.store.findOrCreate(PreferenceAggregator)
    pa.defaultPreferenceCollection = old.store.findOrCreate(DefaultPreferenceCollection)
    pa.searchAggregator = old.store.findOrCreate(SearchAggregator)
    pa.website = old.store.findOrCreate(WebSite)
    return pa

upgrade.registerUpgrader(_upgradePrivateApplication2to3, PrivateApplication.typeName, 2, 3)

def upgradePrivateApplication3to4(old):
    """
    Upgrade L{PrivateApplication} from schema version 3 to schema version 4.

    Copy all existing attributes to the new version and use the
    L{PrivateApplication} to power up the item it is installed on for
    L{ITemplateNameResolver}.
    """
    new = old.upgradeVersion(
        PrivateApplication.typeName, 3, 4,
        preferredTheme=old.preferredTheme,
        hitCount=old.hitCount,
        privateKey=old.privateKey,
        website=old.website,
        customizedPublicPage=old.customizedPublicPage,
        authenticationApplication=old.authenticationApplication,
        preferenceAggregator=old.preferenceAggregator,
        defaultPreferenceCollection=old.defaultPreferenceCollection,
        searchAggregator=old.searchAggregator)
    # Almost certainly this would be more correctly expressed as
    # installedOn(new).powerUp(...), however the 2 to 3 upgrader failed to
    # translate the installedOn attribute to state which installedOn can
    # recognize, consequently installedOn(new) will return None for an item
    # which was created at schema version 2 or earlier.  It's not worth dealing
    # with this inconsistency, since PrivateApplication is always only
    # installed on its store. -exarkun
    new.store.powerUp(new, ITemplateNameResolver)
    return new

upgrade.registerUpgrader(upgradePrivateApplication3to4, PrivateApplication.typeName, 3, 4)
