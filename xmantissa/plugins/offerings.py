from xmantissa import people, offering, provisioning, website

peopleBenefactorFactory = provisioning.BenefactorFactory(
    name=u'People',
    description=u'Organizer, Address Book, etc',
    benefactorClass=people.PeopleBenefactor)

peopleOffering = offering.Offering(
    name=u'People',
    description=u'Mantissa People',

    siteRequirements=((None, website.WebSite),),
    appPowerups=(),
    benefactorFactories=(peopleBenefactorFactory,),
    themes=())

