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
 * @ivar results: An array with one object for each time callRemote has been
 *     invoked.  The objects have the following properties::
 *
 *    deferred: The L{Divmod.Defer.Deferred} which was returned by the
 *              corresponding callRemote call.
 *    method: The name of the remote method which was invoked.
 *    args: An array of the remaining arguments given to the callRemote call.
 */
Mantissa.Test.TestPeople.StubWidget = Divmod.Class.subclass(
    'Mantissa.Test.TestPeople.StubWidget');
Mantissa.Test.TestPeople.StubWidget.methods(
    function __init__(self) {
        self.results = [];
        self.removedRows = [];
    },

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
     * L{Mantissa.People.Organizer.setDetailWidget} should remove the children
     * of the detail node and add the node for the L{Nevow.Athena.Widget} it is
     * passed as a child of it.
     */
    function test_setDetailWidget(self) {
        var identifier = 'athena:123';
        var node = document.createElement('span');
        var detail = document.createElement('span');
        var existing = document.createElement('img');
        node.id = identifier;
        /*
         * XXX - Athena ought to have a public API for constructing this
         * string, perhaps? -exarkun
         */
        detail.id = 'athenaid:123-detail';
        node.appendChild(detail);
        detail.appendChild(existing);

        document.body.appendChild(node);

        var organizer = Mantissa.People.Organizer(node);
        var widget = {};
        widget.node = document.createElement('table');
        organizer.setDetailWidget(widget);
        self.assertIdentical(detail.childNodes.length, 1);
        self.assertIdentical(detail.childNodes[0], widget.node);
    });


/**
 * Tests for L{Mantissa.People.EditPersonForm}.
 */
Mantissa.Test.TestPeople.EditPersonFormTests = Divmod.UnitTest.TestCase.subclass(
    'Mantissa.Test.TestPeople.EDitPersonFormTests');
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
