from twisted.trial.unittest import TestCase
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

        userbase.LoginMethod(store=s,
                             domain=u'divmod.com',
                             localpart=u'joe',
                             protocol=u'zombie dance',
                             verified=True,
                             internal=False,
                             account=la)

        self.store = s
        self.loginAccount = la
        self.reset = PasswordResetResource(self.store)

    def testReset(self):
        """
        Test a password reset, as it might happen for a user
        """
        self.reset.resetPassword(
            self.reset.newAttemptForUser(u'joe@divmod.com'),
            u'more secret')

        self.assertEqual(self.loginAccount.password, u'more secret')
        self.assertEqual(self.store.count(_PasswordResetAttempt), 0)

    def testAttemptByKey(self):
        """
        Test that L{xmantissa.signup.PasswordResetResource.attemptByKey}
        knows the difference between valid and invalid keys
        """
        self.failUnless(self.reset.attemptByKey(
                            self.reset.newAttemptForUser(u'joe@divmod.com').key))
        self.failIf(self.reset.attemptByKey(u'not really a key'))

    def testAccountByAddress(self):
        """
        Test that L{xmantissa.signup.PasswordResetResource.accountByAddress}
        behaves similarly to L{axiom.userbase.LoginSystem.accountByAddress}
        """
        self.assertEqual(
            self.reset.accountByAddress(u'joe@divmod.com'),
            self.loginSystem.accountByAddress(u'joe', u'divmod.com'))

    def testHandleRequest(self):
        """
        Test that we correctly handle the request when we find a user and
        when we don't.
        """
        def myFunc(url, attempt):
            myFunc.emailsSent += 1
            myFunc.url = url
            myFunc.attempt = attempt
        myFunc.emailsSent = 0
        self.reset._sendEmail=myFunc 
        self.reset.handleRequestForUser(u'joe@divmod.com', 'http://oh.no/reset.html')
        self.assertEquals(myFunc.emailsSent, 1)
        self.assertEquals(myFunc.url, 'http://oh.no/reset.html')
        self.assertEquals(myFunc.attempt.username, u'joe@divmod.com')
        # Negative case. User does not exist. Email should not get sent
        self.reset.handleRequestForUser(u'no_joe@divmod.com', 'http://oh.no/reset.html')
        self.assertEquals(myFunc.emailsSent, 1)
