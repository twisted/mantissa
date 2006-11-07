from twisted.trial.unittest import TestCase
from nevow.testutil import AccumulatingFakeRequest, renderPage
from axiom.store import Store
from axiom import userbase
from xmantissa.signup import PasswordResetResource, _PasswordResetAttempt


class PasswordResetTestCase(TestCase):
    def setUp(self):
        s = Store()

        self.loginSystem = userbase.LoginSystem(store=s)

        la = userbase.LoginAccount(store=s,
                                   password=u'secret',
                                   disabled=False)

        # don't use addLoginMethod because we don't properly set up the
        # login account
        userbase.LoginMethod(store=s,
                             domain=u'divmod.com',
                             localpart=u'joe',
                             protocol=u'zombie dance',
                             verified=True,
                             internal=True,
                             account=la)

        userbase.LoginMethod(store=s,
                             domain=u'external.com',
                             localpart=u'joe',
                             protocol=u'zombie dance',
                             verified=False,
                             internal=False,
                             account=la)

        # create an account with no external mail address
        account = userbase.LoginAccount(store=s,
                                        password=u'secret',
                                        disabled=False)

        userbase.LoginMethod(store=s,
                             domain=u'divmod.com',
                             localpart=u'jill',
                             protocol=u'zombie dance',
                             verified=True,
                             internal=True,
                             account=account)

        self.store = s
        self.loginAccount = la
        self.nonExternalAccount = account
        self.reset = PasswordResetResource(self.store)


    def test_reset(self):
        """
        Test a password reset, as it might happen for a user
        """
        self.reset.resetPassword(
            self.reset.newAttemptForUser(u'joe@divmod.com'),
            u'more secret')

        self.assertEqual(self.loginAccount.password, u'more secret')
        self.assertEqual(self.store.count(_PasswordResetAttempt), 0)


    def test_attemptByKey(self):
        """
        Test that L{xmantissa.signup.PasswordResetResource.attemptByKey}
        knows the difference between valid and invalid keys
        """
        self.failUnless(self.reset.attemptByKey(
                self.reset.newAttemptForUser(u'joe@divmod.com').key))
        self.failIf(self.reset.attemptByKey(u'not really a key'))


    def test_accountByAddress(self):
        """
        Test that L{xmantissa.signup.PasswordResetResource.accountByAddress}
        behaves similarly to L{axiom.userbase.LoginSystem.accountByAddress}
        """
        self.assertEqual(
            self.reset.accountByAddress(u'joe@divmod.com'),
            self.loginSystem.accountByAddress(u'joe', u'divmod.com'))


    def test_handleRequest(self):
        """
        Check that handling a password reset request for a user sends email
        appropriate.
        """
        def myFunc(url, attempt, email):
            myFunc.emailsSent += 1
            myFunc.url = url
            myFunc.attempt = attempt
            myFunc.email = email
        url = 'http://oh.no/reset.html'
        myFunc.emailsSent = 0
        self.reset._sendEmail=myFunc

        # positive case. User exists. Email should be sent
        self.reset.handleRequestForUser(u'joe@divmod.com', url)
        self.assertEquals(myFunc.emailsSent, 1)
        self.assertEquals(myFunc.url, 'http://oh.no/reset.html')
        self.assertEquals(myFunc.attempt.username, u'joe@divmod.com')
        self.assertEquals(myFunc.email, 'joe@external.com')

        # Negative case. User does not exist. Email should not be sent
        self.reset.handleRequestForUser(u'no_joe@divmod.com', url)
        self.assertEquals(myFunc.emailsSent, 1)

        # Negative case. User exists, but has no external mail. Email should not
        # be sent.
        self.reset.handleRequestForUser(u'jill@divmod.com', url)
        self.assertEquals(myFunc.emailsSent, 1)


    def test_getExternalEmail(self):
        """
        Test that we can accurately retrieve an external email address from an
        attempt.
        """
        email = self.reset.getExternalEmail(self.loginAccount)
        self.assertEquals(email, 'joe@external.com')


    def test_noExternalEmail(self):
        """
        Test that C{getExternalEmail} returns C{None} if there is no external
        email address for that account.
        """
        email = self.reset.getExternalEmail(self.nonExternalAccount)
        self.assertEquals(email, None)


    def test_onlyUsernameSpecified(self):
        """
        Test that if the user only supplies the local part of their username
        then the password resetter will still find the correct user.
        """
        def handleRequest(username, url):
            handleRequest.attempt = self.reset.newAttemptForUser(username)
            handleRequest.username = username

        class Request(AccumulatingFakeRequest):
            method = 'POST'

            def __init__(self, *a, **kw):
                AccumulatingFakeRequest.__init__(self, *a, **kw)
                self.args = {'username': ['joe']}
                self.setHeader('host', 'divmod.com')

        self.reset.handleRequestForUser = handleRequest
        d = renderPage(self.reset, reqFactory=Request)
        d.addCallback(lambda _: self.assertEquals(handleRequest.username,
                                                  'joe@divmod.com'))
        return d
