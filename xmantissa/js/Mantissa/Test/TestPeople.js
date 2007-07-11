// Copyright (c) 2007 Divmod.
// See LICENSE for details.

/**
 * Tests for L{Mantissa.ScrollTable.ScrollModel}
 */

// import Divmod.Defer
// import Divmod.UnitTest
// import Mantissa.People

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
Mantissa.Test.TestPeople.StubWidget = Divmod.Class.subclass(
    'Mantissa.Test.TestPeople.StubWidget');
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


/**
 * Stub implementation of L{Mantissa.People.AddPersonForm}.
 *
 * @ivar creationObservers: An array of the objects passed to
 *     L{observePersonCreation}.
 */
Mantissa.Test.TestPeople.StubAddPersonForm = Divmod.Class.subclass(
    'Mantissa.Test.TestPeople.StubAddPersonForm');
Mantissa.Test.TestPeople.StubAddPersonForm.methods(
    function __init__(self) {
        self.creationObservers = [];
    },

    /**
     * Ignore the widget hierarchy.
     */
    function setWidgetParent(self, parent) {
    },

    /**
     * Remember a person creation observer in C{self.observers}.
     */
    function observePersonCreation(self, observer) {
        self.creationObservers.push(observer);
    });


/**
 * Tests for L{Mantissa.People.EditAction}.
 */
Mantissa.Test.TestPeople.EditActionTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.OrganizerActionTests');
Mantissa.Test.TestPeople.EditActionTests.methods(
    /**
     * L{Mantissa.People.EditAction.enact} should invoke the edit action on the
     * server and call L{Mantissa.People.EditAction.handleSuccess} when the
     * server responds successfully.
     */
    function test_enact(self) {
        var scroller = Mantissa.Test.TestPeople.StubWidget();
        var action = Mantissa.People.EditAction();
        var row = {};
        row.__id__ = '123';
        var d = action.enact(scroller, row);
        self.assertIdentical(scroller.results.length, 1);
        self.assertIdentical(scroller.results[0].method, 'performAction');
        self.assertIdentical(scroller.results[0].args.length, 2);
        self.assertIdentical(scroller.results[0].args[0], 'edit');
        self.assertIdentical(scroller.results[0].args[1], row.__id__);
    },

    /**
     * L{Mantissa.People.EditAction.handleSuccess} should hand the widget it is
     * given to the widget parent of the scrolling widget it is passed.
     */
    function test_handleSuccess(self) {
        var action = Mantissa.People.EditAction();
        var info = Mantissa.Test.TestPeople.StubWidget();
        var widget = Mantissa.Test.TestPeople.StubWidget();
        var scroller = Mantissa.Test.TestPeople.StubWidget();
        var parent = Mantissa.Test.TestPeople.StubWidget();
        parent.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            results.widgetInfo = widgetInfo;
            return Divmod.Defer.succeed(widget);
        };
        parent.setDetailWidget = function(detailWidget) {
            results.detailWidget = detailWidget;
        };
        scroller.widgetParent = parent;

        var results = {};
        action.handleSuccess(scroller, null, info);
        self.assertIdentical(results.widgetInfo, info);
        self.assertIdentical(results.detailWidget, widget);
    });


/**
 * Tests for L{Mantissa.People.DeleteAction}.
 */
Mantissa.Test.TestPeople.DeleteActionTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.DeleteActionTests');
Mantissa.Test.TestPeople.DeleteActionTests.methods(
    /**
     * L{Mantissa.People.DeleteAction.enact} should invoke the delete action on
     * the server and call L{Mantissa.People.DeleteAction.handleSuccess} when
     * the server responds successfully.
     */
    function test_enact(self) {
        var scroller = Mantissa.Test.TestPeople.StubWidget();
        var action = Mantissa.People.DeleteAction();
        var row = {};
        row.__id__ = '321';
        var d = action.enact(scroller, row);
        self.assertIdentical(scroller.results.length, 1);
        self.assertIdentical(scroller.results[0].method, 'performAction');
        self.assertIdentical(scroller.results[0].args.length, 2);
        self.assertIdentical(scroller.results[0].args[0], 'delete');
        self.assertIdentical(scroller.results[0].args[1], row.__id__);
    },

    /**
     * L{Mantissa.People.DeleteAction.handleSuccess} should remove the row for
     * the deleted person from the scroll table.
     */
    function test_handleSuccess(self) {
        var scroller = Mantissa.Test.TestPeople.StubWidget();
        var row = {};
        row.__id__ = '321';
        scroller.model = Mantissa.ScrollTable.ScrollModel();
        scroller.model.setRowData(0, row);
        var action = Mantissa.People.DeleteAction();
        action.handleSuccess(scroller, row, null);
        self.assertIdentical(scroller.removedRows.length, 1);
        self.assertIdentical(scroller.removedRows[0], 0);
    });


/**
 * Tests for L{Mantissa.People.Organizer}.
 */
Mantissa.Test.TestPeople.OrganizerTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.OrganizerTests');
Mantissa.Test.TestPeople.OrganizerTests.methods(
    /**
     * Create an Organizer for use by test methods.
     */
    function setUp(self) {
        self.node = document.createElement('span');
        self.detail = document.createElement('span');
        self.existing = document.createElement('img');
        /*
         * XXX - Athena ought to have a public API for constructing these
         * strings, perhaps? -exarkun
         */
        self.node.id = 'athena:123';
        self.detail.id = 'athenaid:123-detail';
        self.detail.appendChild(self.existing);
        self.node.appendChild(self.detail);
        document.body.appendChild(self.node);
        self.organizer = Mantissa.People.Organizer(self.node);

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
     * L{Mantissa.People.Organizer.setDetailWidget} should remove the children
     * of the detail node and add the node for the L{Nevow.Athena.Widget} it is
     * passed as a child of it.
     */
    function test_setDetailWidget(self) {
        var widget = {};
        widget.node = document.createElement('table');
        self.organizer.setDetailWidget(widget);
        self.assertIdentical(self.detail.childNodes.length, 1);
        self.assertIdentical(self.detail.childNodes[0], widget.node);
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
     * L{Mantissa.People.Organizer.displayAddPerson} should call
     * I{getAddPerson} on the server and set the resulting widget as the detail
     * widget.
     */
    function test_getAddPerson(self) {
        var result = self.organizer.displayAddPerson();
        self.assertIdentical(self.calls.length, 1);
        self.assertIdentical(self.calls[0].name, 'getAddPerson');
        self.assertIdentical(self.calls[0].args.length, 0);

        var detailWidget = null;
        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            return widgetInfo;
        };
        self.organizer.setDetailWidget = function(widget) {
            detailWidget = widget;
        };
        var resultingWidget = Mantissa.Test.TestPeople.StubAddPersonForm();
        self.calls[0].result.callback(resultingWidget);
        self.assertIdentical(resultingWidget, detailWidget);
    },

    /**
     * L{Organizer} should add an observer to L{AddPersonForm} which calls
     * L{Organizer.displayPersonInfo} with the nickname it is passed.
     */
    function test_personCreationObservation(self) {
        var result = self.organizer.displayAddPerson();
        var nickname = 'test nick';
        self.organizer.addChildWidgetFromWidgetInfo = function(widgetInfo) {
            return widgetInfo;
        };
        self.organizer.displayPersonInfo = function(nickname) {
            displaying = nickname;
        };
        var addPersonForm = Mantissa.Test.TestPeople.StubAddPersonForm();
        self.calls[0].result.callback(addPersonForm);
        addPersonForm.creationObservers[0](nickname);
        self.assertIdentical(displaying, nickname);
    },

    /**
     * L{Mantissa.People.Organizer.displayPersonInfo} should call
     * I{getContactInformation} with the nickname it is passed put the
     * resulting markup in the detail area.
     */
    function test_displayPersonInfo(self) {
        var nickname = 'testuser';
        var result = self.organizer.displayPersonInfo(nickname);

        self.assertIdentical(self.calls.length, 1);
        self.assertIdentical(self.calls[0].name, 'getContactInformation');
        self.assertIdentical(self.calls[0].args.length, 1);
        self.assertIdentical(self.calls[0].args[0], nickname);

        var detailNodes = null;
        self.organizer.setDetailNodes = function(nodes) {
            detailNodes = nodes;
        };

        var resultingFragments = [{}, {}];

        var parsedStrings = [];
        var returnedNodes = [];
        var parseXHTMLString = Divmod.Runtime.theRuntime.parseXHTMLString;
        Divmod.Runtime.theRuntime.parseXHTMLString = function(xhtml) {
            parsedStrings.push(xhtml);
            returnedNodes.push(document.createElement('span'));
            var doc = {};
            doc.documentElement = returnedNodes[returnedNodes.length - 1];
            return doc;
        };
        try {
            self.calls[0].result.callback(resultingFragments);
        } finally {
            Divmod.Runtime.theRuntime.parseXHTMLString = parseXHTMLString;
        }
        self.assertIdentical(detailNodes.length, 2);
        self.assertIdentical(detailNodes[0], returnedNodes[0]);
        self.assertIdentical(detailNodes[1], returnedNodes[1]);
        self.assertIdentical(parsedStrings.length, 2);
        self.assertIdentical(parsedStrings[0], resultingFragments[0]);
        self.assertIdentical(parsedStrings[1], resultingFragments[1]);
    });


/**
 * Tests for L{Mantissa.People.EditPersonForm}.
 */
Mantissa.Test.TestPeople.EditPersonFormTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.EditPersonFormTests');
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


/**
 * Tests for L{Mantissa.People.AddPersonForm}.
 */
Mantissa.Test.TestPeople.AddPersonFormTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.AddPersonFormTests');
Mantissa.Test.TestPeople.AddPersonFormTests.methods(
    /**
     * After successful submission, the form widget should notify all
     * registered person creation observers of the nickname of the person which
     * was just created.
     */
    function test_personCreationNotification(self) {
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
        var form = Mantissa.People.AddPersonForm(node, 'name');
        form.observePersonCreation(personCreationObserver);
        form.submitSuccess(null);
        self.assertIdentical(createdPeople.length, 1);
        self.assertIdentical(createdPeople[0], nickname);
    });


/**
 * Tests for L{Mantissa.People.AddPerson}.
 */
Mantissa.Test.TestPeople.AddPersonTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.AddPersonTests');
Mantissa.Test.TestPeople.AddPersonTests.methods(
    /**
     * L{AddPerson.observePersonCreation} should pass the observer it is called
     * with to the C{observePersonCreation} method of the L{AddPersonForm}
     * instance it contains.
     */
    function test_observePersonCreation(self) {
        var node = document.createElement('span');
        node.id = 'athena:123';
        var addPerson = Mantissa.People.AddPerson(node);
        var addPersonForm = Mantissa.Test.TestPeople.StubAddPersonForm();
        addPerson.addChildWidget(addPersonForm);
        var observer = {};
        addPerson.observePersonCreation(observer);
        self.assertIdentical(addPersonForm.creationObservers.length, 1);
        self.assertIdentical(addPersonForm.creationObservers[0], observer);
    });
