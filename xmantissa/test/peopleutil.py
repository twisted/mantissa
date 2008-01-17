"""
Helpful utilities for code which tests functionality related to
L{xmantissa.people}.
"""

from axiom.store import Store

from xmantissa.ixmantissa import IPeopleFilter
from xmantissa.people import Organizer

from epsilon.descriptor import requiredAttribute


class PeopleFilterTestMixin:
    """
    Mixin for testing L{IPeopleFilter} providers.  Requires the following
    attributes:

    @ivar peopleFilterClass: The L{IPeopleFilter} being tested.
    @type peopleFilterClass: L{IPeopleFilter} provider.

    @ivar peopleFilterName: The expected name of L{peopleFilterClass}.
    @type peopleFilterName: C{str}
    """
    peopleFilterClass = requiredAttribute('peopleFilterClass')
    peopleFilterName = requiredAttribute('peopleFilterName')


    def assertComparisonEquals(self, comparison):
        """
        Instantiate L{peopleFilterClass}, call
        L{IPeopleFilter.getPeopleQueryComparison} on it and assert that its
        result is equal to C{comparison}.

        @type comparison: L{axiom.iaxiom.IComparison}
        """
        peopleFilter = self.peopleFilterClass()
        actualComparison = peopleFilter.getPeopleQueryComparison(Store())
        # none of the Axiom query objects have meaningful equality
        # comparisons, but their string representations do.
        # this assertion should be addressed along with #2464
        self.assertEqual(str(actualComparison), str(comparison))


    def makeOrganizer(self):
        """
        Return an L{Organizer}.
        """
        return Organizer(store=Store())


    def test_implementsInterface(self):
        """
        Our people filter should provide L{IPeopleFilter}.
        """
        self.assertTrue(IPeopleFilter.providedBy(self.peopleFilterClass()))


    def test_organizerIncludesIt(self):
        """
        L{Organizer.getPeopleFilters} should include an instance of our
        L{IPeopleFilter}.
        """
        organizer = self.makeOrganizer()
        self.assertIn(
            self.peopleFilterClass,
            [filter.__class__ for filter in organizer.getPeopleFilters()])


    def test_filterName(self):
        """
        Our L{IPeopleFilter}'s I{filterName} should match L{peopleFilterName}.
        """
        self.assertEqual(
            self.peopleFilterClass().filterName, self.peopleFilterName)
