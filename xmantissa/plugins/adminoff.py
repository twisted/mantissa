
from xmantissa import webadmin, offering, provisioning

adminOffering = offering.Offering(
    name = u'mantissa',
    description = u'Powerups for administrative control of a Mantissa server.',
    siteRequirements = [webadmin.DeveloperSite],
    appPowerups = [],
    benefactorFactories = [
        provisioning.BenefactorFactory(
            u'admin',
            u'System-wide statistics display, Python REPL, and traceback monitoring.',
            webadmin.AdministrativeBenefactor)])
