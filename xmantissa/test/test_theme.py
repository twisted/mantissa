
from twisted.trial.unittest import TestCase
from twisted.python.reflect import qual

from nevow.athena import LivePage
from nevow.loaders import stan
from nevow.stan import Tag
from nevow.tags import (
    html, head, body, div, span, img, script, link, invisible, directive)
from nevow.context import WovenContext
from nevow.testutil import FakeRequest, AccumulatingFakeRequest as makeRequest
from nevow.flat import flatten
from nevow.inevow import IRequest
from nevow.page import renderer

from axiom.store import Store
from axiom.substore import SubStore

from xmantissa.webtheme import (
    getAllThemes, getInstalledThemes, MantissaTheme, ThemedFragment,
    ThemedElement, rewriteTagToRewriteURLs, _ThemedMixin)
from xmantissa.website import WebSite
from xmantissa.offering import installOffering
from xmantissa.plugins.baseoff import baseOffering

def testHead(theme):
    """
    Check that the head method of the given them doesn't explode.
    @param theme: probably an L{xmantissa.webtheme.XHTMLDirectoryTheme}
    """
    s = Store()
    flatten(theme.head(makeRequest(), WebSite(store=s, portNumber=80)))

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
        for theme in getAllThemes():
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
        dbdir = self.mktemp()
        s = Store(dbdir)

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


    def test_rewriter(self):
        """
        Test that the L{rewriteTagToRewriteURLs} preprocessing visitor rewrites
        img, script, and link nodes to use a custom render method.
        """
        for tag in [img(src='/foo/bar'),
                    script(src='/foo/bar'),
                    link(href='/foo/bar')]:
            rewriteTagToRewriteURLs(tag)
            self.assertEquals(
                tag._specials,
                {'render': directive('urlRewrite_' + tag.tagName)})

        for tag in [div(src='/foo/bar'), span(href='/foo/bar')]:
            rewriteTagToRewriteURLs(tag)
            self.assertEquals(tag._specials, {})


    def test_websiteDiscovery(self):
        """
        Test that L{_ThemedMixin.getWebSite} finds the right object whether it
        is wrapped around a user store or the store store.
        """
        s = Store(self.mktemp())
        WebSite(store=s, portNumber=80).installOn(s)

        ss = SubStore.createNew(s, ['user']).open()
        WebSite(store=ss, portNumber=8080).installOn(ss)

        themed = _ThemedMixin()
        themed.store = s
        self.assertEquals(
            themed.getWebSite().portNumber, 80,
            "Found the wrong WebSite from the site store.")

        themed = _ThemedMixin()
        themed.store = ss
        self.assertEquals(
            themed.getWebSite().portNumber, 80,
            "Found the wrong WebSite from the user store.")


    def test_imageSourceRewriting(self):
        """
        Test that a document containing links to static images has those links
        rewritten to an appropriate non-HTTPS URL when being rendered.
        """
        s = Store()
        WebSite(store=s, portNumber=80, hostname=u'example.com').installOn(s)

        class TestElement(ThemedElement):
            docFactory = stan(img(src='/Foo.png'))
            store = s

        d = self._render(TestElement())
        def rendered(req):
            self.assertIn(
                '<img src="http://example.com/Foo.png" />',
                req.v)
        d.addCallback(rendered)
        return d


    def test_imageSourceNotRewritten(self):
        """
        Test that an image tag which includes a hostname in its source does not
        have that source rewritten.
        """
        s = Store()
        WebSite(store=s, portNumber=80, hostname=u'example.com').installOn(s)

        class TestElement(ThemedElement):
            docFactory = stan(img(src='http://example.org/Foo.png'))
            store = s

        d = self._render(TestElement())
        def rendered(req):
            self.assertIn(
                '<img src="http://example.org/Foo.png" />',
                req.v)
        d.addCallback(rendered)
        return d


    def test_originalImageRendererRespected(self):
        """
        Test that an image tag with a render directive has that directive
        invoked after the URL has been rewritten.
        """
        s = Store()
        WebSite(store=s, portNumber=80, hostname=u'example.com').installOn(s)

        class TestElement(ThemedElement):
            docFactory = stan(img(src='/Foo.png', render=directive('mutate')))
            store = s

            def mutate(self, request, tag):
                self.mutated = flatten(tag.attributes['src'])
                return tag
            renderer(mutate)

        ele = TestElement()
        d = self._render(ele)
        def rendered(req):
            self.assertEquals(ele.mutated, 'http://example.com/Foo.png')
        d.addCallback(rendered)
        return d


    def test_scriptSourceRewriting(self):
        """
        Test that a document containing links to static javascript has those
        links rewritten to an appropriate non-HTTPS URL when being rendered.
        """
        s = Store()
        WebSite(store=s, portNumber=80, hostname=u'example.com').installOn(s)

        class TestElement(ThemedElement):
            docFactory = stan(script(src='/Foo.js'))
            store = s

        d = self._render(TestElement())
        def rendered(req):
            self.assertIn(
                '<script src="http://example.com/Foo.js"></script>',
                req.v)
        d.addCallback(rendered)
        return d


    def test_scriptSourceNotRewritten(self):
        """
        Test that a script tag which includes a hostname in its source does not
        have that source rewritten.
        """
        s = Store()
        WebSite(store=s, portNumber=80, hostname=u'example.com').installOn(s)

        class TestElement(ThemedElement):
            docFactory = stan(script(src='http://example.org/Foo.js'))
            store = s

        d = self._render(TestElement())
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
        s = Store()
        WebSite(store=s, portNumber=80, hostname=u'example.com').installOn(s)

        class TestElement(ThemedElement):
            docFactory = stan(script(src='/Foo.js', render=directive('mutate')))
            store = s

            def mutate(self, request, tag):
                self.mutated = flatten(tag.attributes['src'])
                return tag
            renderer(mutate)

        ele = TestElement()
        d = self._render(ele)
        def rendered(req):
            self.assertEquals(ele.mutated, 'http://example.com/Foo.js')
        d.addCallback(rendered)
        return d


    def test_linkHypertextReferenceRewriting(self):
        """
        Test that a document containing static link tags has those links
        rewritten to an appropriate non-HTTPS URL when being rendered.
        """
        s = Store()
        WebSite(store=s, portNumber=80, hostname=u'example.com').installOn(s)

        class TestElement(ThemedElement):
            docFactory = stan(link(href='/Foo.css'))
            store = s

        d = self._render(TestElement())
        def rendered(req):
            self.assertIn(
                '<link href="http://example.com/Foo.css" />',
                req.v)
        d.addCallback(rendered)
        return d


    def test_linkHypertextReferenceNotRewritten(self):
        """
        Test that a link which includes a hostname in its href does not have
        that href rewritten.
        """
        s = Store()
        WebSite(store=s, portNumber=80, hostname=u'example.com').installOn(s)

        class TestElement(ThemedElement):
            docFactory = stan(link(href='http://example.org/Foo.css'))
            store = s

        d = self._render(TestElement())
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
        s = Store()
        WebSite(store=s, portNumber=80, hostname=u'example.com').installOn(s)

        class TestElement(ThemedElement):
            docFactory = stan(link(href='/Foo.css', render=directive('mutate')))
            store = s

            def mutate(self, request, tag):
                self.mutated = flatten(tag.attributes['href'])
                return tag
            renderer(mutate)

        ele = TestElement()
        d = self._render(ele)
        def rendered(req):
            self.assertEquals(ele.mutated, 'http://example.com/Foo.css')
        d.addCallback(rendered)
        return d

    def test_head(self):
        testHead(MantissaTheme(''))
