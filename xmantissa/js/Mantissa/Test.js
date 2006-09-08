
// import Mantissa
// import Nevow.Athena.Test
// import Mantissa.ScrollTable

Mantissa.Test.Forms = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.Forms');
Mantissa.Test.Forms.methods(
    function test_formSubmission(self) {
        return self.childWidgets[0].submit();
    });

Mantissa.Test.StatsTest = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.StatsTest');
Mantissa.Test.StatsTest.methods(
    function test_statsGraph(self) {
        return self.callRemote('run');
    });

Mantissa.Test.UserInfoSignup = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.UserInfoSignup');
Mantissa.Test.UserInfoSignup.methods(
    function test_signup(self) {
        // Ensure that filling out the signup form in a strange order
        // doesn't prevent it from being submittable.
        var f = self.childWidgets[0];
        var button = f.nodeByAttribute("name", "__submit__");
        f.node.firstName.focus();
        f.node.firstName.value = "Fred";
        f.node.firstName.onkeyup();
        f.node.lastName.focus();
        f.node.lastName.value = "Foobar";
        f.node.lastName.onkeyup();
        f.node.username.focus();
        // this is the onkeyup for the username field --
        // doing this by hand to get at the deferred
        Nevow.Athena.Widget.get(f.node.username).verifyUsernameAvailable(
            f.node.username).addCallback(function(x) {
                    f.node.password.focus();
                    f.node.password.value = "x";
                    f.node.password.onkeyup();
                    f.node.confirmPassword.focus();
                    f.node.confirmPassword.value = "foobaz";
                    f.node.confirmPassword.onkeyup();
                    // The password is invalid and there's no email address.
                    // The form shouldn't be submittable.
                    self.assertEquals(f.submitButton.disabled, true);
                    f.node.emailAddress.focus();
                    f.node.emailAddress.value = "fred@example.com";
                    f.node.emailAddress.onkeyup();
                    // The password is still invalid, so still not ready
                    self.assertEquals(f.submitButton.disabled, true);
                    f.node.password.value = "foobaz";
                    f.node.password.onkeyup();
                    // Gotta visit the confirm-password field again to
                    // get it to realize everything is OK now
                    f.node.confirmPassword.onkeyup();
                    // The password is now valid and all the fields are filled.
                    // It should be ready to submit.
                    self.assertEquals(f.submitButton.disabled, false);
                });
    });

Mantissa.Test.Text = Mantissa.Test.Forms.subclass('Mantissa.Test.Text');

Mantissa.Test.MultiText = Mantissa.Test.Forms.subclass('Mantissa.Test.MultiText');

Mantissa.Test.TextArea = Mantissa.Test.Forms.subclass('Mantissa.Test.TextArea');

Mantissa.Test.Select = Mantissa.Test.Forms.subclass('Mantissa.Test.Select');

Mantissa.Test.ChoiceMultiple = Mantissa.Test.Forms.subclass('Mantissa.Test.ChoiceMultiple');

Mantissa.Test.Choice = Mantissa.Test.Forms.subclass('Mantissa.Test.Choice');

Mantissa.Test.Traverse = Mantissa.Test.Forms.subclass('Mantissa.Test.Traverse');

Mantissa.Test.NoNickOrFirstLastNames = Mantissa.Test.Forms.subclass('Mantissa.Test.NoNickOrFirstLastNames');
Mantissa.Test.NoNickButFirstLastNames = Mantissa.Test.Forms.subclass('Mantissa.Test.NoNickButFirstLastNames');
Mantissa.Test.OnlyNick = Mantissa.Test.Forms.subclass('Mantissa.Test.OnlyNick');
Mantissa.Test.OnlyEmailAddress = Mantissa.Test.Forms.subclass('Mantissa.Test.OnlyEmailAddress');
Mantissa.Test.NickNameAndEmailAddress = Mantissa.Test.Forms.subclass('Mantissa.Test.NickNameAndEmailAddress');

Mantissa.Test.ScrollTableModelTestCase = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.ScrollTableModelTestCase');
Mantissa.Test.ScrollTableModelTestCase.methods(
    /**
     * Create a ScrollModel to run tests against.
     *
     * For now, setUp is /not/ a fixture provided by the harness. Each test
     * method invokes it explicitly.
     */
    function setUp(self) {
        self.model = Mantissa.ScrollTable.ScrollModel();
    },

    /**
     * Test that new rows can be added to a ScrollModel.
     */
    function test_setRowData(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});

        self.assertEqual(self.model.getRowData(0).__id__, 'a');
        self.assertEqual(self.model.getRowData(1).__id__, 'b');

        /*
         * Negative updates must be rejected.
         */
        var error = self.assertThrows(
            Error,
            function() { self.model.setRowData(-1, {__id__: 'c'}); });
        self.assertEqual(
            error.message,
            "Specified index out of bounds in setRowData.");
    },

    /**
     * Test that the correct number of rows is returned by
     * L{ScrollModel.rowCount}.
     */
    function test_rowCount(self) {
        self.setUp();

        self.assertEqual(self.model.rowCount(), 0);
        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.assertEqual(self.model.rowCount(), 1);
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});
        self.assertEqual(self.model.rowCount(), 2);
    },

    /**
     * Test that the index of a particular row can be found with its webID
     * using L{ScrollModel.findIndex}.
     */
    function test_findIndex(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});

        self.assertEqual(self.model.findIndex('a'), 0);
        self.assertEqual(self.model.findIndex('b'), 1);

        var error = self.assertThrows(
            Error,
            function() { self.model.findIndex('c'); });
        self.assertEqual(
            "Specified webID not found.",
            error.message);
    },

    /**
     * Test that an array of indices which actually have row data can be
     * retrieved from the ScrollModel.
     */
    function test_getRowIndices(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a'});
        self.model.setRowData(3, {__id__: 'b'});
        self.assertArraysEqual(self.model.getRowIndices(), [0, 3]);
    },

    /**
     * Test that the data associated with a particular row can be discovered by
     * that row's index in the model using L{ScrollModel.getRowData}.
     */
    function test_getRowData(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});

        self.assertEqual(self.model.getRowData(0).foo, 'bar');
        self.assertEqual(self.model.getRowData(1).baz, 'quux');

        var error;

        error = self.assertThrows(
            Error,
            function() { self.model.getRowData(-1); });
        self.assertEqual(
            error.message,
            "Specified index out of bounds in getRowData.");

        error = self.assertThrows(
            Error,
            function() { self.model.getRowData(2); });
        self.assertEqual(
            error.message,
            "Specified index out of bounds in getRowData.");

        /*
         * The array is sparse, so valid indexes might not be
         * populated.  Requesting these should return undefined rather
         * than throwing an error.
         */
        self.model.setRowData(3, {__id__: 'd'});

        self.assertEqual(self.model.getRowData(2), undefined);
    },

    /**
     * Test that the data associated with a particular webID can be discovered
     * from that webID using L{ScrollModel.findRowData}.
     */
    function test_findRowData(self) {
        self.setUp();

        /*
         * XXX This should populate the model's rows using a public API
         * of some sort.
         */
        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});

        self.assertEqual(self.model.findRowData('a').foo, 'bar');
        self.assertEqual(self.model.findRowData('b').baz, 'quux');

        var error = self.assertThrows(
            Error,
            function() { self.model.findRowData('c'); });
        self.assertEqual(
            error.message,
            "Specified webID not found.");
    },

    /**
     * Test that we can advance through a model's rows with
     * L{ScrollModel.findNextRow}.
     */
    function test_findNextRow(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});
        self.model.setRowData(2, {__id__: 'c', red: 'green'});
        self.model.setRowData(3, {__id__: 'd', blue: 'yellow'});
        self.model.setRowData(4, {__id__: 'e', white: 'black'});
        self.model.setRowData(5, {__id__: 'f', brown: 'puce'});

        /*
         * We should be able to advance without a predicate
         */
        self.assertEqual(self.model.findNextRow('a'), 'b');
        self.assertEqual(self.model.findNextRow('b'), 'c');

        /*
         * Going off the end should result in a null result.
         */
        self.assertEqual(self.model.findNextRow('f'), null);

        /*
         * A predicate should be able to cause rows to be skipped.
         */
        self.assertEqual(
            self.model.findNextRow(
                'a',
                function(idx, row, node) {
                    if (row.__id__ == 'b') {
                        return false;
                    }
                    return true;
                }),
            'c');
    },

    /**
     * Like L{test_findNextRow}, but for L{ScrollModel.findPrevRow}.
     */
    function test_findPrevRow(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});
        self.model.setRowData(2, {__id__: 'c', red: 'green'});
        self.model.setRowData(3, {__id__: 'd', blue: 'yellow'});
        self.model.setRowData(4, {__id__: 'e', white: 'black'});
        self.model.setRowData(5, {__id__: 'f', brown: 'puce'});

        /*
         * We should be able to regress without a predicate
         */
        self.assertEqual(self.model.findPrevRow('f'), 'e');
        self.assertEqual(self.model.findPrevRow('e'), 'd');

        /*
         * Going off the beginning should result in a null result.
         */
        self.assertEqual(self.model.findPrevRow('a'), null);

        /*
         * A predicate should be able to cause rows to be skipped.
         */
        self.assertEqual(
            self.model.findPrevRow(
                'f',
                function(idx, row, node) {
                    if (row.__id__ == 'e') {
                        return false;
                    }
                    return true;
                }),
            'd');
    },

    /**
     * Test that rows can be removed from the model and that the model remains
     * in a consistent state.
     */
    function test_removeRowFromMiddle(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});
        self.model.setRowData(2, {__id__: 'c', red: 'green'});
        self.model.setRowData(3, {__id__: 'd', blue: 'yellow'});
        self.model.setRowData(4, {__id__: 'e', white: 'black'});
        self.model.setRowData(5, {__id__: 'f', brown: 'puce'});

        /*
         * Remove something from the middle and make sure only
         * everything after it gets shuffled.
         */
        self.model.removeRow(2);

        /*
         * Things before it should have been left alone.
         */
        self.assertEqual(self.model.getRowData(0).__id__, 'a');
        self.assertEqual(self.model.getRowData(1).__id__, 'b');

        /*
         * It should be missing and things after it should have been
         * moved down one index.
         */
        self.assertEqual(self.model.getRowData(2).__id__, 'd');
        self.assertEqual(self.model.getRowData(3).__id__, 'e');
        self.assertEqual(self.model.getRowData(4).__id__, 'f');

        /*
         * There should be nothing at the previous last index, either.
         */
        var error;

        error = self.assertThrows(
            Error,
            function() { self.model.getRowData(5); });
        self.assertEqual(
            error.message,
            "Specified index out of bounds in getRowData.");

        /*
         * Count should have decreased by one as well.
         */
        self.assertEqual(self.model.rowCount(), 5);

        /*
         * Finding indexes from web IDs should reflect the new state as well.
         */
        self.assertEqual(self.model.findIndex('a'), 0);
        self.assertEqual(self.model.findIndex('b'), 1);
        self.assertEqual(self.model.findIndex('d'), 2);
        self.assertEqual(self.model.findIndex('e'), 3);
        self.assertEqual(self.model.findIndex('f'), 4);

        /*
         * And the removed row should not be discoverable that way.
         */
        error = self.assertThrows(
            Error,
            function() { self.model.findIndex('c'); });
        self.assertEqual(
            error.message,
            "Specified webID not found.");
    },

    /**
     * Test that rows can be removed from the end of the model and that the
     * model remains in a consistent state.
     */
    function test_removeRowFromEnd(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.setRowData(1, {__id__: 'b', baz: 'quux'});
        self.model.setRowData(2, {__id__: 'c', red: 'green'});

        /*
         * Remove something from the middle and make sure only
         * everything after it gets shuffled.
         */
        self.model.removeRow(2);

        /*
         * Things before it should have been left alone.
         */
        self.assertEqual(self.model.getRowData(0).__id__, 'a');
        self.assertEqual(self.model.getRowData(1).__id__, 'b');

        /*
         * There should be nothing at the previous last index, either.
         */
        var error;
        error = self.assertThrows(
            Error,
            function() { self.model.getRowData(2); });
        self.assertEqual(
            error.message,
            "Specified index out of bounds in getRowData.");

        /*
         * Count should have decreased by one as well.
         */
        self.assertEqual(self.model.rowCount(), 2);

        /*
         * Finding indexes from web IDs should reflect the new state as well.
         */
        self.assertEqual(self.model.findIndex('a'), 0);
        self.assertEqual(self.model.findIndex('b'), 1);

        /*
         * And the removed row should not be discoverable that way.
         */
        error = self.assertThrows(
            Error,
            function() { self.model.findIndex('c'); });
        self.assertEqual(
            error.message,
            "Specified webID not found.");
    },

    /**
     * Test that removeRow returns an object with index and row properties
     * which refer to the appropriate objects.
     */
    function test_removeRowReturnValue(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});

        var row = self.model.removeRow(0);
        self.assertEqual(row.__id__, 'a');
        self.assertEqual(row.foo, 'bar');
    },

    /**
     * Test that the empty method gets rid of all the rows.
     */
    function test_empty(self) {
        self.setUp();

        self.model.setRowData(0, {__id__: 'a', foo: 'bar'});
        self.model.empty();
        self.assertEqual(self.model.rowCount(), 0);

        var error;

        error = self.assertThrows(
            Error,
            function() { self.model.getRowData(0); });
        self.assertEqual(
            error.message,
            "Specified index out of bounds in getRowData.");

        error = self.assertThrows(
            Error,
            function() { self.model.findIndex('a'); });
        self.assertEqual(
            error.message,
            "Specified webID not found.");
    }
    );


/**
 * Yeaarg.  Do some buggy crap that happens to accidentally work.  Athena
 * really needs this feature.
 *
 * This probably returns the C{Nevow.Athena.Widget} instance which was buried
 * somewhere inside the XHTML string passed in.
 *
 * @param node: A scratch node which should already be part of the document and
 * should probably be visible.
 *
 * @param widgetMarkup: An XHTML string which is the result of flattening a
 * LiveFragment or LiveElement.
 *
 */
Mantissa.Test.addChildWidgetFromMarkup = function addChildWidgetFromMarkup(node, widgetMarkup, widgetClass) {
    var container = document.createElement('span');
    node.appendChild(container);
    Divmod.Runtime.theRuntime.setNodeContent(container, widgetMarkup);
    var widgetNode = Divmod.Runtime.theRuntime.nodeByAttribute(
        container, 'athena:class', widgetClass);
    var w = Nevow.Athena.Widget.get(widgetNode);
    node.removeChild(container);
    return w;
};


Mantissa.Test.ScrollTableViewTestCase = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.ScrollTableViewTestCase');
Mantissa.Test.ScrollTableViewTestCase.methods(
    /**
     * Retrieve a ScrollingWidget from the server to use for the running test
     * method.
     */
    function setUp(self, testMethodName) {
        var result = self.callRemote('getScrollingWidget', testMethodName);
        result.addCallback(
            function(widgetMarkup) {
                return Mantissa.Test.addChildWidgetFromMarkup(
                    self.node, widgetMarkup,
                    'Mantissa.ScrollTable.ScrollingWidget');
            });
        result.addCallback(
            function(widget) {
                self.scrollingWidget = widget;
                self.node.appendChild(widget.node);
                return widget.initializationDeferred;
            });
        return result;
    },

    /**
     * Test that a ScrollingWidget has a model with some rows after its
     * initialization Deferred fires.
     */
    function test_initialize(self) {
        return self.setUp('initialize').addCallback(function() {
                self.assertEqual(self.scrollingWidget.model.rowCount(), 10);
            });
    },

    /**
     * Test that the scrolled method returns a Deferred which fires when some
     * rows have been requested from the server, perhaps.
     */
    function test_scrolled(self) {
        var result = self.setUp('scrolled');
        result.addCallback(
            function(ignored) {
                var scrolled = self.scrollingWidget.scrolled();
                self.failUnless(scrolled instanceof Divmod.Defer.Deferred);
                return scrolled;
            });
        return result;
    },

    /**
     * Test that the scrolltable can have its elements completely dropped and
     * reloaded from the server with the L{ScrollingWidget.emptyAndRefill}
     * method.
     */
    function test_emptyAndRefill(self) {
        var result = self.setUp('emptyAndRefill');
        result.addCallback(function() {
                /*
                 * Tell the server to lose some rows so that we will be able to
                 * notice emptyAndRefill() actually did something.
                 */
                return self.callRemote('changeRowCount', 'emptyAndRefill', 5);
            });
        result.addCallback(function() {
                return self.scrollingWidget.emptyAndRefill();
            });
        result.addCallback(function() {
                self.assertEqual(self.scrollingWidget.model.rowCount(), 5);
            });
        return result;
    },

    /**
     * Test that removing a row from a ScrollingWidget removes it from the
     * underlying model and removes the display nodes associated with it from
     * the document.  The nodes of rows after the removed row should also have
     * their position adjusted to fill the gap.
     */
    function test_removeRow(self) {
        var result = self.setUp('removeRow');
        result.addCallback(function() {
                var firstRow = self.scrollingWidget.model.getRowData(0);
                var nextRow = self.scrollingWidget.model.getRowData(2);
                var removedRow = self.scrollingWidget.removeRow(1);
                var movedRow = self.scrollingWidget.model.getRowData(1);

                self.assertEqual(nextRow.__id__, movedRow.__id__);
                self.assertEqual(removedRow.__node__.parentNode, null);

                self.assertEqual(
                    parseInt(firstRow.__node__.style.top) + self.scrollingWidget._rowHeight,
                    parseInt(movedRow.__node__.style.top));
            });
        return result;
    }
    );



Mantissa.Test.TestableScrollTable = Mantissa.ScrollTable.ScrollingWidget.subclass(
                                        'Mantissa.Test.TestableScrollTable');
Mantissa.Test.TestableScrollTable.methods(
    function __init__(self, node) {
        Mantissa.Test.TestableScrollTable.upcall(self, "__init__", node);
        self._rowHeight = 20;
        self._scrollViewport.style.height = "200px";
        self._rows = [];
        self._firstRowFetch = true;
    },

    function cbRowsFetched(self, n) {
        if(self._firstRowFetch) {
            self._firstRowFetch = false;
            self.widgetParent.scroller = self;
            self.widgetParent.actuallyRunTests(n);
        /* if n == 0, then nothing was actually requested, so it's fine */
        } else if(0 < n) {
            if(!self._pendingScrollDeferred) {
                self.widgetParent.fail('extraneous row request');
            }
            self._pendingScrollDeferred.callback(n);
            self._pendingScrollDeferred = null;
        }
    },

    function scrollBy(self, rows, deferred) {
        self._pendingScrollDeferred = deferred;
        /* changing scrollTop will call the onscroll handler */
        self._scrollViewport.scrollTop += rows * self._rowHeight;
    });


Mantissa.Test.PersonDetail = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.PersonDetail');
Mantissa.Test.PersonDetail.methods(
    function contactInfoSectionsFromSectionName(self, sectionName) {
        return Nevow.Athena.NodesByAttribute(
            self.personDetail.firstNodeByAttribute("class", sectionName),
            "class",
            "contact-info-item");
    },

    function firstNodeByAttributeAndNodeValue(self, root, attr, value, nodeValue) {
        var nodes = Nevow.Athena.NodesByAttribute(root, attr, value);
        for(var i = 0; i < nodes.length; i++) {
            if(nodes[i].childNodes && nodes[i].firstChild.nodeValue == nodeValue) {
                return nodes[i];
            }
        }
        throw new Error("couldn't find node with " + attr + " value " +
                        value + " and node value " + nodeValue);
    },

    function changeAndSaveItemWithValue(self, sections, value, newValue) {
        var node, valueNode;
        for(var i = 0; i < sections.length; i++) {
            try {
                valueNode = self.firstNodeByAttributeAndNodeValue(
                                sections[i], "class", "value", value);
            } catch(e) {
                continue;
            }
            node = sections[i];
        }
        if(!node) {
            throw new Error("can't find item with value " + value);
        }

        Nevow.Athena.FirstNodeByAttribute(
            node, "class", "contact-info-action-edit").onclick();

        Nevow.Athena.FirstNodeByAttribute(node, "value", value).value = newValue;

        var D = self.personDetail.saveContactInfoItem(
            Nevow.Athena.FirstNodeByAttribute(
                node, "class", "contact-info-action-save"));

        return D.addCallback(
            function() {
                self.assertEquals(valueNode.firstChild.nodeValue, newValue);
            });
    },

    function addItemToSection(self, sectionName, value) {
        var section = self.personDetail.firstNodeByAttribute("class", sectionName);

        Nevow.Athena.FirstNodeByAttribute(
            section, "class", "contact-info-action-add").onclick();

        var addForm = Nevow.Athena.FirstNodeByAttribute(
                        section, "class", "add-contact-info");

        var inputs = addForm.getElementsByTagName("input");
        self.assertEquals(inputs.length, 1);
        inputs[0].value = value;

        var createLink = Nevow.Athena.FirstNodeByAttribute(
                            addForm, "class", "contact-info-action-create");

        var D = self.personDetail.createContactInfoItem(createLink);
        return D.addCallback(
            function(node) {
                node = Nevow.Athena.FirstNodeByAttribute(
                            node, "class", "value");
                self.assertEquals(node.firstChild.nodeValue, value);
            });
    },

    function test_people(self) {
        self.personDetail = Nevow.Athena.Widget.get(
                                Nevow.Athena.FirstNodeByAttribute(
                                    self.node,
                                    "athena:class",
                                    "Mantissa.People.PersonDetail"));

        var phoneSections = self.contactInfoSectionsFromSectionName("PhoneNumber");
        var emailSections = self.contactInfoSectionsFromSectionName("EmailAddress");

        var D = self.changeAndSaveItemWithValue(phoneSections, "434-5030", "555-1212");

        D.addCallback(
            function() {
                return self.changeAndSaveItemWithValue(
                    emailSections, "foo@skynet", "foo@internet");
        }).addCallback(
            function() {
                return self.addItemToSection("PhoneNumber", "123-4567");
        });

        return D;
    });

Mantissa.Test.GeneralPrefs = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.GeneralPrefs');
/**
 * Client-side half of xmantissa.test.livetest_prefs.GeneralPrefs
 */
Mantissa.Test.GeneralPrefs.methods(
    /**
     * Change the values of our preferences, submit the form,
     * and then call the python class with the new values so
     * it can make sure it agrees with us
     */
    function test_persistence(self) {
        /**
         * Change the value of the <select> with name C{inputName}
         * by selecting the first <option> inside it which doesn't
         * represent the current value.
         */
        var changeSelectValue = function(inputName) {
            var input = self.firstNodeByAttribute("name", inputName);
            var options = input.getElementsByTagName("option");
            for(var i = 0; i < options.length; i++) {
                if(options[i].value != input.value) {
                    input.selectedIndex = i;
                    /* ChoiceInput sets the value of the options
                     * to their offset in the choice list, so we
                     * don't want to use that */
                    return options[i].firstChild.nodeValue;
                }
            }
        }

        var itemsPerPageValue = parseInt(changeSelectValue("itemsPerPage"));
        var timezoneValue = changeSelectValue("timezone");
        timezoneValue = timezoneValue.replace(/^\s+/, "").replace(/\s+$/, "");

        var liveform = Nevow.Athena.Widget.get(
                        self.firstNodeByAttribute(
                            "athena:class",
                            "Mantissa.Preferences.PrefCollectionLiveForm"));

        return liveform.submit().addCallback(
            function() {
                return self.callRemote("checkPersisted", itemsPerPageValue, timezoneValue);
            });
    });
