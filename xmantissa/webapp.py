# -*- test-case-name: xmantissa.test.test_webapp -*-

"""
This module is the basis for Mantissa-based web applications.  It provides
several basic pluggable application-level features, most notably Powerup-based
integration of the extensible hierarchical navigation system defined in
xmantissa.webnav
"""

import os, sha

from zope.interface import implements

from twisted.python.filepath import FilePath

from epsilon.structlike import record

from axiom.item import Item, declareLegacyItem
from axiom.attributes import text, integer, reference
from axiom.userbase import getAccountNames
from axiom import upgrade
from axiom.dependency import dependsOn

from nevow.rend import Page, NotFound
from nevow import livepage, athena
from nevow.inevow import IRequest, IResource, IQ
from nevow import tags as t
from nevow import url, static

from xmantissa.publicweb import CustomizedPublicPage
from xmantissa.website import PrefixURLMixin, JUST_SLASH, WebSite
from xmantissa.webtheme import getInstalledThemes, getAllThemes
from xmantissa.webnav import getTabs, getSelectedTab, setTabURLs
from xmantissa._webidgen import genkey, storeIDToWebID, webIDToStoreID
from xmantissa.fragmentutils import dictFillSlots
from xmantissa.offering import getInstalledOfferings

from xmantissa.ixmantissa import INavigableFragment, INavigableElement,\
    ISiteRootPlugin, IWebTranslator, IStaticShellContent

from xmantissa.webgestalt import AuthenticationApplication
from xmantissa.prefs import PreferenceAggregator, DefaultPreferenceCollection
from xmantissa.search import SearchAggregator

def _reorderForPreference(themeList, preferredThemeName):
    """
    Re-order the input themeList according to the preferred theme.

    Returns None.
    """
    for t in themeList:
        if preferredThemeName == t.themeName:
            themeList.remove(t)
            themeList.insert(0,t)
            return

class _WebIDFormatException(TypeError):
    """
    An inbound web ID was not formatted as expected.
    """

class NavMixin(object):

    fragmentName = 'main'
    username = None
    searchPattern = None

    def __init__(self, webapp, pageComponents):
        self.webapp = webapp
        self.pageComponents = pageComponents
        setTabURLs(self.pageComponents.navigation, webapp)

    def getDocFactory(self, fragmentName, default=None):
        return self.webapp.getDocFactory(fragmentName, default)

    def render_content(self, ctx, data):
        raise NotImplementedError("implement render_context in subclasses")

    def render_appNavigation(self, ctx, data):
        selectedTab = getSelectedTab(self.pageComponents.navigation,
                                     url.URL.fromContext(ctx))

        getp = IQ(self.docFactory).onePattern

        for tab in self.pageComponents.navigation:
            if tab == selectedTab or selectedTab in tab.children:
                p = 'selected-app-tab'
                contentp = 'selected-tab-contents'
            else:
                p = 'app-tab'
                contentp = 'tab-contents'

            yield dictFillSlots(getp(p),
                    {'name': tab.name,
                     'tab-contents': getp(contentp).fillSlots('href', tab.linkURL)})

    def render_navigation(self, ctx, data):
        getp = IQ(self.docFactory).onePattern

        def fillSlots(tabs):
            for tab in tabs:
                if tab.children:
                    kids = getp('subtabs').fillSlots('kids', fillSlots(tab.children))
                else:
                    kids = ''

                yield dictFillSlots(getp('tab'), dict(href=tab.linkURL,
                                                      name=tab.name,
                                                      kids=kids))

        return fillSlots(self.pageComponents.navigation)

    def render_title(self, ctx, data):
        return ctx.tag[self.__class__.__name__]

    def render_search(self, ctx, data):
        searchAggregator = self.pageComponents.searchAggregator

        if searchAggregator is None or not searchAggregator.providers():
            return ''
        return IQ(self.docFactory).patternGenerator("search")()

    def render_searchFormAction(self, ctx, data):
        searchAggregator = self.pageComponents.searchAggregator

        if searchAggregator is None or not searchAggregator.providers():
            action = ''
        else:
            action = self.webapp.linkTo(searchAggregator.storeID)

        return ctx.tag.fillSlots('form-action', action)

    def render_username(self, ctx, data):
        if self.username is None:
            for (user, domain) in getAccountNames(self.webapp.store):
                self.username = '%s@%s' % (user, domain)
                break
            else:
                self.username = 'nobody@noplace'
        return ctx.tag[self.username]

    def data_settingsLink(self, ctx, data):
        return self.webapp.linkTo(self.pageComponents.settings.storeID)

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
        title = getattr(self.fragment, 'title', None)
        if not title:
            title = 'Divmod'
        return ctx.tag[title]

    def render_content(self, ctx, data):
        return ctx.tag[self.fragment]

class GenericNavigationPage(FragmentWrapperMixin, Page, NavMixin):
    def __init__(self, webapp, fragment, pageComponents):
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, pageComponents)
        FragmentWrapperMixin.__init__(self, fragment, pageComponents)


class GenericNavigationLivePage(FragmentWrapperMixin, livepage.LivePage, NavMixin):
    def __init__(self, webapp, fragment, pageComponents):
        livepage.LivePage.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, pageComponents)
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



_moduleToHash = {}
_hashToFile = {}
class GenericNavigationAthenaPage(athena.LivePage, FragmentWrapperMixin, NavMixin):
    def __init__(self, webapp, fragment, pageComponents):

        userStore = webapp.store
        siteStore = userStore.parent
        self.website = IResource(siteStore)

        athena.LivePage.__init__(
            self,
            getattr(fragment, 'iface', None),
            fragment,
            jsModuleRoot=None,
            transportRoot=url.root.child('live'),
            docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, pageComponents)
        FragmentWrapperMixin.__init__(self, fragment, pageComponents)


    def _setJSModuleRoot(self, ctx):
        req = IRequest(ctx)
        hostname = req.getHeader('host')
        root = self.website.encryptedRoot(hostname)
        if root is None:
            root = url.URL.fromString('/')
        self.jsModuleRoot = root.child('private').child('jsmodule')


    def renderHTTP(self, ctx):
        """
        Capture the value of the C{Host} header for this request so that we can
        generate URLs with it later on during the page render.
        """
        self._setJSModuleRoot(ctx)
        return super(GenericNavigationAthenaPage, self).renderHTTP(ctx)


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


    def getJSModuleURL(self, moduleName):
        """
        Retrieve an URL at which the given module can be found.

        The default L{athena.LivePage} behavior is overridden here to give each
        module a permanent, unique, totally cachable URL based on its named and
        its contents.  This lets browser skip any requests for this module
        after the first as long as it hasn't changed, and forces it to
        re-request it as soon as it changes.
        """
        fp = FilePath(self.jsModules.mapping[moduleName])
        lastHash, lastTime = _moduleToHash.get(moduleName, (None, 0))
        if lastTime != fp.getmtime():
            thisHash = sha.new(fp.open().read()).hexdigest()
            _moduleToHash[moduleName] = (fp.getmtime(), thisHash)
            _hashToFile[thisHash] = fp.path
        else:
            thisHash = lastHash

        return self.jsModuleRoot.child(thisHash).child(moduleName)


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



class HashedJSModuleNames(athena.JSModules):
    """
    An Athena module-serving resource which handles hashed names instead of
    regular module names.
    """
    def resourceFactory(self, fileName):
        """
        Retrieve an L{inevow.IResource} to render the contents of the given
        file.

        Override the default behavior to return a resource which can be cached
        for a long dang time.
        """
        return static.Data(
            file(fileName).read(),
            'text/javascript',
            expires=(60 * 60 * 24 * 365 * 5))



class PrivateRootPage(Page, NavMixin):
    addSlash = True

    def __init__(self, webapp, pageComponents):
        self.webapp = webapp
        Page.__init__(self, docFactory=webapp.getDocFactory('shell'))
        NavMixin.__init__(self, webapp, pageComponents)

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

    def child_jsmodule(self, ctx):
        """
        Retrieve a resource with JavaScript modules as child resources.
        """
        return HashedJSModuleNames(_hashToFile)

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
        return pageClass(self.webapp, fragment, self.pageComponents)


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

    implements(ISiteRootPlugin, IWebTranslator)

    powerupInterfaces = (IWebTranslator,)

    typeName = 'private_web_application'
    schemaVersion = 3


    preferredTheme = text()
    hitCount = integer(default=0)
    privateKey = integer()

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

    def __init__(self, **kw):
        super(PrivateApplication, self).__init__(**kw)
        gk = genkey()
        self.privateKey = gk

    def getPageComponents(self):
        navigation = getTabs(self.store.powerupsFor(INavigableElement))

        staticShellContent = IStaticShellContent(self.store, None)

        return _PageComponents(navigation,
                               self.searchAggregator,
                               staticShellContent,
                               self.store.findFirst(PreferenceAggregator),
                               getInstalledThemes(self.store.parent))

    def createResource(self):
        return PrivateRootPage(self, self.getPageComponents())

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


    def getDocFactory(self, fragmentName, default=None):
        l = getAllThemes()
        _reorderForPreference(l, self.preferredTheme)
        for t in l:
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

upgrade.registerUpgrader(_upgradePrivateApplication2to3, PrivateApplication.typeName, 2, 3)
