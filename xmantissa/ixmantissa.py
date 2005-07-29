
from zope.interface import Interface, Attribute

class IWebTheme(Interface):
    """
    Represents a directory full of theme information.
    """


class ISiteRootPlugin(Interface):
    """
    Plugin Interface for functionality provided at the root of the website.
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


class INavigableElement(Interface):
    """Tag interface used by the web navigation plugin system.

    Plugins for this interface are retrieved when generating the navigation
    user-interface.  Each result has C{getTabs} invoked, after which the
    results are merged and the result used to construct various top- and
    secondary-level \"tabs\" which can be used to visit different parts of
    the application.
    """

    def getTabs():
        """Retrieve data about this elements navigation.

        This returns a list of C{quotient.appnav.Tab}s.

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
    """

    live = Attribute("""

    A boolean, telling us whether or not this fragment requires a LivePage to
    function properly.

    """)


class ITab(Interface):
    """
    Abstract, non-UI representation of a tab that shows up in the UI.  The only
    concrete representation is xmantissa.webnav.Tab
    """

