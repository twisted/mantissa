
// import Mantissa
// import Nevow.Athena.Test
// import Mantissa.ScrollTable

Mantissa.Test.Forms = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.Forms');
Mantissa.Test.Forms.methods(
    function run(self) {
        return self.childWidgets[0].submit();
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

