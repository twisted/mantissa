
from zope.interface import Interface, Attribute

class IWebTheme(Interface):
    """
    Represents a directory full of theme information.
    """
    def head():
        """
        Provide some additional content to be included in the <head>
        section of the page when themed fragments are being rendered

        if not None, the returned value will appear in the head tag
        before the return result of the fragment's head()
        """

class IPreference(Interface):
    """
    Represents the display logic of an individual preference
    """

    key = Attribute("Internal, unique (per-store) identifier for this preference")
    value = Attribute("The current value of this preference")
    name = Attribute("Short, displayable title, e.g. 'Preferred Widget'")
    collection = Attribute("Reference to my IPreferenceCollection")
    description = Attribute("Longer, helpful summary of the utility of this preference")

    def choices():
        """
        If this is a multiple choice preference, returns all possible values.
        otherwise returns None.
        """

    def valueToDisplay(value):
        """
        Returns a displayable version of the preferences value.  e.g.
        True -> "Yes"
        """

    def displayToValue(display):
        """
        inverse of "valueToDisplay".  raises prefs.PreferenceValidationError
        if the "display" argument is not a valid preference value
        """

class IPreferenceAggregator(Interface):
    """
    Allows convenient retrieval of individual preferences
    """

    def getPreference(key):
        """
        Return the preference associated with "key"
        """

    def getPreferenceValue(key):
        """
        Return the value of the preference associated with "key"
        """

class IPreferenceCollection(Interface):
    """
    Represents an Item that aggregates preferences associated with some
    functionality - i.e. there might be a core mantissa Preference Collection,
    and an AcmeWidgets Preference Collection that extends the set of available
    preferences.
    """

    name = Attribute("The name of this collection, e.g. 'Mantissa Preferences'")

    def getPreferences():
        """
        Returns a mapping of key->preference for all preferences
        in this collection
        """

    def setPreferenceValue(pref, value):
        """
        Update and persist the value of the given preference
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

    def search(term, count, offset):
        """
        Return a sequence of search.SearchResult instances, representing
        'count' results for unprocessed string 'term', starting from 'offset'.
        The bounds of offset & count will be within the value last returned from
        count() for this term
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

    def search(term, count, offset):
        """
        same as ISearchProvider.search, but queries all search providers
        """

    def providers():
        """
        returns the number of available search providers
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


class IPublicPage(Interface):
    """
    Factory for creating public-facing resources, either to be viewed
    anonymously or by a logged in user.
    """
    def anonymousResource():
        """Return an IResource
        """

    def resourceForUser(username):
        """
        Create and return an IResource object.

        @type username: C{unicode}
        @param username: The name of the user for whom to create the resource.

        @rtype: C{IResource}
        @return: A public-page resource, possibly customized for the
        indicated user.
        """

class ICustomizablePublicPage(Interface):
    """
    Factory for creating IResource objects which can be customized for
    a specific user.
    """
    def getPublicPageFactory():
        """
        Return an IPublicPage provider.
        """

class IWebTranslator(Interface):
    """
    Provide methods for naming objects on the web, and vice versa.
    """

    def linkTo(storeID):
        """
        @param storeID: The Store ID of an Axiom item.

        @rtype: C{str}
        @return: An URL which refers to the item with the given Store ID.
        """

    def linkFrom(webID):
        """
        The inverse of L{linkTO}
        """

    def getDocFactory(name):
        """
        Retrieve a Nevow document factory for the given name.
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

    The main thing that this interface requires is that the element passed in
    be 'flattenable', meaning that it can be flattened as part of a Nevow stan
    tree.  The easiest way to achieve this is to subclass
    L{nevow.rend.Fragment}; hence the interface name.
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

class ITab(Interface):
    """
    Abstract, non-UI representation of a tab that shows up in the UI.  The only
    concrete representation is xmantissa.webnav.Tab
    """

class IBenefactor(Interface):
    """
    Make accounts for users and give them things to use.
    """

    def endow(emailAddress):
        """
        Make a user and return it.  Give the newly created user new powerups or
        other functionality.

        This is only called when the user has confirmed the email address
        passed in by receiving a message and clicking on the link in the
        provided email.
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


class ITemporalEvent(Interface):
    """
    I am an event which happens at a particular time and has a specific duration.
    """

    startTime = Attribute("""
    An extime.Time.  The start-point of this event.
    """)

    endTime = Attribute("""
    An extime.Time.  The end-point fo this event.
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
