
from twisted.python.filepath import FilePath

from nevow.inevow import IResource

from xmantissa.webtheme import MantissaTheme
from xmantissa import offering
import xmantissa

baseOffering = offering.Offering(
    name=u'mantissa-base',
    description=u'Basic Mantissa functionality',
    siteRequirements=(),
    appPowerups=(),
    installablePowerups=(),
    loginInterfaces = [(IResource, "Web logins")],
    # priority should be 0 for pretty much any other theme.  'base' is the theme
    # that all other themes should use as a reference for what elements are
    # required.

    themes=(MantissaTheme('base', 1),),
    staticContentPath=FilePath(xmantissa.__file__).sibling('static'),
    version=xmantissa.version)
