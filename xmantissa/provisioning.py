
from zope.interface import implements

from twisted import plugin

from xmantissa import ixmantissa

class BenefactorFactory(object):
    implements(plugin.IPlugin, ixmantissa.IBenefactorFactory)

    def __init__(self, name, description, benefactorClass, dependencies=(), parameters={}):
        self.name = name
        self.description = description
        self.benefactorClass = benefactorClass
        self.deps = dependencies
        self.params = parameters

    def dependencies(self):
        return iter(self.deps)

    def parameters(self):
        return self.params

    def instantiate(self, **kw):
        return self.benefactorClass(**kw)
