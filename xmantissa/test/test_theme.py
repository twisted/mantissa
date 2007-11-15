from zope.interface import implements
from zope.interface import classProvides

from twisted.web import microdom
from twisted.trial.unittest import TestCase
from twisted.python.reflect import qual
from twisted.python.util import sibpath

from nevow.athena import LivePage
from nevow.loaders import stan, xmlstr
from nevow.tags import (
    html, head, body, img, script, link, invisible, directive)
from nevow.context import WovenContext
from nevow.testutil import FakeRequest, AccumulatingFakeRequest as makeRequest
from nevow.flat import flatten
from nevow.inevow import IRequest
from nevow.page import renderer
from nevow.athena import LiveFragment

from axiom.item import Item
from axiom.attributes import integer
from axiom.store import Store
from axiom.substore import SubStore
from axiom.dependency import installOn

from xmantissa.ixmantissa import ITemplateNameResolver
from xmantissa.port import TCPPort
from xmantissa import webtheme
from xmantissa.ixmantissa import ITemplateNameResolver
from xmantissa.webtheme import (
    getAllThemes, getInstalledThemes, MantissaTheme, ThemedFragment,
    ThemedElement, _ThemedMixin, ThemedDocumentFactory)
from xmantissa.website import WebSite
from xmantissa.offering import installOffering
from xmantissa.plugins.baseoff import baseOffering
from zope.interface import implements

from xmantissa.publicweb import PublicAthenaLivePage
from xmantissa.webapp import (GenericNavigationAthenaPage, _PageComponents,
                              PrivateApplication)


class ThemedDocumentFactoryTests(TestCase):
    """
    Tests for the automatic document factory descriptor,
    L{ThemedDocumentFactory}.
    """
    def test_getter(self):
        """
        Retrieving the value of a L{ThemedDocumentFactory} descriptor should
        cause an L{ITemplateNameResolver} to be requested from the supplied
        callable and a loader for the template for the fragment name the
        descriptor was created with to be created and returned.
        """
        docFactory = object()
        loadAttempts = []
        fragmentName = 'abc'
        class Dummy(object):
            class StubResolver(object):
                classProvides(ITemplateNameResolver)
                def getDocFactory(name):
                    loadAttempts.append(name)
                    return docFactory
                getDocFactory = staticmethod(getDocFactory)
            docFactory = ThemedDocumentFactory(fragmentName, 'StubResolver')
        self.assertIdentical(Dummy().docFactory, docFactory)
        self.assertEqual(loadAttempts, [fragmentName])



def testHead(theme):
    """
    Check that the head method of the given theme doesn't explode.
    @param theme: probably an L{xmantissa.webtheme.XHTMLDirectoryTheme}
    """
    store = Store()
    site = WebSite(store=store)
    installOn(site, store)
    port = TCPPort(store=store, portNumber=80, factory=site)
    installOn(port, store)
    flatten(theme.head(makeRequest(), site))



class FakeTheme:
    """
    Stub theme object for template-loader tests.
    """
    implements(ITemplateNameResolver)
    def __init__(self, name, priority):
        self.name = name
        self.priority = priority

    def getDocFactory(self, n, default):
        """
        Doesn't have to return anything meaningful, just something
        recognizable for assertions.
        """
        return [self.name, n]


class FakeOffering:
    def __init__(self, name, priority):
        self.themes = [FakeTheme(name, priority)]

class WebThemeTestCase(TestCase):
    def _render(self, element):
        """
        Put the given L{IRenderer} provider into an L{athena.LivePage} and
        render it.  Return a Deferred which fires with the request object used
        which is an instance of L{nevow.testutil.FakeRequest}.
        """
        p = LivePage(
            docFactory=stan(
                html[
                    head(render=directive('liveglue')),
                    body[
                        invisible(render=lambda ctx, data: element)]]))
        element.setFragmentParent(p)

        ctx = WovenContext()
        req = FakeRequest()
        ctx.remember(req, IRequest)

        d = p.renderHTTP(ctx)
        def rendered(ign):
            p.action_close(None)
            return req
        d.addCallback(rendered)
        return d


    def test_getAllThemesPrioritization(self):
        """
        Test that the L{xmantissa.webtheme.getAllThemes} function returns
        L{ITemplateNameResolver} providers from the installed
        L{xmantissa.ixmantissa.IOffering} plugins in priority order.
        """
        lastPriority = None
        for theme in webtheme.getAllThemes():
            if lastPriority is None:
                lastPriority = theme.priority
            else:
                self.failIf(
                    theme.priority > lastPriority,
                    "Theme out of order: %r" % (theme,))
                lastPriority = theme.priority


    def test_getInstalledThemes(self):
        """
        Test that only themes which belong to offerings installed on a
        particular store are returned by
        L{xmantissa.webtheme.getInstalledThemes}.
        """
        s = Store()
        self.assertEquals(getInstalledThemes(s), [])

        installOffering(s, baseOffering, {})

        installedThemes = getInstalledThemes(s)
        self.assertEquals(len(installedThemes), 1)
        self.failUnless(isinstance(installedThemes[0], MantissaTheme))


    def _defaultThemedRendering(self, cls):
        class ThemedSubclass(cls):
            pass
        d = self._render(ThemedSubclass())
        def rendered(req):
            self.assertIn(
                qual(ThemedSubclass),
                req.v)
            self.assertIn(
                'specified no <code>fragmentName</code> attribute.',
                req.v)
        d.addCallback(rendered)
        return d


    def test_themedFragmentDefaultRendering(self):
        """
        Test that a ThemedFragment which does not override fragmentName is
        rendered with some debugging tips.
        """
        return self._defaultThemedRendering(ThemedFragment)


    def test_themedElementDefaultRendering(self):
        """
        Test that a ThemedElement which does not override fragmentName is
        rendered with some debugging tips.
        """
        return self._defaultThemedRendering(ThemedElement)


    def test_websiteDiscovery(self):
        """
        Test that L{_ThemedMixin.getWebSite} finds the right object whether it
        is wrapped around a user store or the store store.
        """
        siteStore = Store()
        siteSite = WebSite(store=siteStore)
        installOn(siteSite, siteStore)

        subStore = SubStore.createNew(siteStore, ['user']).open()
        subSite = WebSite(store=subStore)
        installOn(subSite, subStore)

        themed = _ThemedMixin()
        themed.store = siteStore
        self.assertIdentical(
            themed.getWebSite(), siteSite,
            "Found the wrong WebSite from the site store.")

        themed = _ThemedMixin()
        themed.store = subStore
        self.assertEquals(
            themed.getWebSite(), siteSite,
            "Found the wrong WebSite from the user store.")

    def test_imageSourceNotRewritten(self):
        """
        Test that an image tag which includes a hostname in its source does not
        have that source rewritten.
        """
        store = Store()
        site = WebSite(store=store, hostname=u'example.com')
        installOn(site, store)

        testElement = ThemedElement()
        testElement.docFactory = stan(img(src='http://example.org/Foo.png'))
        testElement.store = store

        d = self._render(testElement)
        def rendered(req):
            dom = microdom.parseString(req.v)
            img = dom.getElementsByTagName('img')[0]
            self.assertEquals("http://example.org/Foo.png",
                              img.getAttribute('src'))
        d.addCallback(rendered)
        return d


    def _mutate(self, urlString):
        return "%s_mutated" % (urlString,)


    def test_originalImageRendererRespected(self):
        """
        Test that an image tag with a render directive has that directive
        invoked after the URL has been rewritten.
        """
        store = Store()
        site = WebSite(store=store, hostname=u'example.com')
        installOn(site, store)

        class TestElement(ThemedElement):
            def mutate(this, request, tag):
                this.mutated = self._mutate(tag.attributes['src'])
                return tag
            renderer(mutate)

        ele = TestElement()
        ele.docFactory = stan(img(src='/Foo.png', render=directive('mutate')))
        ele.store = store

        d = self._render(ele)
        def rendered(req):
            self.assertEquals(ele.mutated, self._mutate('/Foo.png'))
        d.addCallback(rendered)
        return d


    def test_scriptSourceNotRewritten(self):
        """
        Test that a script tag which includes a hostname in its source does not
        have that source rewritten.
        """
        store = Store()
        site = WebSite(store=store, hostname=u'example.com')
        installOn(site, store)

        testElement = ThemedElement()
        testElement.docFactory = stan(script(src='http://example.org/Foo.js'))
        testElement.store = store

        d = self._render(testElement)
        def rendered(req):
            self.assertIn(
                '<script src="http://example.org/Foo.js"></script>',
                req.v)
        d.addCallback(rendered)
        return d


    def test_originalScriptRendererRespected(self):
        """
        Test that an script tag with a render directive has that directive
        invoked after the URL has been rewritten.
        """
        store = Store()
        site = WebSite(store=store, hostname=u'example.com')
        installOn(site, store)

        class TestElement(ThemedElement):
            def mutate(this, request, tag):
                this.mutated = self._mutate(tag.attributes['src'])
                return tag
            renderer(mutate)

        ele = TestElement()
        ele.docFactory = stan(script(src='/Foo.js', render=directive('mutate')))
        ele.store = store

        d = self._render(ele)
        def rendered(req):
            self.assertEquals(ele.mutated, self._mutate('/Foo.js'))
        d.addCallback(rendered)
        return d


    def test_linkHypertextReferenceNotRewritten(self):
        """
        Test that a link which includes a hostname in its href does not have
        that href rewritten.
        """
        store = Store()
        site = WebSite(store=store, hostname=u'example.com')
        installOn(site, store)

        testElement = ThemedElement()
        testElement.docFactory = stan(link(href='http://example.org/Foo.css'))
        testElement.store = store

        d = self._render(testElement)
        def rendered(req):
            self.assertIn(
                '<link href="http://example.org/Foo.css" />',
                req.v)
        d.addCallback(rendered)
        return d


    def test_originalLinkRendererRespected(self):
        """
        Test that a link tag with a render directive has that directive invoked
        after the URL has been rewritten.
        """
        store = Store()
        site = WebSite(store=store, hostname=u'example.com')
        installOn(site, store)

        class TestElement(ThemedElement):
            def mutate(this, request, tag):
                this.mutated = self._mutate(tag.attributes['href'])
                return tag
            renderer(mutate)

        ele = TestElement()
        ele.docFactory = stan(link(href='/Foo.css', render=directive('mutate')))
        ele.store = store

        d = self._render(ele)
        def rendered(req):
            self.assertEquals(ele.mutated, self._mutate('/Foo.css'))
        d.addCallback(rendered)
        return d


    def test_head(self):
        testHead(MantissaTheme(''))



CUSTOM_MSG = xmlstr('<div>Athena unsupported here</div>')
BASE_MSG =  file(sibpath(__file__,
                         "../themes/base/athena-unsupported.html")
                 ).read().strip()

class StubThemeProvider(Item):
    """
    Trivial implementation of a theme provider, for testing that custom
    Athena-unsupported pages can be used.
    """
    _attribute = integer(doc="exists to pacify Axiom's hunger for attributes")
    implements(ITemplateNameResolver)
    powerupInterfaces = (ITemplateNameResolver,)
    def getDocFactory(self, name):
        """
        Return the page indicating Athena isn't available, if requested.
        """
        if name == 'athena-unsupported':
            return CUSTOM_MSG



class AthenaUnsupported(TestCase):
    """
    Tests for proper treatment of browsers that don't support Athena.
    """
    def test_publicPage(self):
        """
        Test that L{publicpage.PublicAthenaLivePage} supports themeing of
        Athena's unsupported-browser page.
        """
        store = Store()
        installOn(WebSite(store=store), store)
        stp = StubThemeProvider(store=store)
        installOn(stp, store)
        p = PublicAthenaLivePage(store, None)
        self.assertEqual(p.renderUnsupported(None),
                         flatten(CUSTOM_MSG))


    def test_publicPageUncustomized(self):
        """
        Test that L{publicpage.PublicAthenaLivePage} renders something when
        Athena is unsupported, even if there's no customization installed.
        """
        store = Store()
        privapp = PrivateApplication(store=store)
        installOn(privapp, store)
        p = PublicAthenaLivePage(store, None)
        self.assertEqual(p.renderUnsupported(None).replace('\n ', ''),
                         BASE_MSG)


    def test_navPage(self):
        """
        Test that L{webapp.GenericNavigationLivePage} supports themeing
        of Athena's unsupported-browser page.
        """
        s = Store()
        installOn(WebSite(store=s), s)
        s.parent = s
        ss = SubStore.createNew(s, ['athena', 'unsupported'])
        ss = ss.open()
        stp = StubThemeProvider(store=ss)
        installOn(stp, ss)
        p = GenericNavigationAthenaPage(stp,
                                        LiveFragment(),
                                        _PageComponents([], None, None,
                                                        None, None),
                                        None)
        self.assertEqual(p.renderUnsupported(None),
                         flatten(CUSTOM_MSG))


    def test_navPageUncustomized(self):
        """
        Test that L{webapp.GenericNavigationLivePage} renders something when
        Athena is unsupported, even if there's no customization installed.
        """
        s = Store()
        installOn(WebSite(store=s), s)
        s.parent = s
        ss = SubStore.createNew(s, ['athena', 'unsupported'])
        ss = ss.open()
        privapp = PrivateApplication(store=ss)
        installOn(privapp, ss)
        p = GenericNavigationAthenaPage(privapp,
                                        LiveFragment(),
                                        _PageComponents([], None, None,
                                                        None, None),
                                        None)
        self.assertEqual(p.renderUnsupported(None).replace('\n ', ''),
                         BASE_MSG)



class Loader(TestCase):
    def setUp(self):
        self._getAllThemes = webtheme.getAllThemes
        self.gATcalled = 0
        def fakeGetAllThemes():
            self.gATcalled += 1
            return [FakeTheme('foo', 7),
                    FakeTheme('baz', 2)]
        webtheme._loaderCache.clear()
        webtheme.getAllThemes = fakeGetAllThemes

    def tearDown(self):
        webtheme.getAllThemes = self._getAllThemes

    def test_getLoader(self):
        """
        getLoader should search available themes for the named
        template and return it.
        """
        self.assertEquals(webtheme.getLoader('template'),
                          ['foo', 'template'])

    def test_getLoaderCaching(self):
        """
        getLoader should return identical loaders for equal arguments.
        """
        self.assertIdentical(webtheme.getLoader('template'),
                             webtheme.getLoader('template'))
        self.assertEqual(self.gATcalled, 1)



class TestThemeCache(TestCase):
    """
    some tests for L{ThemeCache}.
    """
    def setUp(self):
        """
        Replace L{getOfferings} with a mock method returning some fake
        offerings.
        """
        self._getOfferings = webtheme.getOfferings
        self.called = 0
        def fakeGetOfferings():
            self.called += 1
            return [FakeOffering('foo', 7),
                    FakeOffering('baz', 2),
                    FakeOffering('boz', 5)]

        webtheme.getOfferings = fakeGetOfferings

    def tearDown(self):
        """
        Reset L{getOfferings} to its original value.
        """
        webtheme.getOfferings = self._getOfferings


    def test_getAllThemes(self):
        """
        C{getAllThemes} should collect themes from available
        offerings, and only call C{getOfferings} once no matter how
        many times it's called.
        """
        tc = webtheme.ThemeCache()
        ths = tc.getAllThemes()
        self.assertEqual([theme.name for theme in ths],
                         ['foo', 'boz', 'baz'])
        tc.getAllThemes()
        self.assertEqual(self.called, 1)

    def test_realGetAllThemes(self):
        """
        C{_realGetAllThemes} should collect themes from available offerings.
        """
        tc = webtheme.ThemeCache()
        ths = tc.getAllThemes()
        self.assertEqual([theme.name for theme in ths],
                         ['foo', 'boz', 'baz'])


    def test_clearThemeCache(self):
        """
        C{emptyCache} should invalidate the cache contents for both types.
        """
        tc = webtheme.ThemeCache()
        s = Store()
        tc.getAllThemes()
        tc.getInstalledThemes(s)
        tc.emptyCache()
        self.assertEqual(tc._getAllThemesCache, None)
        self.assertEqual(len(tc._getInstalledThemesCache), 0)
