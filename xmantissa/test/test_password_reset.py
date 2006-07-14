from twisted.trial.unittest import TestCase
from axiom.store import Store
from axiom import userbase
from epsilon.extime import Time
from xmantissa.signup import PasswordReset, _PasswordResetAttempt

class PasswordResetTestCase(TestCase):
    def testStuff(self):
        s = Store()

        userbase.LoginSystem(store=s)
        passwordReset = PasswordReset(store=s)

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

        passwordReset.resetPassword(
            passwordReset.newAttemptForUser(u'joe@divmod.com'),
            u'more secret')

        self.assertEqual(la.password, u'more secret')
        self.assertEqual(s.count(_PasswordResetAttempt), 0)
