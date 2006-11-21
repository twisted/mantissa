# -*- test-case-name: xmantissa.test.test_theme -*-

import os, sys

from zope.interface import implements

from twisted.python import reflect
from twisted.python.util import sibpath

from nevow.loaders import xmlfile
from nevow import inevow, tags, athena, page, stan
from nevow.url import URL

from xmantissa import ixmantissa
from xmantissa.offering import getInstalledOfferings, getOfferings

def getAllThemes():
    l = []
    for offering in getOfferings():
        l.extend(offering.themes)
    l.sort(key=lambda o: o.priority)
    l.reverse()
    return l

def getInstalledThemes(store):
    l = []
    for offering in getInstalledOfferings(store).itervalues():
        l.extend(offering.themes)
    l.sort(key=lambda o: o.priority)
    l.reverse()
    return l

_marker = object()

def getLoader(n, default=_marker):
    """
    Deprecated.  Don't call this.
    """
    for t in getAllThemes():
        fact = t.getDocFactory(n, None)
        if fact is not None:
            return fact
    if default is _marker:
        raise RuntimeError("No loader for %r anywhere" % (n,))
    return default

class XHTMLDirectoryTheme(object):
    """
    I am a theme made up of a directory full of XHTML templates.

    The suggested use for this class is to make a subclass,
    C{YourThemeSubclass}, in a module in your Mantissa package, create a
    directory in your package called 'yourpackage/themes/<your theme name>',
    and then pass <your theme name> as the constructor to C{YourThemeSubclass}
    when passing it to the constructor of L{xmantissa.offering.Offering}.  You
    can then avoid calculating the path name in the constructor, since it will
    be calculated based on where your subclass was defined.

    @ivar directoryName: the name of the directory containing the appropriate
    template files.

    @ivar themeName: the name of the theme that this directory represents.
    This will be displayed to the user.
    """
    implements(ixmantissa.ITemplateNameResolver)

    def __init__(self, themeName, priority=0, directoryName=None):
        """
        Create a theme based off of a directory full of XHTML templates.

        @param themeName: sets my themeName

        @param priority: an integer that affects the ordering of themes
        returned from L{getAllThemes}.

        @param directoryName: If None, calculates the directory name based on
        the module the class is defined in and the given theme name.  For a
        subclass C{bar.baz.FooTheme} defined in C{bar/baz.py} the instance
        C{FooTheme('qux')}, regardless of where it is created, will have a
        default directoryName of {bar/themes/qux/}.
        """

        self.themeName = themeName
        self.priority = priority
        self.cachedLoaders = {}
        if directoryName is None:
            directoryName = os.path.join(
                sibpath(sys.modules[self.__class__.__module__].__file__,
                        'themes'),
                self.themeName)
        self.directoryName = directoryName


    def head(self, request, website):
        """
        Provide content to include in the head of the document.  Override this.

        @type request: L{inevow.IRequest} provider
        @param request: The request object for which this is a response.

        @param website: The site-wide L{xmantissa.website.WebSite} instance.
        Primarily of interest for its C{cleartextRoot} and C{encryptedRoot}
        methods.

        @return: Anything providing or adaptable to L{nevow.inevow.IRenderer},
        or C{None} to include nothing.
        """


    # IThemePreferrer
    def getDocFactory(self, fragmentName, default=None):
        if fragmentName in self.cachedLoaders:
            return self.cachedLoaders[fragmentName]
        p = os.path.join(self.directoryName, fragmentName + '.html')
        if os.path.exists(p):
            loader = xmlfile(p)
            self.cachedLoaders[fragmentName] = loader
            return loader
        return default



class MantissaTheme(XHTMLDirectoryTheme):
    def head(self, request, website):
        root = website.encryptedRoot(request.getHeader('host'))
        return tags.link(
            rel='stylesheet',
            type='text/css',
            href=root.child('Mantissa').child('mantissa.css'))



class _ThemedMixin(object):
    """
    Mixin for L{nevow.inevow.IRenderer} implementations which want to use the
    theme system.
    """

    implements(ixmantissa.ITemplateNameResolver)

    def __init__(self, fragmentParent=None):
        """
        Create a themed fragment with the given parent.

        @param fragmentParent: An object to pass to C{setFragmentParent}.  If
        not None, C{self.setFragmentParent} is called immediately.  It is
        suggested but not required that you set this here; if not, the
        resulting fragment will be initialized in an inconsistent state.  You
        must call setFragmentParent to correct this before this fragment is
        rendered.
        """
        super(_ThemedMixin, self).__init__()
        if fragmentParent is not None:
            self.setFragmentParent(fragmentParent)


    def head(self):
        """
        Don't do anything.
        """

    def rend(self, context, data):
        """
        Automatically retrieve my C{docFactory} based on C{self.fragmentName}
        before invoking L{athena.LiveElement.rend}.
        """
        if self.docFactory is None:
            self.docFactory = self.getDocFactory(self.fragmentName)
        return super(_ThemedMixin, self).rend(context, data)


    def pythonClass(self, request, tag):
        """
        This renderer is available on all themed fragments.  It returns the fully
        qualified python name of the class of the fragment being rendered.
        """
        return reflect.qual(self.__class__)
    page.renderer(pythonClass)


    def render_pythonClass(self, ctx, data):
        return self.pythonClass(inevow.IRequest(ctx), ctx.tag)


    _website = None
    def getWebSite(self):
        """
        Retrieve the L{xmantissa.website.WebSite} instance installed on the
        site-store.
        """
        if self._website is None:
            siteStore = self.store
            if siteStore.parent is not None:
                siteStore = siteStore.parent
            self._website = inevow.IResource(siteStore)
        return self._website


    # ITemplateNameResolver
    def getDocFactory(self, fragmentName, default=None):
        f = getattr(self.page, "getDocFactory", getLoader)
        return f(fragmentName, default)



class ThemedFragment(_ThemedMixin, athena.LiveFragment):
    """
    Subclass me to create a LiveFragment which supports automatic
    theming. (Deprecated)

    @ivar fragmentName: A short string naming the template from which the
    docFactory for this fragment should be loaded.

    @see ThemedElement
    """
    fragmentName = 'fragment-no-fragment-name-specified'



class ThemedElement(_ThemedMixin, athena.LiveElement):
    """
    Subclass me to create a LiveElement which supports automatic theming.

    @ivar fragmentName: A short string naming the template from which the
    docFactory for this fragment should be loaded.
    """
    fragmentName = 'element-no-fragment-name-specified'
