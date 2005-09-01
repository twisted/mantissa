from twisted.application import service
from axiom import store

import xmantissa.website
import xmantissa.webadmin
import xmantissa.signup

application = service.Application('AXIOM')
store.StorageService(__file__.replace('.tac', '.axiom')).setServiceParent(application)
