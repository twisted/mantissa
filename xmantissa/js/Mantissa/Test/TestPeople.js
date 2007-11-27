// Copyright (c) 2007 Divmod.
// See LICENSE for details.

/**
 * Tests for L{Mantissa.ScrollTable.ScrollModel}
 */

// import Divmod.Defer
// import Divmod.UnitTest
// import Mantissa.People
// import Nevow.Test.WidgetUtil

Mantissa.Test.TestPeople.StubWidget = Divmod.Class.subclass(
    'Mantissa.Test.TestPeople.StubWidget');
/**
 * Stub implementation of L{Nevow.Athena.Widget} used by tests to verify that
 * the correct remote calls are made.
 *
 * @ivar node: The widget's node.
 *
 * @ivar results: An array with one object for each time callRemote has been
 *     invoked.  The objects have the following properties::
 *
 *    deferred: The L{Divmod.Defer.Deferred} which was returned by the
 *              corresponding callRemote call.
 *    method: The name of the remote method which was invoked.
 *    args: An array of the remaining arguments given to the callRemote call.
 *
 * @ivar wasDetached: A flag indicating whether C{detach} was called.
 */
Mantissa.Test.TestPeople.StubWidget.methods(
    function __init__(self) {
        self.node = document.createElement('span');
        self.results = [];
        self.removedRows = [];
        self.wasDetached = false;
    },

    /**
     * Record an attempt to call a method on the server.
     */
    function callRemote(self, method) {
        var result = {};
        result.deferred = Divmod.Defer.Deferred();
        result.method = method;
        result.args = [];
        for (var i = 2; i < arguments.length; ++i) {
            result.args.push(arguments[i]);
        }
        self.results.push(result);
        return result.deferred;
    },

    /**
     * Pretend to be a ScrollingWidget and remember which rows have been
     * removed.
     */
    function removeRow(self, index) {
        self.removedRows.push(index);
    },

    /**
     * Record an attempt to detach this widget.
     */
    function detach(self) {
        self.wasDetached = true;
    });


Mantissa.Test.TestPeople.StubPersonForm = Divmod.Class.subclass(
    'Mantissa.Test.TestPeople.StubPersonForm');
/**
 * Stub implementation of L{Mantissa.People.AddPersonForm} and
 * L{Mantissa.People.EditPersonForm}.
 *
 * @ivar submissionObservers: An array of the objects passed to
 * L{observeSubmission}
 */
Mantissa.Test.TestPeople.StubPersonForm.methods(
    function __init__(self) {
        self.submissionObservers = [];
    },

    /**
     * Ignore the widget hierarchy.
     */
    function setWidgetParent(self, parent) {
    },

    /**
     * Remember an observer in L{submissionObservers}.
     */
    function observeSubmission(self, observer) {
        self.submissionObservers.push(observer);
    });


Mantissa.Test.TestPeople.StubOrganizerView = Divmod.UnitTest.TestCase.subclass(
    'Mantisa.Test.TestPeople.StubOrganizerView');
/**
 * Stub L{Mantissa.People.OrganizerView}.
 *
 * @ivar detailNode: The current detail node.
 * @type detailNode: DOM Node or C{null}.
 *
 * @ivar editLinkVisible: Whether the "edit" link is currently visible.
 * Defaults to C{false}.
 * @type editLinkVisible: C{Boolean}
 *
 * @ivar deleteLinkVisible: Whether the "delete" link is currently visible.
 * Defaults to C{false}.
 * @type deleteLinkVisible: C{Boolean}
 *
 * @ivar cancelFormLinkVisible: Whether the "cancel form" link is currently
 * visible.  Defaults to C{false}.
 * @type cancelFormLinkVisible: C{Boolean}
 *
 * @ivar organizerPositionSet: Whether the I{organizer} node has been
 * positioned.  Defaults to C{false}.
 * @type organizerPositionSet: C{Boolean}
 */
Mantissa.Test.TestPeople.StubOrganizerView.methods(
    function __init__(self) {
        self.detailNode = null;
        self.editLinkVisible = false;
        self.deleteLinkVisible = false;
        self.cancelFormLinkVisible = false;
        self.organizerPositionSet = false;
    },

    /**
     * Set L{organizerPositionSet} to C{true}.
     */
    function setOrganizerPosition(self) {
        self.organizerPositionSet = true;
    },

    /**
     * Set L{detailNode} to C{node}.
     */
    function setDetailNode(self, node) {
        self.detailNode = node;
    },

    /**
     * Set L{detailNode} to C{null}.
     */
    function clearDetailNodes(self) {
        self.detailNode = null;
    },

    /**
     * Set L{deleteLinkVisible} to C{true}.
     */
    function showDeleteLink(self) {
        self.deleteLinkVisible = true;
    },

    /**
     * Set L{deleteLinkVisible} to C{false}.
     */
    function hideDeleteLink(self) {
        self.deleteLinkVisible = false;
    },

    /**
     * Set L{editLinkVisible} to C{true}.
     */
    function showEditLink(self) {
        self.editLinkVisible = true;
    },

    /**
     * Set L{editLinkVisible} to C{false}.
     */
    function hideEditLink(self) {
        self.editLinkVisible = false;
    },

    /**
     * Set L{cancelFormLinkVisible} to C{true}.
     */
    function showCancelFormLink(self) {
        self.cancelFormLinkVisible = true;
    },

    /**
     * Set L{cancelFormLinkVisible} to C{false}.
     */
    function hideCancelFormLink(self) {
        self.cancelFormLinkVisible = false;
    });


Mantissa.Test.TestPeople.OrganizerViewTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.OrganizerViewTests');
/**
 * Tests for L{Mantissa.People.OrganizerView}.
 */
Mantissa.Test.TestPeople.OrganizerViewTests.methods(
    /**
     * Construct a L{Mantissa.People.OrganizerView}.
     */
    function setUp(self) {
        self.nodes = {
            'detail': document.createElement('span'),
            'edit-link': document.createElement('a'),
            'delete-link': document.createElement('a'),
            'cancel-form-link': document.createElement('a')}
        self.view = Mantissa.People.OrganizerView(
            function nodeById(id) {
                return self.nodes[id];
            });
    },

    /**
     * L{Mantissa.People.OrganizerView.setOrganizerPosition} should set the
     * I{top} style property of the I{organizer} node to the Y-position of its
     * parent node.
     */
    function test_setOrganizerPosition(self) {
        var containerNode = document.createElement('div');
        var organizerNode = document.createElement('div');
        containerNode.appendChild(organizerNode);
        self.nodes['organizer'] = organizerNode;
        var yPosition = 203;
        var queriedNodes = [];
        var originalFindPosY = Divmod.Runtime.theRuntime.findPosY;
        try {
            Divmod.Runtime.theRuntime.findPosY = function findPosY(node) {
                queriedNodes.push(node);
                return yPosition;
            }
            self.view.setOrganizerPosition();
        } finally {
            Divmod.Runtime.theRuntime.findPosY = originalFindPosY;
        }
        self.assertIdentical(queriedNodes.length, 1);
        self.assertIdentical(queriedNodes[0], containerNode);
        self.assertIdentical(organizerNode.style.top, yPosition + 'px');
    },

    /**
     * L{Mantissa.People.OrganizerView.setDetailNode} should clear any current
     * detail nodes and append the given node.
     */
    function test_setDetailNode(self) {
        self.nodes['detail'].appendChild(
            document.createElement('span'));
        var detailNode = document.createElement('img');
        self.view.setDetailNode(detailNode);
        self.assertIdentical(
            self.nodes['detail'].childNodes.length, 1);
        self.assertIdentical(
            self.nodes['detail'].childNodes[0], detailNode);
    },

    /**
     * L{Mantissa.People.OrganizerView.clearDetailNodes} should clear any
     * current detail nodes.
     */
    function test_clearDetailNodes(self) {
        self.nodes['detail'].appendChild(
            document.createElement('img'));
        self.nodes['detail'].appendChild(
            document.createElement('span'));
        self.view.clearDetailNodes();
        self.assertIdentical(self.nodes['detail'].childNodes.length, 0);
    },

    /**
     * L{Mantissa.People.OrganizerView.hideEditLink} should hide the edit
     * link.
     */
    function test_hideEditLink(self) {
        self.view.hideEditLink();
        self.assertIdentical(
            self.nodes['edit-link'].style.display, 'none');
    },

    /**
     * L{Mantissa.People.OrganizerView.hideDeleteLink} should hide the delete
     * link.
     */
    function test_hideDeleteLink(self) {
        self.view.hideDeleteLink();
        self.assertIdentical(
            self.nodes['delete-link'].style.display, 'none');
    },

    /**
     * L{Mantissa.People.OrganizerView.showEditLink} should show the edit
     * link.
     */
    function test_showEditLink(self) {
        self.view.hideEditLink();
        self.view.showEditLink();
        self.assertIdentical(
            self.nodes['edit-link'].style.display, '');
    },

    /**
     * L{Mantissa.People.OrganizerView.showDeleteLink} should show the delete
     * link.
     */
    function test_showDeleteLink(self) {
        self.view.hideDeleteLink();
        self.view.showDeleteLink();
        self.assertIdentical(
            self.nodes['delete-link'].style.display, '');
    },

    /**
     * L{Mantissa.People.OrganizerView.hideCancelFormLink} should hide the
     * cancel form link.
     */
    function test_hideCancelFormLink(self) {
        self.view.hideCancelFormLink();
        self.assertIdentical(
            self.nodes['cancel-form-link'].style.display, 'none');
    },

    /**
     * L{Mantissa.People.OrganizerView.showCancelFormLink} should show the
     * cancel form link.
     */
    function test_showCancelFormLink(self) {
        self.view.hideCancelFormLink();
        self.view.showCancelFormLink();
        self.assertIdentical(
            self.nodes['cancel-form-link'].style.display, '');
    });


Mantissa.Test.TestPeople.TestableOrganizer = Mantissa.People.Organizer.subclass(
    'Mantissa.Test.TestPeople.TestableOrganizer');
/**
 * Trivial L{Mantissa.People.Organizer} subclass which uses
 * L{Mantissa.Test.TestPeople.StubOrganizerView}.
 */
Mantissa.Test.TestPeople.TestableOrganizer.methods(
    /**
     * Override the base implementation to return a
     * L{Mantissa.Test.TestPeople.StubOrganizerView}.
     */
    function _makeView(self) {
        return Mantissa.Test.TestPeople.StubOrganizerView();
    });


Mantissa.Test.TestPeople.OrganizerTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.OrganizerTests');
/**
 * Tests for L{Mantissa.People.Organizer}.
 */
Mantissa.Test.TestPeople.OrganizerTests.methods(
    /**
     * Create an Organizer for use by test methods.
     */
    function setUp(self) {
        self.node = Nevow.Test.WidgetUtil.makeWidgetNode();
        self.organizer = Mantissa.Test.TestPeople.TestableOrganizer(self.node);
        self.view = self.organizer.view;

        self.calls = [];
        self.organizer.callRemote = function(name) {
            var args = [];
            for (var i = 1; i < arguments.length; ++i) {
                args.push(arguments[i]);
            }
            var result = Divmod.Defer.Deferred();
            self.calls.push({name: name, args: args, result: result});
            return result;
        };
    },

    /**
     * L{Mantissa.People.Organizer.personScrollerInitialized} should call
     * L{Mantissa.People.Organizer.selectInPersonList} with the name of the
     * initial person, if one is set.
     */
    function test_personScrollerInitialized(self) {
        var initialPersonName = 'Alice';
        self.organizer.initialPersonName = initialPersonName;
        var selectedInPersonList = [];
        self.organizer.selectInPersonList = function(personName) {
            selectedInPersonList.push(personName);
        }
        self.organizer.personScrollerInitialized();
        self.assertIdentical(selectedInPersonList.length, 1);
        self.assertIdentical(
            selectedInPersonList[0], initialPersonName);
    },

    /**
     * L{Mantissa.People.Organizer}'s constructor should call
     * C{setOrganizerPosition} on its view.
     */
    function test_constructorSetsPosition(self) {
        self.assertIdentical(self.view.organizerPositionSet, true);
    },

    /**
     * L{Mantissa.People.Organizer}'s constructor should call
     * L{Mantissa.People.Organizer.displayEditPerson} if the C{initialState}
     * is I{edit}.
     */
    function test_initialStateObserved(self) {
        var displayEditPersonCalls = 0;
        /* subclass because the method we want to mock is called by the
         * constructor */
        var MockEditPersonOrganizer = Mantissa.Test.TestPeople.TestableOrganizer.subclass(
            'MockEditPersonOrganizer');
        MockEditPersonOrganizer.methods(
            function displayEditPerson(self) {
                displayEditPersonCalls++;
            });
        var initialPersonName = 'Initial Person';
        organizer = MockEditPersonOrganizer(
            Nevow.Test.WidgetUtil.makeWidgetNode(),
            '', initialPersonName, 'edit');
        self.assertIdentical(displayEditPersonCalls, 1);
        self.assertIdentical(
            organizer.initialPersonName, initialPersonName);
        self.assertIdentical(
            organizer.currentlyViewingName, initialPersonName);
    },

    /**
     * L{Mantissa.People.Organizer.setDetailWidget} should remove the children
     * of the detail node and add the node for the L{Nevow.Athena.Widget} it is
     * passed as a child of it.
     */
    function test_setDetailWidget(self) {
        var widget = {};
        widget.node = document.createElement('table');
        self.organizer.setDetailWidget(widget);
        self.assertIdentical(self.view.detailNode, widget.node);
    },

    /**
     * L{Mantissa.People.Organizer.setDetailWidget} should destroy the previous
     * detail widget.
     */
    function test_oldDetailWidgetDiscarded(self) {
        var firstWidget = Mantissa.Test.TestPeople.StubWidget();
        var secondWidget = Mantissa.Test.TestPeople.StubWidget();
        self.organizer.setDetailWidget(firstWidget);
        self.organizer.setDetailWidget(secondWidget);
        self.assertIdentical(firstWidget.wasDetached, true);
        self.assertIdentical(secondWidget.wasDetached, false);
    },

    /**
     * L{Mantissa.People.Organizer.deletePerson} should call the remote
     * I{deletePerson} method.
     */
    function test_deletePerson(self) {
        var personName = 'A Person Name';
        self.organizer.currentlyViewingName = personName;
        self.organizer.deletePerson().callback(null);
        self.assertIdentical(self.calls.length, 1);
        self.assertIdentical(self.calls[0].name, 'deletePerson');
        self.assertIdentical(self.calls[0].args.length, 1);
        self.assertIdentical(self.calls[0].args[0], personName);

        self.assertIdentical(self.view.detailNode, null);
        self.assertIdentical(self.view.editLinkVisible, false);
        self.assertIdentical(self.view.deleteLinkVisible, false);
    },

    /**
     * L{Mantissa.People.Organizer.dom_deletePerson} should call
     * L{Mantissa.People.Organizer.deletePerson}.
     */
    function test_domDeletePerson(self) {
        var calls = 0;
        self.organizer.deletePerson = function() {
            calls++;
        }
        self.assertIdentical(self.organizer.dom_deletePerson(), false);
        self.assertIdentical(calls, 1);
    },

    /**
     * L{Mantissa.People.Organizer.cancelForm} should load the last-viewed
     * person and hide the form.
     */
    function test_cancelForm(self) {
        var formNode = document.createElement('form');
        self.view.detailNode = formNode;
        var personName = 'Person Name';
        self.organizer.currentlyViewingName = personName;
        var displayedPerson;
        self.organizer.displayPersonInfo = function(name) {
            displayedPerson = name;
        }
        self.organizer.cancelForm();
        self.assertIdentical(self.view.detailNode, null);
        self.assertIdentical(displayedPerson, personName);
        self.assertIdentical(self.view.cancelFormLinkVisible, false);
    },

    /**
     * L{Mantissa.People.Organizer.dom_cancelForm} should call
     * L{Mantissa.People.Organizer.cancelForm}.
     */
    function test_domCancelForm(self) {
        var calls = 0;
        self.organizer.cancelForm = function() {
            calls++;
        }
        self.assertIdentical(self.organizer.dom_cancelForm(), false);
        self.assertIdentical(calls, 1);
    },

    /**
     * L{Mantissa.People.Organizer.displayAddPerson} should call
     * I{getAddPerson} on the server and set the resulting widget as the detail
     * widget.
     */
    function test_getAddPerson(self) {
        var result = self.organizer.displayAddPerson();
        self.assertIdentical(self.calls.length, 1);
        self.assertIdentical(self.calls[0].name, 'getAddPerson');
        self.assertIdentical(self.calls[0].args.length, 0);
        self.assertIdentical(self.view.editLinkVisible, false);
        self.assertIdentical(self.view.deleteLinkVisible, false);
        self.assertIdentical(self.view.cancelFormLinkVisible, false);

        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            return widgetInfo;
        };
        var detailWidget = null;
        self.organizer.setDetailWidget = function(widget) {
            detailWidget = widget;
        };
        var resultingWidget = Mantissa.Test.TestPeople.StubPersonForm();
        self.calls[0].result.callback(resultingWidget);
        self.assertIdentical(resultingWidget, detailWidget);
        self.assertIdentical(self.view.editLinkVisible, false);
        self.assertIdentical(self.view.deleteLinkVisible, false);
        self.assertIdentical(self.view.cancelFormLinkVisible, true);
    },

    /**
     * Similar to L{test_getAddPerson}, but for
     * L{Mantissa.People.Organizer.displayEditPerson}.
     */
    function test_getEditPerson(self) {
        var name = "A Person's name";
        self.organizer.currentlyViewingName = name;
        var result = self.organizer.displayEditPerson();
        self.assertIdentical(self.calls.length, 1);
        self.assertIdentical(self.calls[0].name, 'getEditPerson');
        self.assertIdentical(self.calls[0].args.length, 1);
        self.assertIdentical(self.calls[0].args[0], name);

        var detailWidget = null;
        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            return widgetInfo;
        };
        self.organizer.setDetailWidget = function(widget) {
            detailWidget = widget;
        };
        var resultingWidget = Mantissa.Test.TestPeople.StubPersonForm();
        self.calls[0].result.callback(resultingWidget);
        self.assertIdentical(resultingWidget, detailWidget);
        self.assertIdentical(self.view.editLinkVisible, false);
        self.assertIdentical(self.view.deleteLinkVisible, false);
        self.assertIdentical(self.view.cancelFormLinkVisible, true);
    },

    /**
     * L{Mantissa.People.Organizer.dom_displayEditPerson} should call
     * L{Mantissa.People.Organizer.displayEditPerson}.
     */
    function test_domDisplayEditPerson(self) {
        var calls = 0;
        self.organizer.displayEditPerson = function() {
            calls++;
        }
        self.assertIdentical(self.organizer.dom_displayEditPerson(), false);
        self.assertIdentical(calls, 1);
    },

    /**
     * L{Mantissa.People.Organizer.getPersonScroller} should return the first
     * child widget.
     */
    function test_getPersonScroller(self) {
        var personScroller = {};
        self.organizer.childWidgets = [personScroller];
        self.assertIdentical(
            self.organizer.getPersonScroller(), personScroller);
    },

    /**
     * L{Mantissa.People.Organizer.refreshPersonList} should call
     * C{emptyAndRefill} on the child scrolltable.
     */
    function test_refreshPersonList(self) {
        var calls = 0;
        self.organizer.childWidgets = [
            {emptyAndRefill: function() {
                calls++;
            }}];
        self.organizer.refreshPersonList();
        self.assertIdentical(calls, 1);
    },

    /**
     * L{Mantissa.People.Organizer.selectInPersonList} should call
     * C{selectNamedPerson} on the child scrolltable.
     */
    function test_selectInPersonList(self) {
        var names = [];
        self.organizer.childWidgets = [
            {selectNamedPerson: function(name) {
                names.push(name);
            }}];
        var personName = 'A person name';
        self.organizer.selectInPersonList(personName);
        self.assertIdentical(names.length, 1);
        self.assertIdentical(names[0], personName);
    },

    /**
     * Test that calling back C{displayDeferred} with a
     * L{Mantissa.Test.TestPeople.StubPersonForm} results in a submission
     * observer being added to the form, and that invoking the observer pokes
     * the appropriate state.
     *
     * @param displayDeferred: Deferred from display{Edit,Add}Person.
     * @type displayDeferred: L{Divmod.Defer.Deferred}
     */
    function _doObservationTest(self, displayDeferred) {
        var nickname = 'test nick';
        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            return widgetInfo;
        };
        self.organizer.displayPersonInfo = function(nickname) {
            displaying = nickname;
        };
        var refreshed = false;
        self.organizer.refreshPersonList = function() {
            refreshed = true;
            return Divmod.Defer.succeed(undefined);
        }
        var form = Mantissa.Test.TestPeople.StubPersonForm();
        self.calls[0].result.callback(form);
        form.submissionObservers[0](nickname);
        self.assertIdentical(displaying, nickname);
        self.assertIdentical(refreshed, true);
    },

    /**
     * L{Organizer} should add an observer to L{AddPersonForm} which calls
     * L{Organizer.displayPersonInfo} with the nickname it is passed.
     */
    function test_personCreationObservation(self) {
        self._doObservationTest(self.organizer.displayAddPerson());
    },

    /**
     * Similar to L{test_personCreationObservation}, but for
     * L{Mantissa.People.Organizer.displayEditPerson} and person edit
     * notification.
     */
    function test_personEditObservation(self) {
        self._doObservationTest(self.organizer.displayEditPerson());
    },

    /**
     * The person-edit observer set by
     * L{Mantissa.People.Organizer.displayEditPerson} should call
     * L{Mantissa.People.Organizer.storeOwnerPersonNameChanged} if the store
     * owner person was edited.
     */
    function test_personEditObservationStoreOwner(self) {
        var name = 'Store Owner!';
        self.organizer.currentlyViewingName = name;
        self.organizer.storeOwnerPersonName = name;
        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            return widgetInfo;
        }
        self.organizer.displayEditPerson();
        var stubPerformForm = Mantissa.Test.TestPeople.StubPersonForm();
        self.calls[0].result.callback(stubPerformForm);
        var nameChanges = [];
        self.organizer.storeOwnerPersonNameChanged = function(name) {
            nameChanges.push(name);
        }
        self.organizer._cbPersonModified = function() {
        }
        var newName = 'Store Owner 2!';
        stubPerformForm.submissionObservers[0](newName);
        self.assertIdentical(nameChanges.length, 1);
        self.assertIdentical(nameChanges[0], newName);
    },

    /**
     * L{Mantissa.People.Organizer.storeOwnerPersonNameChanged} should call
     * the method with the same name on the child person scroller.
     */
    function test_storeOwnerPersonNameChanged(self) {
        var nameChanges = [];
        self.organizer.childWidgets = [
            {storeOwnerPersonNameChanged: function(newName) {
                nameChanges.push(newName);
            }}];
        var newName = 'Store Owner!';
        self.organizer.storeOwnerPersonNameChanged(newName);
        self.assertIdentical(nameChanges.length, 1);
        self.assertIdentical(nameChanges[0], newName);
    },

    /**
     * L{Mantissa.People.Organizer.displayPersonInfo} should call
     * I{getContactInfoWidget} with the nickname it is passed put the
     * resulting markup in the detail area.
     */
    function test_displayPersonInfo(self) {
        var nickname = 'testuser';
        var result = self.organizer.displayPersonInfo(nickname);

        self.assertIdentical(self.calls.length, 1);
        self.assertIdentical(self.calls[0].name, 'getContactInfoWidget');
        self.assertIdentical(self.calls[0].args.length, 1);
        self.assertIdentical(self.calls[0].args[0], nickname);

        var resultingFragment = {};

        var parsedStrings = [];
        var returnedNode = document.createElement('span');
        var parseXHTMLString = Divmod.Runtime.theRuntime.parseXHTMLString;
        Divmod.Runtime.theRuntime.parseXHTMLString = function(xhtml) {
            parsedStrings.push(xhtml);
            return {documentElement: returnedNode};
        };
        try {
            self.calls[0].result.callback(resultingFragment);
        } finally {
            Divmod.Runtime.theRuntime.parseXHTMLString = parseXHTMLString;
        }
        self.assertIdentical(self.view.detailNode, returnedNode);
        self.assertIdentical(parsedStrings.length, 1);
        self.assertIdentical(parsedStrings[0], resultingFragment);
    });


Mantissa.Test.TestPeople.EditPersonFormTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.EditPersonFormTests');
/**
 * Tests for L{Mantissa.People.EditPersonForm}.
 */
Mantissa.Test.TestPeople.EditPersonFormTests.methods(
    /**
     * L{Mantissa.People.EditPersonForm.reset} shouldn't reset the values of
     * the form.
     */
    function test_reset(self) {
        var identifier = 'athena:123';
        var node = document.createElement('form');
        var wasReset = false;
        node.reset = function reset() {
            wasReset = true;
        };
        node.id = identifier;
        var form = Mantissa.People.EditPersonForm(node, 'name');
        form.reset();
        self.assertIdentical(wasReset, false);
    });


Mantissa.Test.TestPeople.SubmitNotificationFormTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.SubmitNotificationFormTests');
/**
 * Tests for L{Mantissa.Peoople._SubmitNotificationForm}.
 */
Mantissa.Test.TestPeople.SubmitNotificationFormTests.methods(
    /**
     * After successful submission, the form widget should notify all
     * registered observers of the nickname of the person which was just
     * modified.
     */
    function test_observeSubmission(self) {
        var createdPeople = [];
        function personCreationObserver(nickname) {
            createdPeople.push(nickname);
        };
        var nickname = 'test nick';
        var node = document.createElement('form');
        node.id = 'athena:123';
        var input = document.createElement('input');
        input.name = 'nickname';
        input.value = nickname;
        input.type = 'text';
        node.appendChild(input);
        var form = Mantissa.People._SubmitNotificationForm(node, 'name');
        form.observeSubmission(personCreationObserver);
        form.submitSuccess(null);
        self.assertIdentical(createdPeople.length, 1);
        self.assertIdentical(createdPeople[0], nickname);
    });


Mantissa.Test.TestPeople.AddPersonTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.AddPersonTests');
/**
 * Tests for L{Mantissa.People.AddPerson}.
 */
Mantissa.Test.TestPeople.AddPersonTests.methods(
    /**
     * L{Mantissa.People.AddPerson.observeSubmission} should pass the observer
     * it is called with to the C{observeSubmission} method of the
     * L{AddPersonForm} instance it contains.
     */
    function test_observePersonCreation(self) {
        var node = document.createElement('span');
        node.id = 'athena:123';
        var addPerson = Mantissa.People.AddPerson(node);
        var addPersonForm = Mantissa.Test.TestPeople.StubPersonForm();
        addPerson.addChildWidget(addPersonForm);
        var observer = {};
        addPerson.observeSubmission(observer);
        self.assertIdentical(addPersonForm.submissionObservers.length, 1);
        self.assertIdentical(addPersonForm.submissionObservers[0], observer);
    });


Mantissa.Test.TestPeople.EditPersonTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.EditPersonTests');
/**
 * Tests for L{Mantissa.People.EditPerson}.
 */
Mantissa.Test.TestPeople.EditPersonTests.methods(
    /**
     * L{Mantissa.People.EditPerson.observeSubmission} should pass the
     * observer it is called with to the C{observeSubmission} method of the
     * L{Mantissa.People.EditPersonForm} instance it contains.
     */
    function test_observePersonEdits(self) {
        var editPerson = Mantissa.People.EditPerson(
            Nevow.Test.WidgetUtil.makeWidgetNode());
        var editPersonForm = Mantissa.Test.TestPeople.StubPersonForm();
        editPerson.addChildWidget(editPersonForm);
        var observer = {};
        editPerson.observeSubmission(observer);
        self.assertIdentical(editPersonForm.submissionObservers.length, 1);
        self.assertIdentical(editPersonForm.submissionObservers[0], observer);
    });


Mantissa.Test.TestPeople.PersonScrollerTestCase = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.PersonScrollerTestCase');
/**
 * Tests for L{Mantissa.People.PersonScroller}.
 */
Mantissa.Test.TestPeople.PersonScrollerTestCase.methods(
    /**
     * Construct a L{Mantissa.People.PersonScroller}.
     */
    function setUp(self) {
        self.scroller = Mantissa.People.PersonScroller(
            Nevow.Test.WidgetUtil.makeWidgetNode(), null, []);
    },

    /**
     * L{Mantissa.People.PersonScroller.loaded} should call
     * C{personScrollerInitialized} on the widget parent after the deferred
     * returned from the base implementation fires.
     */
    function test_loaded(self) {
        var initialized = false;
        self.scroller.widgetParent = {
            personScrollerInitialized: function() {
                initialized = true;
            }
        };
        var deferred = Divmod.Defer.Deferred();
        self.scroller.callRemote = function() {
            return deferred;
        }
        self.scroller.loaded();
        self.assertIdentical(initialized, false);
        deferred.callback([]);
        self.assertIdentical(initialized, true);
    },

    /**
     * L{Mantissa.People.PersonScroller.dom_cellClicked} should call the
     * C{displayPersonInfo} method on the parent widget.
     */
    function test_domCellClicked(self) {
        var displayingPerson;
        self.scroller.widgetParent = {
            displayPersonInfo: function(name) {
                displayingPerson = name;
            }}
        var personName = 'A person name';
        var rowNode = document.createElement('div');
        rowNode.appendChild(document.createTextNode(personName));
        self.assertIdentical(self.scroller.dom_cellClicked(rowNode), false);
        self.assertIdentical(displayingPerson, personName);
    },

    /**
     * L{Mantissa.People.PersonScroller.dom_cellClicked} should make the row
     * appear selected.
     */
    function test_domCellClickedSelection(self) {
        self.scroller.widgetParent = {
            displayPersonInfo: function(name) {
        }};
        var rowNode = document.createElement('div');
        self.scroller.dom_cellClicked(rowNode);
        self.assertIdentical(
            rowNode.getAttribute('class'),
            'person-list-selected-person-row');
    },

    /**
     * L{Mantissa.People.PersonScroller.dom_cellClicked} should unselect the
     * previously-selected row.
     */
    function test_domCellClickedDeselection(self) {
        self.scroller.widgetParent = {
            displayPersonInfo: function(name) {
        }};
        var rowNode = document.createElement('div');
        self.scroller.dom_cellClicked(rowNode);
        var secondRowNode = document.createElement('div');
        self.scroller.dom_cellClicked(secondRowNode);
        self.assertIdentical(
            rowNode.getAttribute('class'),
            'person-list-person-row');
        self.assertIdentical(
            secondRowNode.getAttribute('class'),
            'person-list-selected-person-row');
    },

    /**
     * L{Mantissa.People.PersonScroller.selectNamedPerson} should make the
     * given person's row appear selected.
     */
    function test_selectNamedPerson(self) {
        var personName = 'A person name';
        var firstJunkRowNode = self.scroller.makeRowElement(
            0, {name: 'Some other person name'}, []);
        var rowNode = self.scroller.makeRowElement(
            1, {name: personName}, []);
        var secondJunkRowNode = self.scroller.makeRowElement(
            2, {name: 'A third person name'}, []);
        self.scroller.selectNamedPerson(personName);
        self.assertIdentical(
            rowNode.getAttribute('class'),
            'person-list-selected-person-row');
        self.assertIdentical(
            firstJunkRowNode.getAttribute('class'),
            'person-list-person-row');
        self.assertIdentical(
            secondJunkRowNode.getAttribute('class'),
            'person-list-person-row');
    },

    /**
     * L{Mantissa.People.PersonScroller.makeRowElement} should make a
     * link-like node.
     */
    function test_makeRowElement(self) {
        var cellElement = document.createElement('span');
        var rowData = {name: 'A person name'};
        var rowElement = self.scroller.makeRowElement(
            0, rowData, [cellElement]);
        self.assertIdentical(rowElement.tagName, 'DIV');
        self.assertIdentical(rowElement.childNodes.length, 1);
        self.assertIdentical(rowElement.childNodes[0], cellElement);
        if(rowElement.onclick === undefined) {
            self.fail('row element has no onclick handler');
        }
    },

    /**
     * L{Mantissa.People.PersonScroller.makeCellElement} should return an
     * image tag for the C{vip} column.
     */
    function test_makeCellElementVIP(self) {
        var cellElement = self.scroller.makeCellElement(
            'vip', {vip: true});
        self.assertIdentical(cellElement.tagName, 'IMG');
        cellElement = self.scroller.makeCellElement(
            'vip', {vip: false});
        self.assertIdentical(cellElement, undefined);
    },

    /**
     * L{Mantissa.People.PersonScroller.makeCellElement} should include an
     * image in the store owner person's name cell.
     */
    function test_makeCellElementStoreOwner(self) {
        var storeOwnerPersonName = 'Store Owner!';
        self.scroller.storeOwnerPersonName = storeOwnerPersonName;
        self.scroller.columns = {name: {
            extractValue: function(rowData) {
                return rowData.name;
            },
            valueToDOM: function(value) {
                return value;
            }}};
        var cellElement = self.scroller.makeCellElement(
            'name', {name: storeOwnerPersonName, vip: false});
        self.assertIdentical(cellElement.childNodes.length, 2);
        self.assertIdentical(
            cellElement.childNodes[0].nodeValue, storeOwnerPersonName);
        self.assertIdentical(
            cellElement.childNodes[1].tagName, 'IMG');
        self.assertIdentical(
            cellElement.childNodes[1].getAttribute('src'),
            '/Mantissa/images/star-icon.png');
    },

    /**
     * L{Mantissa.People.PersonScroller.makeCellElement} should return a span
     * tag for the C{name} column.
     */
    function test_makeCellElementName(self) {
        self.scroller.columns = {name: {
            extractValue: function(rowData) {
                return rowData.name;
            },
            valueToDOM: function(value) {
                return value;
            }}};
        var cellElement = self.scroller.makeCellElement(
            'name', {name: 'A person name', vip: false});
        self.assertIdentical(cellElement.tagName, 'SPAN');
        self.assertIdentical(
            cellElement.className, 'people-table-person-name');
        cellElement = self.scroller.makeCellElement(
            'name', {name: 'A VIP person name', vip: true});
        self.assertIdentical(cellElement.tagName, 'SPAN');
        self.assertIdentical(
            cellElement.className, 'people-table-vip-person-name');
    });
