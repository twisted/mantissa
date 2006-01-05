
import random, itertools

from twisted.trial import unittest

from axiom import store, userbase, item, attributes

from xmantissa import signup, offering
from xmantissa.plugins import adminoff, free_signup


class TestDependent(object):
    def __init__(self, name, dependencies):
        self.name = name
        self.deps = dependencies

    def dependencies(self):
        return iter(self.deps)

    def __repr__(self):
        return 'D<' + self.name + '>'

class DependencyOrderTestCase(unittest.TestCase):
    def testOrdering(self):
        a = TestDependent('a', [])
        b = TestDependent('b', [a])
        c = TestDependent('c', [a, b])
        d = TestDependent('d', [])
        e = TestDependent('e', [d, c])
        f = TestDependent('f', [c, d])
        g = TestDependent('g', [f])

        L = [a, b, c, d, e, f, g]

        for i in xrange(10):
            random.shuffle(L)
            inputList = L[:]
            order = signup.dependencyOrdered(L)
            for element in a, b, c, d, e, f, g:
                for dependency in element.deps:
                    self.failUnless(
                        order.index(element) > order.index(dependency),
                        "%r came before %r in %r (input was %r)" % (element, dependency,
                                                                    order, inputList))

class FakeTestBenefactor(item.Item):
    typeName = 'test_fake_test_benefactor'
    schemaVersion = 1

    endowed = attributes.integer(default=0)
    counter = attributes.inmemory()

    def endow(self, ticket, avatar):
        self.endowed = self.counter()

class MultiBenefactorTestCase(unittest.TestCase):
    def testAdding(self):
        s = store.Store()
        mb = signup.Multifactor(store=s)
        counter = itertools.count(1).next
        ftb = FakeTestBenefactor(store=s, counter=counter)
        ftb2 = FakeTestBenefactor(store=s, counter=counter)
        mb.add(ftb)
        mb.add(ftb2)
        mb.endow(None, None) # Hopefully no one ever cares about the ticket or
                             # the avatar here
        self.assertEquals(ftb.endowed, 1)
        self.assertEquals(ftb2.endowed, 2)

class SignupCreationTestCase(unittest.TestCase):
    def setUp(self):
        self.dbdir = self.mktemp()
        self.store = store.Store(self.dbdir)
        ls = userbase.LoginSystem(store=self.store)
        self.admin = ls.addAccount(u'admin', u'localhost', None)
        self.substore = self.admin.avatars.open()
        self.sc = signup.SignupConfiguration(store=self.substore)

    def _installTestOffering(self):
        io = offering.InstalledOffering(
            store=self.store,
            offeringName=u"mantissa",
            application=None)


    def testCreateSignup(self):
        self._installTestOffering()

        self.sc.createSignup(
            u'testuser@localhost',
            free_signup.freeTicket.itemClass,
            {'prefixURL': u'signup'},
            {adminoff.adminOffering.benefactorFactories[0]: {}})

        self.sc.createSignup(
            u'testuser@localhost',
            free_signup.freeTicketPassword.itemClass,
            {'prefixURL': u'signup-password'},
            {adminoff.adminOffering.benefactorFactories[0]: {}})
