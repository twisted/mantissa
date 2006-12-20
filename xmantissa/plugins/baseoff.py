from xmantissa.webtheme import MantissaTheme
from xmantissa import offering
import xmantissa
from nevow.inevow import IResource

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
    version=xmantissa.version)
