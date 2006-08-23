
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

Mantissa.Test.TextArea = Mantissa.Test.Forms.subclass('Mantissa.Test.TextArea');

Mantissa.Test.Select = Mantissa.Test.Forms.subclass('Mantissa.Test.Select');

Mantissa.Test.ChoiceMultiple = Mantissa.Test.Forms.subclass('Mantissa.Test.ChoiceMultiple');

Mantissa.Test.Choice = Mantissa.Test.Forms.subclass('Mantissa.Test.Choice');

Mantissa.Test.Traverse = Mantissa.Test.Forms.subclass('Mantissa.Test.Traverse');

Mantissa.Test.People = Mantissa.Test.Forms.subclass('Mantissa.Test.People');

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

Mantissa.Test.ScrollTable = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.Scrolltable');

Mantissa.Test.ScrollTable.methods(
    function __init__(self, node) {
        Mantissa.Test.ScrollTable.upcall(self, "__init__", node);
        self._preTestDeferred = new Divmod.Defer.Deferred();
    },

    function test_scrolling(self) {
        var assertRowCount = function(n) {
            var rows = self.scroller.nodesByAttribute("class", "scroll-row");
            var cell;
            for(var i = 0; i < rows.length; i++) {
                cell = Nevow.Athena.FirstNodeByAttribute(rows[i], "class", "scroll-cell");
                self.assertEquals(cell.firstChild.nodeValue, parseInt(i));
            }
            self.assertEquals(i, n);
        }
        return self._preTestDeferred.addCallback(
            function(requestedRowCount) {
                self.assertEquals(requestedRowCount, 10);
                assertRowCount(10);

                var scrollDeferred = Divmod.Defer.Deferred();

                scrollDeferred.addCallback(
                    function(requestedRowCount) {
                        /* but check a full screenful was requested */
                        self.assertEquals(requestedRowCount, 10);
                        assertRowCount(20);
                    });

                /* only scroll half a screenful */
                self.scroller.scrollBy(5, scrollDeferred);
                return scrollDeferred;
            });
    },

    function actuallyRunTests(self, n) {
        self._preTestDeferred.callback(n);
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
