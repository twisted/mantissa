
// import Mantissa
// import Nevow.Athena.Test
// import Mantissa.ScrollTable

Mantissa.Test.Forms = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.Forms');
Mantissa.Test.Forms.methods(
    function run(self) {
        return self.childWidgets[0].submit();
    });

Mantissa.Test.StatsTest = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.StatsTest');
Mantissa.Test.StatsTest.methods(
    function run(self) {
        return self.callRemote('run');
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
        self._rowHeight = 1;
        self._scrollViewport.style.height = "10px";
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
        self._scrollViewport.scrollTop += rows;
    });

Mantissa.Test.ScrollTable = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.Scrolltable');

Mantissa.Test.ScrollTable.methods(
    function __init__(self, node) {
        Mantissa.Test.ScrollTable.upcall(self, "__init__", node);
        self._preTestDeferred = new Divmod.Defer.Deferred();
    },

    function run(self) {
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

    function run(self) {
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
