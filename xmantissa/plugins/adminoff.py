from xmantissa import webadmin, offering, provisioning, stats
from axiom import iaxiom, scheduler, substore

adminOffering = offering.Offering(
    name = u'mantissa',
    description = u'Powerups for administrative control of a Mantissa server.',
    siteRequirements = [(None, webadmin.DeveloperSite),
                        (iaxiom.IScheduler, scheduler.Scheduler),
                        (None, substore.SubStoreStartupService)],
    appPowerups = [scheduler.SubScheduler, stats.StatsService],
    benefactorFactories = [
        provisioning.BenefactorFactory(
            u'admin',
            u'System-wide statistics display, Python REPL, and traceback monitoring.',
            webadmin.AdministrativeBenefactor)],
    loginInterfaces=(),
    themes = ())
