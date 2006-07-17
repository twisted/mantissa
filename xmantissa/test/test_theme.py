
from twisted.trial.unittest import TestCase
from twisted.python.reflect import qual

from nevow.athena import LivePage
from nevow.loaders import stan
from nevow.tags import html, head, body, invisible, directive
from nevow.context import WovenContext
from nevow.testutil import FakeRequest
from nevow.inevow import IRequest

from axiom.store import Store

from xmantissa.webtheme import (
    getAllThemes, getInstalledThemes, MantissaTheme, ThemedFragment,
    ThemedElement)
from xmantissa.offering import installOffering
from xmantissa.plugins.baseoff import baseOffering

class WebThemeTestCase(TestCase):
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
        f = ThemedSubclass()
        p = LivePage(
            docFactory=stan(
                html[
                    head(render=directive('liveglue')),
                    body[
                        invisible(render=lambda ctx, data: f)]]))
        f.setFragmentParent(p)

        ctx = WovenContext()
        req = FakeRequest()
        ctx.remember(req, IRequest)

        d = p.renderHTTP(ctx)
        def rendered(ign):
            p.action_close(None)

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
