# Copyright 2006-2008 Divmod, Inc.
# See LICENSE file for details

"""
Tests for L{xmantissa.websession}.
"""
from datetime import timedelta

from axiom.store import Store
from twisted.cred.checkers import AllowAnonymousAccess
from twisted.cred.portal import IRealm, Portal
from twisted.cred.credentials import Anonymous, IAnonymous
from twisted.internet.task import Clock
from twisted.trial.unittest import SynchronousTestCase
from nevow.guard import GuardSession
from nevow.inevow import IResource
from nevow.testutil import FakeRequest
from zope.interface import implementer

from xmantissa.websession import (
    PersistentSession, PersistentSessionWrapper, usernameFromRequest,
    PERSISTENT_SESSION_LIFETIME, SESSION_CLEAN_FREQUENCY, DBPassthrough)


@implementer(IRealm)
class _TrivialRealm(object):
    """
    A trivial realm for testing.
    """
    def __init__(self, avatarFactory=lambda: None):
        self._avatarFactory = avatarFactory


    def requestAvatar(self, avatarId, mind, *interfaces):
        avatar = self._avatarFactory()
        return IResource, avatar, lambda: None



class TestUsernameFromRequest(SynchronousTestCase):
    """
    Tests for L{xmantissa.websession.usernameFromRequest}.
    """
    def test_domainUnspecified(self):
        """
        Test that L{usernameFromRequest} adds the value of host header to the
        username in the request if the username doesn't already specify a
        domain.
        """
        request = FakeRequest(headers={'host': 'divmod.com'})
        request.args = {'username': ['joe']}
        username = usernameFromRequest(request)
        self.assertEqual(username, 'joe@divmod.com')


    def test_domainSpecified(self):
        """
        Test that L{usernameFromRequest} returns the username in the request
        if that username specifies a domain.
        """
        request = FakeRequest(headers={'host': 'divmod.com'})
        request.args = {'username': ['joe@notdivmod.com']}
        username = usernameFromRequest(request)
        self.assertEqual(username, 'joe@notdivmod.com')



class TestPersistentSessionWrapper(SynchronousTestCase):
    """
    Tests for L{PersistentSessionWrapper}.
    """
    def test_savorSessionCookie(self):
        """
        L{PersistentSessionWrapper.savorSessionCookie} adds a cookie with a
        large maximum age and a request-appropriate domain to the request.
        """
        request = FakeRequest(headers={'host': 'example.com'})
        resource = PersistentSessionWrapper(
            None, None, domains=['example.org', 'example.com'])

        resource.savorSessionCookie(request)
        self.assertEqual(
            request.cookies, {resource.cookieKey: request.getSession().uid})


    def test_createSession(self):
        """
        L{PersistentSessionWrapper.createSessionForKey} creates a persistent
        session in the database for the given session ID.
        """
        store = Store()
        resource = PersistentSessionWrapper(store, None)
        resource.createSessionForKey(b'key', b'username@domain')
        session = store.findUnique(PersistentSession)
        self.assertEqual(session.sessionKey, b'key')
        self.assertEqual(session.authenticatedAs, b'username@domain')


    def test_retrieveSession(self):
        """
        L{PersistentSessionWrapper.authenticatedUserForKey} returns the user to
        whom a session belongs.
        """
        store = Store()
        resource = PersistentSessionWrapper(store, None)
        resource.createSessionForKey(b'key', b'username@domain')
        user = resource.authenticatedUserForKey(b'key')
        self.assertEqual(user, b'username@domain')


    def test_retrieveNonexistentSession(self):
        """
        L{PersistentSessionWrapper.authenticatedUserForKey} returns C{None} if
        a session does not exist.
        """
        store = Store()
        resource = PersistentSessionWrapper(store, None)
        user = resource.authenticatedUserForKey(b'doesnotexist')
        self.assertIdentical(user, None)


    def test_removeSession(self):
        """
        L{PersistentSessionWrapper.removeSessionWithKey} removes an existing
        session with the given key.
        """
        store = Store()
        resource = PersistentSessionWrapper(store, None)
        resource.createSessionForKey(b'key', b'username@domain')
        self.assertEqual(store.query(PersistentSession).count(), 1)
        resource.removeSessionWithKey(b'key')
        self.assertEqual(store.query(PersistentSession).count(), 0)


    def test_removeNonexistentSession(self):
        """
        L{PersistentSessionWrapper.removeSessionWithKey} does nothing if the
        session does not exist.
        """
        store = Store()
        resource = PersistentSessionWrapper(store, None)
        resource.removeSessionWithKey(b'key')


    def _cookieTest(self, host, cookie, **kw):
        """
        Assert that a L{PersistentSessionWrapper} created with the given
        keyword arguments returns C{cookie} from its C{cookieDomainForRequest}
        method when passed a request with C{host} as the value for its I{Host}
        header.
        """
        request = FakeRequest(headers={'host': host})
        resource = PersistentSessionWrapper(None, None, **kw)
        self.assertEqual(resource.cookieDomainForRequest(request), cookie)


    def test_missingHostHeaderCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns C{None} if
        no host header is present.
        """
        self._cookieTest(None, None)


    def test_noDomainsNoSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns C{None} if
        no domain sequence is provided and subdomains are disabled.
        """
        self._cookieTest('example.com', None)


    def test_noDomainsSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns the hostname
        from the request prefixed with C{"."} if no domain sequence is provided
        and subdomains are enabled.
        """
        self._cookieTest('example.com', '.example.com', enableSubdomains=True)


    def test_domainNotFoundNoSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns the C{None}
        if the hostname from the request is not found in the supplied domain
        sequence and subdomains are disabled.
        """
        self._cookieTest('example.com', None, domains=['example.org'])


    def test_domainNotFoundSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns the hostname
        from the request prefixed with C{"."} if the hostname from the request
        is not found in the supplied domain sequence and subdomains are
        enabled.
        """
        self._cookieTest(
            'example.com', ".example.com", domains=['example.org'],
            enableSubdomains=True)


    def test_domainFoundNoSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns C{None} if
        the hostname from the request is found in the supplied domain sequence
        and subdomains are disabled.
        """
        self._cookieTest('example.com', None, domains=['example.com'])


    def test_domainFoundSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns the hostname
        from the request prefixed with C{"."} if the hostname from the request
        is found in the supplied domain sequence and subdomains are enabled.
        """
        self._cookieTest('example.com', ".example.com",
                         domains=['example.com'], enableSubdomains=True)


    def test_subdomainFoundNoSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns C{None} if
        the hostname from the request is a subdomain of one of the domains in
        the supplied domain sequence but subdomains are disabled.
        """
        self._cookieTest('alice.example.com', None, domains=['example.com'])


    def test_subdomainFoundSubdomainsCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} returns the domain
        from the supplied domain sequence prefixed with C{"."} that the
        hostname from the request is found to be a subdomain of, if it is found
        to be a subdomain of any of them and subdomains are enabled.
        """
        self._cookieTest('alice.example.com', '.example.com',
                         domains=['example.com'], enableSubdomains=True)


    def test_explicitPortNumberCookie(self):
        """
        L{PersistentSessionWrapper.cookieDomainForRequest} disregards the port
        number in the request host.
        """
        self._cookieTest('alice.example.com:8080', '.example.com',
                         domains=['example.com'], enableSubdomains=True)


    def test_sessionCleanup(self):
        """
        Expired sessions are cleaned up every C{sessionCleanFrequency} seconds.
        """
        clock = Clock()
        store = Store()
        portal = Portal(_TrivialRealm())
        portal.registerChecker(AllowAnonymousAccess(), IAnonymous)
        request = FakeRequest(headers={'host': 'example.com'})
        resource = PersistentSessionWrapper(
            store, portal, domains=['example.org', 'example.com'], clock=clock)
        session = GuardSession(resource, b'uid')

        # Create two sessions
        resource.createSessionForKey(b'key1', b'username@domain')
        resource.createSessionForKey(b'key2', b'username@domain')
        self.assertEqual(store.query(PersistentSession).count(), 2)

        # Session shouldn't be cleaned yet
        resource.login(request, session, Anonymous(), ())
        self.assertEqual(store.query(PersistentSession).count(), 2)

        # First session is expired and it's time for a clean
        ps = store.findUnique(
            PersistentSession, PersistentSession.sessionKey == b'key1')
        ps.lastUsed -= timedelta(seconds=PERSISTENT_SESSION_LIFETIME + 1)
        clock.advance(SESSION_CLEAN_FREQUENCY + 1)
        resource.login(request, session, Anonymous(), ())
        self.assertEqual(
            list(store.query(PersistentSession).getColumn('sessionKey')),
            [b'key2'])

        # Now we expire the second session
        ps2 = store.findUnique(
            PersistentSession, PersistentSession.sessionKey == b'key2')
        ps2.lastUsed -= timedelta(seconds=PERSISTENT_SESSION_LIFETIME + 1)
        clock.advance(SESSION_CLEAN_FREQUENCY + 1)
        resource.login(request, session, Anonymous(), ())
        self.assertEqual(store.query(PersistentSession).count(), 0)


    def test_logoutRemovesSession(self):
        """
        Logging out explicitly removes your persistent session.
        """
        store = Store()
        resource = PersistentSessionWrapper(store, None)
        session = GuardSession(resource, b'uid')

        resource.createSessionForKey(session.uid, b'username@domain')
        self.assertEqual(store.query(PersistentSession).count(), 1)

        resource.explicitLogout(session)
        self.assertEqual(store.query(PersistentSession).count(), 0)


    def test_cleanOnStart(self):
        """
        L{PersistentSessionWrapper} immediately cleans expired sessions on
        instantiation.
        """
        store = Store()
        resource = PersistentSessionWrapper(store, None)
        resource.createSessionForKey(b'key', b'username@domain')
        ps = store.findUnique(PersistentSession)
        ps.lastUsed -= timedelta(seconds=PERSISTENT_SESSION_LIFETIME + 1)

        PersistentSessionWrapper(store, None)
        self.assertEqual(store.query(PersistentSession).count(), 0)



class DBPassthroughTests(SynchronousTestCase):
    """
    Tests for L{DBPassthrough}.
    """
    def test_repr(self):
        """
        Getting the repr returns a sensible string.
        """
        dbp = DBPassthrough(None)
        r = repr(dbp)
        self.assertIn(b'DBPassthrough', r)
