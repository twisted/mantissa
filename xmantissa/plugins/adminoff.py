from xmantissa import webadmin, offering, stats
from xmantissa.webadmin import (TracebackViewer, LocalUserBrowser,
                                DeveloperApplication, BatchManholePowerup)
from xmantissa.signup import SignupConfiguration
from axiom import iaxiom, scheduler

adminOffering = offering.Offering(
    name = u'mantissa',
    description = u'Powerups for administrative control of a Mantissa server.',
    siteRequirements = [(None, webadmin.DeveloperSite),
                        (iaxiom.IScheduler, scheduler.Scheduler)],
    appPowerups = [scheduler.SubScheduler, stats.StatsService],
    installablePowerups = [("Signup Configuration", "Allows configuration of signup mechanisms", SignupConfiguration),
                           ("Traceback Viewer", "Allows viewing unhandled exceptions which occur on the server", TracebackViewer),
                           ("Local User Browser", "A page listing all users existing in this site's store.", LocalUserBrowser),
                           ("Admin REPL", "An interactive python prompt.", DeveloperApplication),
                           ("Batch Manhole", "Enables ssh login to the batch-process manhole", BatchManholePowerup),
                           ("Offering Configuration", "Allows installation of Offerings on this site", offering.OfferingConfiguration)],
    loginInterfaces=(),
    themes = ())
