from twisted.trial.unittest import TestCase
from twisted.python.reflect import qual
from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer
from xmantissa.product import Installation, Product
from zope.interface import implements, Interface

class IFoo(Interface):
    pass

class Foo(Item):
    implements(IFoo)
    powerupInterfaces = (IFoo,)
    attr = integer()

class IBaz(Interface):
    pass

class Baz(Item):
    implements(IBaz)
    powerupInterfaces = (IBaz,)
    attr = integer()

class ProductTest(TestCase):

    def test_product(self):
        s = Store()
        p = Product(store=s)
        p.types = [n.decode('ascii') for n in [qual(Foo), qual(Baz)]]
        userStore = Store()
        p.installProductOn(userStore)
        i = userStore.findUnique(Installation)
        self.assertEqual(i.types, p.types)

class InstallationTest(TestCase):

    def setUp(self):
        self.s = Store()
        self.product = Product()
        self.product.types = [n.decode('ascii') for n in [qual(Foo), qual(Baz)]]
        self.product.installProductOn(self.s)
        self.i = self.s.findUnique(Installation)
    def test_install(self):
        """
        Ensure that Installation installs instances of the types it is created with.
        """
        self.assertNotEqual(IFoo(self.s, None), None)
        self.assertNotEqual(IBaz(self.s, None), None)
        self.assertEqual(list(self.i.items), [self.s.findUnique(t) for t in [Foo, Baz]])

    def test_uninstall(self):
        """
        Ensure that Installation properly uninstalls all of the items it controls.
        """
        self.product.removeProductFrom(self.s)
        self.assertEqual(IFoo(self.s, None), None)
        self.assertEqual(IBaz(self.s, None), None)
        self.assertEqual(list(self.s.query(Installation)), [])

