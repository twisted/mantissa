from nevow.livetrial import testcase
from xmantissa.signup import ValidatingSignupForm
class FakeUserInfoSignup:

    def createUser(self, firstName, lastName, username, domain,
                   password, emailAddress):
        assert False, "Form shouldn't be submitted"

    def usernameAvailable(self, username, domain):
        return True

class TestUserInfoSignup(testcase.TestCase):
    jsClass = u'Mantissa.Test.UserInfoSignup'

    def getWidgetDocument(self):
        uis = FakeUserInfoSignup()
        vsf = ValidatingSignupForm(uis)
        vsf.setFragmentParent(self)
        return vsf


class TestSignupLocalpartValidation(TestUserInfoSignup):
    jsClass = u'Mantissa.Test.SignupLocalpartValidation'
