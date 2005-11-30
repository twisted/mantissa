
from zope.interface import implements

from twisted import plugin

from xmantissa import ixmantissa

class BenefactorFactory(object):
    implements(plugin.IPlugin, ixmantissa.IBenefactorFactory)

    def __init__(self, name, description, benefactorClass, dependencies=()):
        self.name = name
        self.description = description
        self.benefactorClass = benefactorClass
        self.deps = dependencies

    def dependencies(self):
        return iter(self.deps)

    def parameters(self):
        return self.benefactorClass.getSchema()

    def instantiate(self, **kw):
        return self.benefactorClass(**kw)
