// Copyright (c) 2007 Divmod.
// See LICENSE for details.

/**
 * Tests for L{Mantissa.ScrollTable.ScrollModel}
 */

// import Divmod.Defer
// import Divmod.UnitTest
// import Mantissa.People

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
        var Widget = Divmod.Class.subclass();
        Widget.methods(
            function callRemote(self, method, name, id) {
                results.method = method;
                results.name = name;
                results.id = id;
                return results.deferred;
            });

        var results = {};
        results.deferred = Divmod.Defer.Deferred();
        var scroller = Widget();
        var action = Mantissa.People.EditAction();
        var row = {};
        row.__id__ = '123';
        var d = action.enact(scroller, row);
        self.assertIdentical(results.method, 'performAction');
        self.assertIdentical(results.name, 'edit');
        self.assertIdentical(results.id, row.__id__);
    },

    /**
     * L{Mantissa.People.EditAction.handleSuccess} should hand the widget it is
     * given to the widget parent of the scrolling widget it is passed.
     */
    function test_handleSuccess(self) {
        var Widget = Divmod.Class.subclass();

        var action = Mantissa.People.EditAction();
        var info = Widget();
        var widget = Widget();
        var scroller = Widget();
        var parent = Widget();
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
