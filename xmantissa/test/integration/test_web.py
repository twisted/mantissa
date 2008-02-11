
"""
Integration tests having primarily to do with Mantissa's HTTP features.
"""

from zope.interface import Interface, Attribute, implements

from twisted.python.reflect import qual
from twisted.python.filepath import FilePath
from twisted.python.components import registerAdapter
from twisted.internet.defer import Deferred
from twisted.trial.unittest import TestCase
from twisted.web import http

from nevow.inevow import ICurrentSegments, IRemainingSegments
from nevow.context import RequestContext
from nevow.url import URL
from nevow.testutil import renderPage, FakeRequest
from nevow.page import Element
from nevow.guard import SESSION_KEY, GuardSession
from nevow import athena

from axiom.store import Store
from axiom.attributes import text
from axiom.item import Item
from axiom.userbase import LoginSystem
from axiom.plugins.mantissacmd import Mantissa

import xmantissa
from xmantissa.ixmantissa import (
    INavigableFragment, IOfferingTechnician, IPreferenceAggregator,
    IWebTranslator)
from xmantissa.port import TCPPort
from xmantissa.offering import Offering, installOffering
from xmantissa.product import Product
from xmantissa.website import WebSite
from xmantissa.webapp import PrivateApplication
from xmantissa.sharing import getEveryoneRole
from xmantissa.websharing import addDefaultShareID
from xmantissa.plugins.baseoff import baseOffering


def getResource(site, uri, headers={}, cookies={}):
    """
    Retrieve the resource at the given URI from C{site}.

    Return a L{Deferred} which is called back with the request after
    resource traversal and rendering has finished.

    @type site: L{NevowSite}
    @param site: The site object from which to retrieve the resource.

    @type uri: C{str}
    @param uri: The absolute path to the resource to retrieve, eg
        I{/private/12345}.

    @type headers: C{dict}
    @param headers: HTTP headers to include in the request.
    """
    headers = headers.copy()
    cookies = cookies.copy()

    url = URL.fromString(uri)
    args = {}
    for (k, v) in url.queryList():
        args.setdefault(k, []).append(v)
    remainingSegments = tuple(url.pathList())
    request = FakeRequest(headers=headers, cookies=cookies, uri=uri,
                          args=args, currentSegments=())
    requestContext = RequestContext(parent=site.context, tag=request)
    requestContext.remember((), ICurrentSegments)
    requestContext.remember(remainingSegments, IRemainingSegments)

    page = site.getPageContextForRequestContext(requestContext)
    page.addCallback(
        renderPage,
        topLevelContext=lambda tag: tag,
        reqFactory=lambda: request)
    page.addCallback(lambda ignored: request)
    return page


def getWithSession(site, redirectLimit, uri, headers={}):
    """
    Retrieve the resource at the given URI from C{site} while supplying a
    cookie identifying an existing session.

    @see L{getResource}
    """
    visited = []
    cookies = {}

    result = Deferred()
    page = getResource(site, uri, headers)
    def rendered(request):
        if request.redirected_to is None:
            result.callback(request)
        else:
            visited.append(request.redirected_to)

            if visited.index(request.redirected_to) != len(visited) - 1:
                visited.append(request.redirected_to)
                result.errback(Exception("Redirect loop: %r" % (visited,)))
            elif len(visited) > redirectLimit:
                result.errback(Exception("Too many redirects: %r" % (visited,)))
            else:
                newHeaders = headers.copy()

                # Respect redirects
                location = URL.fromString(request.redirected_to)
                newHeaders['host'] = location.netloc
                # Easiest way to make it relative
                location.scheme = ''
                location.netloc = ''

                # Respect cookies
                cookies.update(request.cookies)

                # str(URL) shouldn't really do what it does.
                page = getResource(
                    site, str(location), newHeaders, cookies)
                page.addCallbacks(rendered, result.errback)

    page.addCallbacks(rendered, result.errback)
    return result



class IDummy(Interface):
    """
    An interface for which dummy items can be shared.
    """
    markup = Attribute(
        """
        The precise result to produce when rendering this object.
        """)



class DummyItem(Item):
    """
    An item which can be shared in order to test web sharing interactions.
    """
    implements(IDummy)

    markup = text(
        doc="""
        Some text to emit when rendering this item.
        """)



class DummyView(Element):
    """
    View for any L{IDummy}.
    """
    def __init__(self, dummy):
        Element.__init__(self)
        self.dummy = dummy


    def rend(self, ctx, data):
        return self.dummy.markup.encode('ascii')

registerAdapter(DummyView, IDummy, INavigableFragment)



class IntegrationTestsMixin:
    """
    L{TestCase} mixin defining setup and teardown such that requests can be
    made against a site strongly resembling an actual one.

    @type store: L{Store}
    @ivar store: The site store.

    @type web: L{WebSite}
    @ivar web: The site store's web site.

    @type login: L{LoginSystem}
    @ivar login: The site store's login system.

    @ivar site: A protocol factory created by the site store's L{WebSite}.
        This is probably a L{NevowSite}, but that should be an irrelevant
        detail.

    @type domain: C{unicode}
    @ivar domain: The canonical name of the website and the domain part used
        when creating users.
    """
    domain = u'example.com'

    def setUp(self):
        """
        Create a L{Store} with a L{WebSite} in it.  Get a protocol factory from
        the website and save it for tests to use.  Patch L{twisted.web.http}
        and L{nevow.guard} so that they don't create garbage timed calls that
        have to be cleaned up.
        """
        self.store = Store(filesdir=self.mktemp()) # See #2484
        installOffering(self.store, baseOffering, {})
        Mantissa().installSite(self.store, u'', False) # See #2483
        self.web = self.store.findUnique(WebSite)
        self.login = self.store.findUnique(LoginSystem)

        # XXX These things should be offering installation parameters.
        self.web.hostname = self.domain
        TCPPort(store=self.store, factory=self.web, portNumber=80)

        self.site = self.web.getFactory()

        self.origFunctions = (http._logDateTimeStart,
                              GuardSession.checkExpired.im_func,
                              athena.ReliableMessageDelivery)
        http._logDateTimeStart = lambda: None
        GuardSession.checkExpired = lambda self: None
        athena.ReliableMessageDelivery = lambda *a, **kw: None


    def tearDown(self):
        """
        Restore the patched functions to their original state.
        """
        http._logDateTimeStart = self.origFunctions[0]
        GuardSession.checkExpired = self.origFunctions[1]
        athena.ReliableMessageDelivery = self.origFunctions[2]
        del self.origFunctions



class AnonymousWebSiteIntegrationTests(IntegrationTestsMixin, TestCase):
    """
    Integration (ie, not unit) tests for an anonymous user's interactions with
    a Mantissa L{WebSite}.
    """
    def _verifyResource(self, uri, verifyCallback):
        """
        Request the given URI and call the given callback with the resulting
        request.

        @type uri: C{str}

        @return: A L{Deferred} which will be called back with the result of
            C{verifyCallback} or which will errback if there is a problem
            requesting the resource or if the C{verifyCallback} raises an
            exception.
        """
        page = getResource(
            self.site, uri, {'host': self.domain.encode('ascii')})
        page.addCallback(verifyCallback)
        return page


    def test_rootResource(self):
        """
        A sessionless, unauthenticated request for C{/} is responded to with a
        redirect to negotiate a session.
        """
        def rendered(request):
            redirectLocation = URL.fromString(request.redirected_to)
            key, path = redirectLocation.pathList()
            self.assertTrue(key.startswith(SESSION_KEY))
            self.assertEqual(path, '')
        return self._verifyResource('/', rendered)


    def test_mantissaStylesheet(self):
        """
        A sessionless, unauthenticated request for C{/Mantissa/mantissa.css} is
        responded to with the contents of the mantissa css file.
        """
        def rendered(request):
            staticPath = FilePath(xmantissa.__file__).sibling('static')
            self.assertEqual(
                request.accumulator,
                staticPath.child('mantissa.css').getContent())
        return self._verifyResource('/Mantissa/mantissa.css', rendered)


    def _fakeOfferings(self, store, offerings):
        """
        Override the adaption hook on the given L{Store} instance so that
        adapting it to L{IOfferingTechnician} returns an object which
        reports the given offerings as installed.
        """
        class FakeOfferingTechnician(object):
            def getInstalledOfferings(self):
                return offerings
        store.inMemoryPowerUp(FakeOfferingTechnician(), IOfferingTechnician)


    def test_offeringWithStaticContent(self):
        """
        L{StaticContent} has a L{File} child with the name of one of the
        offerings passed to its initializer which has a static content path.
        """
        # Make a fake offering to get its static content rendered.
        offeringName = u'name of the offering'
        offeringPath = FilePath(self.mktemp())
        offeringPath.makedirs()
        childName = 'content'
        childContent = 'the content'
        offeringPath.child(childName).setContent(childContent)

        self._fakeOfferings(self.store, {
                offeringName: Offering(
                    offeringName, None, None, None, None, None, None,
                    offeringPath, None)})

        def rendered(request):
            self.assertEqual(request.accumulator, childContent)
        return self._verifyResource('/static/%s/%s' % (
                offeringName.encode('ascii'), childName), rendered)


    def test_userSharedResource(self):
        """
        An item shared by a user to everybody can be accessed by an
        unauthenticated user.
        """
        # Make a user to own the shared item.
        username = u'alice'
        aliceAccount = self.login.addAccount(
            username, self.domain, u'password', internal=True)
        aliceStore = aliceAccount.avatars.open()

        # Make an item to share.
        sharedContent = u'content owned by alice and shared to everyone'
        shareID = getEveryoneRole(aliceStore).shareItem(
            DummyItem(store=aliceStore, markup=sharedContent)).shareID

        # Get it.
        page = getWithSession(
            self.site, 2, '/users/%s/%s' % (
                username.encode('ascii'), shareID.encode('ascii')),
            {'host': self.domain.encode('ascii')})
        def rendered(request):
            self.assertIn(sharedContent.encode('ascii'), request.accumulator)
        page.addCallback(rendered)
        return page



class AuthenticatedWebSiteIntegrationTests(IntegrationTestsMixin, TestCase):
    """
    Integration (ie, not unit) tests for an authenticated user's interactions
    with a Mantissa L{WebSite}.

    @type username: C{unicode}
    @ivar username: The localpart used when creating users.

    @type cookies: C{dict}
    @ivar cookies: The cookies to use in order to use the authenticated session
        created in L{setUp}.
    """
    username = u'alice'

    def setUp(self):
        """
        Create an account and log in using it.
        """
        IntegrationTestsMixin.setUp(self)

        # Make an account to be already logged in.
        self.userAccount = self.login.addAccount(
            self.username, self.domain, u'password', internal=True)
        self.userStore = self.userAccount.avatars.open()

        # Make a product that includes PrivateApplication.  This is probably
        # the minimum requirement for web access.
        web = Product(store=self.store,
                      types=[qual(PrivateApplication)])
        # Give it to Alice.
        web.installProductOn(self.userStore)

        # Log in to the web as Alice.
        login = getWithSession(
            self.site, 3, '/__login__?username=%s@%s&password=%s' % (
                self.username.encode('ascii'), self.domain.encode('ascii'),
                'password'),
            {'host': self.web.hostname.encode('ascii')})
        def loggedIn(request):
            self.cookies = request.cookies
        login.addCallback(loggedIn)
        return login


    def test_authenticatedResetPasswordRedirectsToSettings(self):
        """
        When a user is already logged in, navigating to C{/resetPassword}
        redirects them to their own settings page.
        """
        prefPage = IPreferenceAggregator(self.userStore)
        urlPath = IWebTranslator(self.userStore).linkTo(prefPage.storeID)

        # Get the password reset resource.
        page = getResource(
            self.site, '/resetPassword',
            headers={'host': self.web.hostname.encode('ascii')},
            cookies=self.cookies)

        def rendered(request):
            # Make sure it's a redirect to the settings page.
            self.assertEquals(
                'http://' + self.web.hostname.encode('ascii') + urlPath,
                request.redirected_to)
        page.addCallback(rendered)
        return page


    def test_userSharedResource(self):
        """
        An item shared by a user to everybody can be accessed by that user.
        """
        # Make an item and share it.
        sharedContent = u'content owned by alice and shared to everyone'
        shareID = getEveryoneRole(self.userStore).shareItem(
            DummyItem(store=self.userStore, markup=sharedContent)).shareID

        page = getResource(
            self.site, '/users/%s/%s' % (
                self.username.encode('ascii'), shareID.encode('ascii')),
            {'host': self.domain.encode('ascii')},
            self.cookies)

        def rendered(request):
            self.assertIn(sharedContent, request.accumulator)
        page.addCallback(rendered)
        return page



class UserSubdomainWebSiteIntegrationTests(IntegrationTestsMixin, TestCase):
    """
    @type share: L{Share}
    @ivar share: The share for the shared item.

    @type sharedContent: C{unicode}
    @ivar sharedContent: The text which will appear in the view for C{share}.

    @type username: C{unicode}
    @ivar username: The localpart of the user which shared C{share}.

    @type virtualHost: C{unicode}
    @ivar virtualHost: The full domain name of a user-specific subdomain for
        the user which shared C{share}.
    """
    skip = "User subdomain virtual hosting not implemented yet.  See #2406."

    def setUp(self):
        """
        Create a user account and share an item from it to everyone.
        """
        IntegrationTestsMixin.setUp(self)

        # Make an account to go with this virtual host.
        self.username = u'alice'
        self.userAccount = self.login.addAccount(
            self.username, self.domain, u'password', internal=True)
        self.userStore = self.userAccount.avatars.open()
        self.virtualHost = u'.'.join((username, self.domain))

        # Share something that we'll try to load.
        self.sharedContent = u'content owned by alice and shared to everyone'
        self.share = getEveryoneRole(self.userStore).shareItem(
            DummyItem(store=self.userStore, markup=self.sharedContent))


    def test_anonymousUserVirtualHost(self):
        """
        A request by an anonymous user for I{/shareid} on a subdomain of the
        website's is responded to with the page for indicated item shared by
        the user to whom that subdomain corresponds.
        """
        page = getWithSession(
            self.site, 2, '/' + self.share.shareID.encode('ascii'),
            {'host': virtualHost.encode('ascii')})
        def rendered(request):
            self.assertIn(
                self.sharedContent.encode('ascii'), request.accumulator)
        page.addCallback(rendered)
        return page


    def test_authenticatedUserVirtualHost(self):
        """
        A request by an authenticated user for I{/shareid} on a subdomain of
        the website's is responded to in the same way as the same request made
        by an anonymous user.
        """
        # Make an account as which to authenticate.
        username = u'bob'
        bobAccount = self.login.addAccount(
            username, self.domain, u'password', internal=True)
        bobStore = bobAccount.avatars.open()

        # Make a product that includes PrivateApplication.  This supposes that
        # viewing user-subdomain virtual hosting is the responsibility of
        # PrivateApplication.
        web = Product(store=self.store,
                      types=[qual(PrivateApplication)])
        # Give it to Bob.
        web.installProductOn(bobStore)

        # Log in through the web as Bob.
        cookies = {}
        login = getWithSession(
            self.site, 3, '/__login__?username=%s@%s&password=%s' % (
                username.encode('ascii'), domain.encode('ascii'), 'password'),
            {'host': self.domain.encode('ascii')})
        def loggedIn(request):
            # Get the share page from the virtual host as the authenticated
            # user.
            return getResource(
                self.site, '/' + self.share.shareID.encode('ascii'),
                headers={'host': self.virtualHost.encode('ascii')},
                cookies=request.cookies)
        login.addCallback(loggedIn)

        def rendered(request):
            # Make sure we're really authenticated.
            self.assertIn(username.encode('ascii'), request.accumulator)
            # Make sure the shared thing is there.
            self.assertIn(
                self.sharedContent.encode('ascii'), request.accumulator)
        login.addCallback(rendered)
        return login


    def test_authenticatedUserVirtualHostDefaultShare(self):
        """
        A request by an authenticated user for I{/} on a subdomain of of the
        website's is responded to in the same way as the same request made by
        an anonymous user.
        """
        # Make an account as which to authenticate.
        username = u'bob'
        bobAccount = self.login.addAccount(
            username, self.domain, u'password', internal=True)
        bobStore = bobAccount.avatars.open()

        # Make a product that includes PrivateApplication.  This supposes that
        # viewing user-subdomain virtual hosting is the responsibility of
        # PrivateApplication.
        web = Product(store=self.store,
                      types=[qual(PrivateApplication)])
        # Give it to Bob.
        web.installProductOn(bobStore)

        # Log in through the web as Bob.
        cookies = {}
        login = getWithSession(
            self.site, 3, '/__login__?username=%s@%s&password=%s' % (
                username.encode('ascii'), domain.encode('ascii'), 'password'),
            {'host': self.domain.encode('ascii')})
        def loggedIn(request):
            # Get the share page as the authenticated user.
            return getResource(
                self.site, '/',
                headers={'host': self.virtualHost.encode('ascii')},
                cookies=request.cookies)
        login.addCallback(loggedIn)

        def rendered(request):
            # Make sure we're really authenticated.
            self.assertIn(username.encode('ascii'), request.accumulator)
            # Make sure the shared thing is there.
            self.assertIn(
                self.sharedContent.encode('ascii'), request.accumulator)
        login.addCallback(rendered)
        return login
