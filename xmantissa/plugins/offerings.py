from xmantissa import people, offering, website

peopleOffering = offering.Offering(
    name=u'People',
    description=u'Mantissa People',

    siteRequirements=((None, website.WebSite),),
    appPowerups=(),
    installablePowerups = [("People", "Organizer and Address Book", people.AddPerson)],
    loginInterfaces=(),
    themes=())

