# -*- test-case-name: xmantissa.test -*-

"""
Public interfaces used in Mantissa.
"""

from zope.interface import Interface, Attribute

from nevow.inevow import IRenderer


class IColumn(Interface):
    """
    Represents a column that can be viewed via a scrolling table, and provides
    hints & metadata about the column.
    """

    def sortAttribute():
        """
        @return: a sortable axiom.attribute, or None if this column cannot be
        sorted
        """


    def extractValue(model, item):
        """
        @type model: L{xmantissa.tdb.TabularDataModel}
        @param item: the L{axiom.item.Item} from which to extract column value

        @return: the underlying value for this column
        """


    def getType():
        """
        returns a string describing the type of this column, or None
        """


    def toComparableValue(value):
        """
        Convert a value received from the client into one that can be compared
        like-for-like with L{sortAttribute}, when executing an axiom query.

        (Callers should note that this is new as of Mantissa 0.6.6, and be
        prepared to deal with its absence in legacy code.)
        """


    attributeID = Attribute(
        """
        An ASCII-encoded str object uniquely describing this column.
        """)



class ITemplateNameResolver(Interface):
    """
    Loads Nevow document factories from a particular theme based on simple
    string names.
    """

    def getDocFactory(name, default=None):
        """
        Retrieve a Nevow document factory for the given name.

        @param name: a short string that names a fragment template for
        development purposes.

        @return: a Nevow docFactory
        """



class IPreferenceAggregator(Interface):
    """
    Allows convenient retrieval of individual preferences
    """

    def getPreferenceCollections():
        """
        Return a list of all installed L{IPreferenceCollection}s
        """

    def getPreferenceValue(key):
        """
        Return the value of the preference associated with "key"
        """

class ISearchProvider(Interface):
    """
    Represents an Item capable of searching for things
    """

    def count(term):
        """
        Return the number of items currently associated with the given
        (unprocessed) search string
        """

    def search(term, keywords=None, count=None, offset=0, sortAscending=True):
        """
        Query for items which contain the given term.

        @type term: C{unicode}
        @param keywords: C{dict} mapping C{unicode} field name to C{unicode}
        field contents.  Search results will be limited to documents with
        fields of these names containing these values.
        @type count: C{int} or C{NoneType}
        @type offset: C{int}, default is 0
        @param sortAscending: should the results be sorted ascendingly
        @type sortAscending: boolean

        @rtype: L{twisted.internet.defer.Deferred}
        @return: a Deferred which will fire with an iterable of
        L{search.SearchResult} instances, representing C{count} results for the
        unprocessed search represented by C{term}, starting at C{offset}.  The
        bounds of offset and count will be within the value last returned from
        L{count} for this term.
        """



class ISearchAggregator(Interface):
    """
    An Item responsible for interleaving and displaying search results
    obtained from available ISearchProviders
    """

    def count(term):
        """
        same as ISearchProviders.count, but queries all search providers
        """

    def search(term, keywords, count, offset, sortAscending):
        """
        same as ISearchProvider.search, but queries all search providers
        """

    def providers():
        """
        returns the number of available search providers
        """



class IFulltextIndexer(Interface):
    """
    A general interface to a low-level full-text indexer.
    """
    def add(document):
        """
        Add the given document to this index.

        This method may only be called in the batch process (it will
        synchronously invoke an indexer method which may block or cause a
        segfault).
        """


    def remove(document):
        """
        Remove the given document from this index.

        This method may be called from any process.
        """



class IFulltextIndexable(Interface):
    """
    Something which can be indexed for later search.
    """
    def uniqueIdentifier():
        """
        @return: a C{str} uniquely identifying this item.
        """


    def textParts():
        """
        @return: an iterable of unicode strings to be indexed as the text of
        this item.
        """


    def keywordParts():
        """
        @return: a C{dict} mapping C{str} to C{unicode} of additional
        metadata.  It will be possible to search on these fields using
        L{ISearchAggregator.search}.
        """


    def documentType():
        """
        @return: a C{str} uniquely identifying the type of this item.  Like
        the return value of L{keywordParts}, it will be possible to search
        for this using the C{"documentType"} key in the C{keywords} argument
        to L{ISearchAggregator.search}.
        """


    def sortKey():
        """
        @return: A unicode string that will be used as the key when sorting
        search results comprised of items of this type.
        """



class IStaticShellContent(Interface):
    """
    Represents per-store header/footer content thats used to buttress
    the shell template
    """

    def getHeader():
        """
        Returns stan to be added to the page header.  Can return None
        if no header is desired.
        """

    def getFooter():
        """
        Returns stan to be added to the page footer.  Can return None
        if no footer is desired.
        """

class ISiteRootPlugin(Interface):
    """
    Plugin Interface for functionality provided at the root of the website.

    This interface is queried for on the Store by website.WebSite when
    processing an HTTP request.  Things which are installed on a Store using
    s.powerUp(x, ISiteRootPlugin) will be visible to individual users when
    installed on a user's store or visible to the general public when installed
    on a top-level store.
    """

    def resourceFactory(segments):
        """Get an object that provides IResource

        @type segments: list of str, representing decoded requested URL
        segments

        @return: None or a two-tuple of the IResource provider and the segments
        to pass to its locateChild.
        """

class ISessionlessSiteRootPlugin(Interface):
    """
    Extremely similar to ISiteRootPlugin except access is not mediated by
    nevow.guard.
    """


class ICustomizable(Interface):
    """
    Factory for creating IResource objects which can be customized for
    a specific user.
    """
    def customizeFor(avatarName):
        """
        Retrieve a IResource provider specialized for the given avatar.

        @type avatarName: C{unicode}
        @param avatarName: The user for whom to return a specialized resource.

        @rtype: C{IResource}
        @return: A public-page resource, possibly customized for the
        indicated user.
        """

class IPublicPage(Interface):
    """
    I am a marker interface designed to segregate the private view (designated
    using the normal IResource) from the public view (returned from my
    getResource) of a substore.
    """

    index = Attribute("""
    A boolean indicating whether a link to this page will show up on
    the front index page.
    """)

    def getResource():
        """
        Retrieve an IResource provider meant to serve as the
        public-facing view.  The retrieved object will provide
        IResource.
        """

class ICustomizablePublicPage(Interface):
    """
    Don't use this.  Delete it if you notice it still exists but
    upgradePublicWeb2To3 has been removed.
    """

class IWebTranslator(Interface):
    """
    Provide methods for naming objects on the web, and vice versa.
    """

    def fromWebID(webID):
        """
        @param webID: A string that identifies an item through this translator.

        @return: an Item, or None if no Item is found.
        """

    def toWebID(item):
        """
        @param item: an item in the same store as this translator.

        @return: a string, shorter than 80 characters, which is an opaque
        identifier that may be used to look items up through this translator
        using fromWebID (or the legacy 'linkFrom')
        """


    def linkTo(storeID):
        """
        @param storeID: The Store ID of an Axiom item.

        @rtype: C{str}
        @return: An URL which refers to the item with the given Store ID.
        """

    def linkFrom(webID):
        """
        The inverse of L{linkTo}
        """

class INavigableElement(Interface):
    """Tab interface used by the web navigation plugin system.

    Plugins for this interface are retrieved when generating the navigation
    user-interface.  Each result has C{getTabs} invoked, after which the
    results are merged and the result used to construct various top- and
    secondary-level \"tabs\" which can be used to visit different parts of
    the application.
    """

    def getTabs():
        """Retrieve data about this elements navigation.

        This returns a list of C{xmantissa.appnav.Tab}s.

        For example, a powerup which wanted to install navigation under the
        Divmod tab would return this list:::

        [Tab("Divmod", quotient.iquotient.ISummaryPage, 1.0
             children=[
                    Tab("Summary", quotient.iquotient.ISummaryPage, 1.0),
                    Tab("Inbox", lambda x:
                        IRootPool(x).getNamedElement(
                            'Mail Folders').getNamedElement('Inbox'),
                        0.8)
                    ])]
        """

class INavigableFragment(Interface):
    """
    Register an adapter to this interface in order to provide web UI content
    within the context of the 'private' application with navigation, etc.

    You will still need to produce some UI by implementing INavigableElement
    and registering a powerup for that as well, which allows users to navigate
    to this object.

    The primary requirement of this interface is that providers of it also
    provide L{nevow.inevow.IRenderer}.  The easiest way to achieve this is to
    subclass L{nevow.page.Element}.
    """

    live = Attribute("""
    A boolean, telling us whether or not this fragment requires a LivePage to
    function properly.
    """)

    fragmentName = Attribute("""
    The name of this fragment; a string used to look up the template from the
    current theme(s).

    For quick-and-dirty development, this may be set to None and instead you
    can set a docFactory.  While this will work, it's not generally
    recommended, because then your application's visual style will be
    inextricably welded to its front-end code.
    """)

    docFactory = Attribute("""
    Nevow-style docFactory object.  Must be set if fragmentName is not.
    """)


    def head():
        """
        Provide some additional content to be included in the <head>
        section of the page when this fragment is being rendered.

        May return None if nothing needs to be added there.
        """


    def locateChild(self, ctx, segments):
        """
        INavigableFragments may optionally provide a locateChild method similar
        to the one found on L{nevow.inevow.IResource.locateChild}.  You may
        implement this method if your INavigableFragment contains any resources
        which it may need to refer to with hyperlinks when rendered.  Please
        note that an INavigableFragment may be rendered on any page within an
        application, and that hyperlinks to resources returned from this method
        must always be to /private/<your-webid>/..., not the current page's
        URL, if you are using the default
        L{xmantissa.webapp.PrivateApplication} URL dispatcher.

        (There is a slight bug in the calling code's handling of Deferreds.
        If you wish to delegate to normal child-resource handling, you must
        return rend.NotFound exactly, not a Deferred which fires it.)
        """



class ITab(Interface):
    """
    Abstract, non-UI representation of a tab that shows up in the UI.  The only
    concrete representation is xmantissa.webnav.Tab
    """

class IBenefactor(Interface):
    """
    Make accounts for users and give them things to use.
    """

    def endow(ticket, avatar):
        """
        Make a user and return it.  Give the newly created user new powerups or
        other functionality.

        This is only called when the user has confirmed the email address
        passed in by receiving a message and clicking on the link in the
        provided email.
        """

    def deprive(ticket, avatar):
        """
        Remove the increment of functionality or privilege that we have previously
        bestowed upon the indicated avatar.
        """

class IBenefactorFactory(Interface):
    """A factory which describes and creates IBenefactor providers.
    """

    def dependencies():
        """
        Return an iterable of other IBenefactorFactory providers that this one
        depends upon, and must be installed before this one is invoked.
        """

    def parameters():
        """
        Return a description of keyword parameters to be passed to instantiate.

        @rtype: A list of 4-tuples.  The first element of each tuple
        is a keyword argument to L{instantiate}.  The second describes
        the type of prompt to present for this field.  The third is a
        one-argument callable will should be invoked with a string the
        user supplies and should return the value for this keyword
        argument.  The fourth is a description of the purpose of this
        keyword argument.
        """

    def instantiate(**kw):
        """
        Create an IBenefactor provider and return it.
        """


class IQ2QService(Interface):

    q2qPortNumber = Attribute(
        """
        The TCP port number on which to listen for Q2Q connections.
        """)

    inboundTCPPortNumber = Attribute(
        """
        The TCP port number on which to listen for Q2Q data connections.
        """)

    publicIP = Attribute(
        """
        Dotted-quad format string representing the IP address via
        which this service is exposed to the public internet.
        """)

    udpEnabled = Attribute(
        """
        A boolean indicating whether or not PTCP connections will be
        allowed or attempted.
        """)

    def listenQ2Q(fromAddress, protocolsToFactories, serverDescription):
        """
        @see: L{vertex.q2q.Q2QService.connectQ2Q}
        """

    def connectQ2Q(fromAddress, toAddress, protocolName, protocolFactory,
                   usePrivateCertificate=None, fakeFromDomain=None,
                   chooser=None):
        """
        @see: L{vertex.q2q.Q2QService.connectQ2Q}
        """

class IPreferenceCollection(Interface):
    """
    I am an item that groups preferences into logical chunks.
    """

    def getPreferences():
        """
        Returns a mapping of preference-name->preference-value.
        """

    def getSections():
        """
        Returns a sequence of INavigableFragments or None. These fragments
        will be displayed alongside preferences under this collections's
        settings group.
        """

    def getPreferenceAttributes():
        """
        Returns a sequence of L{xmantissa.liveform.Parameter} instances - one
        for each preference.  The names of the parameters should correspond
        to the attribute names of the preference attributes on this item.
        """

    def getTabs():
        """
        Like L{ixmantissa.INavigableElement.getTabs}, but for preference tabs
        """

class ITemporalEvent(Interface):
    """
    I am an event which happens at a particular time and has a specific duration.
    """

    startTime = Attribute("""
    An extime.Time.  The start-point of this event.
    """)

    endTime = Attribute("""
    An extime.Time.  The end-point of this event.
    """)


class IDateBook(Interface):
    """
    A source of L{IAppointment}s which have times associated with them.
    """

    def eventsBetween(startTime, endTime):
        """
        Retrieve events which overlap a particular range.

        @param startTime: an L{epsilon.extime.Time} that begins a range.
        @param endTime: an L{epsilon.extime.Time} that ends a range.

        @return: an iterable of L{ITemporalEvent} providers.
        """



class IContactType(Interface):
    """
    A means by which communication with a L{Person} might occur.  For example,
    a telephone number.
    """
    allowMultipleContactItems = Attribute("""
    C{bool} indicating whether more than one contact item of this type can be
    created of a particular L{Person}.
    """)

    def getParameters(contactInfoItem):
        """
        Return some liveform parameters, one for each piece of information that is
        needed to construct a contact info item of this type.

        If C{contactInfoItem} is supplied, implementations may return C{None}
        to indicate that the given contact item is not editable.

        @param contactInfoItem: An existing contact info item of this type, or
        C{None}.  If not C{None}, then the current values of the contact info
        type will be used to provide suitable defaults for the parameters that
        are returned.
        @type contactInfoItem: L{axiom.item.Item} subclass.

        @return: Some liveform parameters or C{None}.
        @rtype: C{NoneType} or C{list} of L{xmantissa.liveform.Parameter}.
        """


    def createContactItem(person, **parameters):
        """
        Create a new instance of this contact type for the given person.

        @type person: L{Person}
        @param person: The person to whom the contact item pertains.

        @param parameters: The form input key/value pairs as returned by the
            L{xmantissa.liveform.LiveForm} constructed from L{getParameters}'s
            parameter instances.

        @return: The created contact item or C{None} if one was not created for
            any reason.
        """


    def getContactItems(person):
        """
        Return an iterator of contact items created by this contact type for
        the given person.

        @type person: L{Person}
        @param person: The person to whom the contact item pertains.
        """


    def uniqueIdentifier():
        """
        Return a C{unicode} string which, for the lifetime of a single Python
        process, uniquely identifies this type of contact information.
        """


    def descriptiveIdentifier():
        """
        A descriptive name for this type of contact information.

        @rtype: C{unicode}
        """



    def getEditorialForm(contact):
        """
        Return a L{LiveForm} which will allow the given contact item to be
        edited.

        @param contact: An L{Item} previously returned by this provider's
            C{createContactItem} method for which a form should be returned.

        @rtype: L{LiveForm}
        """


    def editContactItem(contact, **parameters):
        """
        Update the given contact item to reflect the new parameters.

        @param **parameters: The form input key/value pairs, as produced by the
            L{LiveForm} returned by L{ L{getEditorialForm}.
        """


    def getReadOnlyView(contact):
        """
        Return an L{IRenderer} which will display the given contact.
        """



class IOrganizerPlugin(Interface):
    """
    Powerup which provides additional functionality to Mantissa
    People.  Organizer plugins add support for new kinds of person
    data (for example, one Organizer plugin might add support for
    contact information: physical addresses, email addresses,
    telephone numbers, etc.  Another plugin might retrieve and
    aggregate blog posts, or provide an interface for configuring
    sharing permissions).
    """
    def getContactTypes():
        """
        Return an iterator of L{IContactType} providers supplied by this
        plugin.
        """


    def personCreated(person):
        """
        Called when a new L{Person} is created.
        """


    def personNameChanged(person, oldName):
        """
        Called after a L{Person} item's name has been changed.

        @type person: L{Person}
        @param person: The person whose name is being changed.

        @type oldName: C{unicode}
        @param oldName: The previous value of L{{Person.name}.
        """


    def contactItemCreated(contact):
        """
        Called when a new contact item is created.

        @param contact: The new contact item.  It may be any object returned by
            an L{IContactType.createContactItem} implementation.
        """


    def contactItemEdited(contact):
        """
        Called when an existing contact item has been edited.

        @param contact: The contact item.
        """


    def personalize(person):
        """
        Return some plugin-specific state for the given person.

        @param person: A L{xmantissa.person.Person} instance.

        @return: something adaptable to L{IPersonFragment}
        """



class IPersonFragment(Interface):
    """
    Web facet of a personalized L{IOrganizerPlugin}, e.g.
    widget that provides web UI for associating RSS feeds
    with a person, or shows a list of emails recently received
    from them.
    """

    title = Attribute("""
    The title of this fragment.  This will be displayed as the title
    of the tab in the tabbed pane that contains this fragment
    """)

class IOffering(Interface):
    """
    Describes a product, service, application, or other unit of functionality
    which can be added to a Mantissa server.
    """

    name = Attribute("""
    What it is called.
    """)

    description = Attribute("""
    What it is.
    """)

    siteRequirements = Attribute("""
    A list of 2-tuples of (interface, powerupClass) of Axiom Powerups which
    will be installed on the Site store when this offering is installed if the
    store cannot be adapted to the given interface.
    """)

    appPowerups = Attribute("""
    A list of Axiom Powerups which will be installed on the App store when this
    offering is installed.  May be None if no App store is required (in this
    case, none will be created).
    """)

    benefactorFactories = Attribute("""
    A list of IBenefactorFactory providers
    """)

    loginInterfaces = Attribute("""
    A list of 2-tuples of (interface, description) of interfaces
    implemented by avatars provided by this offering, and human
    readable descriptions of the service provided by logging into
    them. Used by the statistics reporting system to label graphs of
    login activity.
    """)

    themes = Attribute("""
    Sequence of L{xmantissa.webtheme.XHTMLDirectoryTheme} instances,
    constituting themes that belong to this offering
    """)

    version = Attribute("""
    L{twisted.python.versions.Version} instance indicating the version of
    this offering.  If included, the Version's value will be displayed to
    users once the offering is installed.  Defaults to None.
    """)


class ISignupMechanism(Interface):
    """
    Describe an Item which can be instantiated to add a means of
    signing up to a Mantissa server.
    """

    name = Attribute("""
    What it is called.
    """)

    description = Attribute("""
    What it does.
    """)

    itemClass = Attribute("""
    An Axiom Item subclass which will be instantiated and added to the
    site store when this signup mechanism is selected.  The class
    should implement L{ISessionlessSiteRootPlugin} or
    L{ISiteRootPlugin}.
    """)

    configuration = Attribute("""
    XXX EDOC ME
    """)



class IProtocolFactoryFactory(Interface):
    """
    Powerup interface for Items which can create Twisted protocol factories.
    """
    def getFactory():
        """
        Return a Twisted protocol factory.
        """



class IParameter(Interface):
    """
    Description of a single variable which will take on a value from external
    input and be used to perform some calculation or action.

    For example, an HTML form is a collection of IParameters, most likely one
    per input tag.  When POSTed, each input supplies its text value as the
    external input to a corresponding IParameter provider and the resulting
    collection is used to respond to the POST somehow.

    NOTE: This interface is highly unstable and subject to grossly incompatible
    changes.
    """

    # XXX - These shouldn't be attributes of IParameter, I expect.  They are
    # both really view things.  Either they goes into the template which is
    # used for this parameter (as an explanation to a user what the parameter
    # is), or some code which creates the view supplies them as parameters to
    # that object (in which case, it's probably more of a unique identifier in
    # that view context for this parameter). -exarkun
    name = Attribute(
        """
        A short C{unicode} string uniquely identifying this parameter within
        the context of a collection of L{IParameter} providers.
        """)

    label = Attribute(
        """
        A short C{unicode} string uniquely identifying this parameter within
        the context of a collection of L{IParameter} providers.
        """)

    # XXX - Another thing which belongs on the view.  Who even says this will
    # be rendered to an HTML form?
    type = Attribute(
        """
        One of C{liveform.TEXT_INPUT}, C{liveform.PASSWORD_INPUT},
        C{liveform.TEXTAREA_INPUT}, C{liveform.FORM_INPUT},
        C{liveform.RADIO_INPUT}, or C{liveform.CHECKBOX_INPUT} indicating the
        kind of input interface which will be presented for this parameter.
        """)

    # XXX - This shouldn't be an attribute of IParameter.  It's intended to be
    # displayed to end users, it belongs in a template.
    description = Attribute(
        """
        A long C{unicode} string explaining the meaning or purpose of this
        parameter.  May be C{None} to provide the end user with an unpleasant
        experience.
        """)

    # XXX - At this level, a default should be a structured object, not a
    # unicode string.  There is presently no way to serialize a structured
    # object into the view, though, so we use unicode here.
    default = Attribute(
        """
        A C{unicode} string which will be initially presented in the view as
        the value for this parameter, or C{None} if no such value should be
        presented.
        """)


    def viewFactory(parameter, default):
        """
        @type view: L{IParameter} provider
        @param view: The parameter for which to create a view.

        @param default: An object to return if no view can be created for the
            given parameter.

        @rtype: L{IParameterView} provider
        """


    # XXX - This is most definitely a view thing.
    def compact():
        """
        Mutate the parameter so that when a view object is created for it, it
        is more visually compact than it would otherwise have been.
        """


    def fromInputs(inputs):
        """
        Extract the value for this parameter from the given submission
        dictionary and return a structured value for this parameter.
        """



class IParameterView(IRenderer):
    """
    View interface for an individual LiveForm parameter.
    """
    patternName = Attribute("""
    Short string giving the name of the pattern for this parameter view.  Must
    be one of C{'text'}, C{'password'}, C{'repeatable-form'} or C{'choice'}.
    """)

    def setDefaultTemplate(tag):
        """
        Called by L{xmantissa.liveform.LiveForm} to specify the default
        template for this view.

        @type tag: L{nevow.stan.Tag} or C{nevow.stan.Proto}
        """


__all__ = [
    'IColumn', 'ITemplateNameResolver', 'IPreferenceAggregator',
    'ISearchProvider', 'ISearchAggregator', 'IFulltextIndexer',
    'IFulltextIndexable', 'IStaticShellContent', 'ISiteRootPlugin',
    'ISessionlessSiteRootPlugin', 'ICustomizable', 'IPublicPage',
    'ICustomizablePublicPage', 'IWebTranslator', 'INavigableElement',
    'INavigableFragment', 'ITab', 'IBenefactor', 'IBenefactorFactory',
    'IQ2QService', 'IPreferenceCollection', 'ITemporalEvent', 'IDateBook',
    'IOrganizerPlugin', 'IPersonFragment', 'IOffering', 'ISignupMechanism',
    'IProtocolFactoryFactory', 'IParameterView',
    ]
