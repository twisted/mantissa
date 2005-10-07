from xmantissa.signup import emailRegex
from twisted.trial.unittest import TestCase

class EmailValidationTestCase(TestCase):
    def _validate(self, positive=(), negative=()):
        for addr in positive:
            self.failUnless(emailRegex.match(addr), "%s is not a valid address?" % addr)

        for addr in negative:
            self.failIf(emailRegex.match(addr), "%s is a valid address?" % addr)

    def testShort(self):
        self._validate(positive=("a@n.dk", "a.b@n-x.dk", "a_b@a-b-c.us"),
                       negative=("@", "@n.dk", "a.b@n%", "a@b_n.dk", "a@b.c", "x@d-."))

    def testSubdomains(self):
        self._validate(positive=("xyz@very.dodgy.info", "hyper@a.b.c.d.e.net", "a@a-b.c-d.e-f.gh"),
                       negative=("a@a.b.c.d", "a@b-c.d-e.f", "a@b-c.d-"))

    def testFunnyCharacters(self):
        self._validate(positive=("moe..@larry.curly",),
                       negative=("%bob@alice.jones.", "b$o@google.com"))
