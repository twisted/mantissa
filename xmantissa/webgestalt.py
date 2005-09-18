
"""
Account configuration and management features, via the web.

This is a pitiful implementation of these concepts (hence the pitiful
module name).  It will be replaced by a real implementation when
clustering is ready for general use.
"""

import pytz

from zope.interface import implements

from twisted.cred import checkers
from twisted.python.components import registerAdapter
from twisted.internet import defer

from nevow import inevow, livepage, rend

from epsilon import extime

from axiom import item, attributes, userbase

from xmantissa import ixmantissa, websession, website, webnav

class InvalidPassword(Exception):
    pass

class NonExistentAccount(Exception):
    pass

class NoSuchSession(Exception):
    pass


class AuthenticationApplication(item.Item):
    implements(ixmantissa.INavigableElement)

    typeName = 'mantissa_web_authentication_application'
    schemaVersion = 1

    lastCredentialsChange = attributes.timestamp(allowNone=False)

    def __init__(self, **kw):
        if 'lastCredentialsChange' not in kw:
            kw['lastCredentialsChange'] = extime.Time()
        super(AuthenticationApplication, self).__init__(**kw)


    def installOn(self, other):
        other.powerUp(self, ixmantissa.INavigableElement)


    def getTabs(self):
        return [webnav.Tab('Configuration', self.storeID, 0.0,
                           [webnav.Tab('Authentication',
                                       self.storeID,
                                       0.0)],
                           authoritative=False)]


    def topPanelContent(self):
        return None


    def _account(self):
        substore = self.store.parent.getItemByID(self.store.idInParent)
        for account in self.store.parent.query(userbase.LoginAccount,
                                               userbase.LoginAccount.avatars == substore):
            return account
        raise NonExistentAccount()

    def _username(self):
        acc = self._account()
        # XXX Why is authenticatedAs bytes and not text?
        return (acc.username + '@' + userbase.dflip(acc.domain)).encode('utf-8')

    def hasCurrentPassword(self):
        return defer.succeed(self._account().password is not None)

    def changePassword(self, oldPassword, newPassword):
        account = self._account()
        if account.password is not None and account.password != oldPassword:
            raise InvalidPassword()
        else:
            account.password = newPassword
            self.lastCredentialsChange = extime.Time()


    def persistentSessions(self):
        username = self._username()
        return self.store.parent.query(
            websession.PersistentSession,
            websession.PersistentSession.authenticatedAs == username)


    def cancelPersistentSession(self, uid):
        username = self._username()
        for sess in self.store.parent.query(websession.PersistentSession,
                                            attributes.AND(websession.PersistentSession.authenticatedAs == username,
                                                           websession.PersistentSession.sessionKey == uid)):
            sess.deleteFromStore()
            break
        else:
            raise NoSuchSession()



# XXX Nevow is basically the worst possible piece of software
class PersistentSessionContainer(object):
    implements(inevow.IContainer)

    def __init__(self, session, zone):
        self.session = session
        self.zone = zone


    def child(self, ctx, name):
        if name == 'lastUsed':
            return ctx.tag[self.session.lastUsed.asHumanly(self.zone) + ' ' + self.zone.zone]


class AuthenticationFragment(website.AxiomFragment):
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'authentication-configuration'
    live = True

    def __init__(self, original):
        self.store = original.store
        website.AxiomFragment.__init__(self, original)


    def head(self):
        return ()


    def render_currentPasswordField(self, ctx, data):
        d = self.original.hasCurrentPassword()

        def cb(result):
            if result:
                patName = 'current-password'
            else:
                patName = 'no-current-password'
            return inevow.IQ(self.docFactory).onePattern(patName)

        return d.addCallback(cb)


    def render_cancel(self, ctx, data):
        # XXX See previous XXX
        return ctx.tag(onclick=[
                livepage.js.server.handle('cancel', data.session.sessionKey),
                livepage.stop])


    def handle_changePassword(self, ctx, currentPassword, newPassword):
        try:
            self.original.changePassword(currentPassword, newPassword)
        except NonExistentAccount:
            return livepage.alert('You do not seem to exist.  Password unchanged.')
        except InvalidPassword:
            return livepage.alert('Incorrect password!  Nothing changed.')
        else:
            return [
                livepage.js.document.forms[0].currentPassword.removeAttribute("disabled"),
                livepage.eol,
                livepage.alert('Password changed!'),
                ]



    def handle_cancel(self, ctx, uid):
        try:
            self.original.cancelPersistentSession(uid)
        except NoSuchSession:
            return livepage.alert('That session seems to have vanished.')
        else:
            return livepage.alert('Session discontinued')


    def data_persistentSessions(self, ctx, data):
        zone = pytz.timezone('US/Eastern')
        return (PersistentSessionContainer(sess, zone) for sess in self.original.persistentSessions())


registerAdapter(AuthenticationFragment, AuthenticationApplication, ixmantissa.INavigableFragment)
