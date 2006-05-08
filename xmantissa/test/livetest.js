
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
        self._rowFetches = 0;
    },
    
    function cbRowsFetched(self, n) {
        self._rowFetches++;
        if(self._rowFetches == 1) {
            self.widgetParent.scroller = self;
            self.widgetParent.actuallyRunTests(n);
        }
    });

Mantissa.Test.ScrollTable = Nevow.Athena.Test.TestCase.subclass('Mantissa.Test.Scrolltable');

Mantissa.Test.ScrollTable.methods(
    function __init__(self, node) {
        Mantissa.Test.ScrollTable.upcall(self, "__init__", node);
        self._preTestDeferred = new Divmod.Defer.Deferred();
    },

    function run(self) {
        return self._preTestDeferred.addCallback(
            function(rowCount) {
                self.assertEquals(rowCount, 10);
                var rows = Nevow.Athena.NodesByAttribute(self.scroller.node, "class", "scroll-row");
                var cell;
                for(var i = 0; i < rows.length; i++) {
                    cell = Nevow.Athena.FirstNodeByAttribute(rows[i], "class", "scroll-cell");
                    self.assertEquals(cell.firstChild.nodeValue, parseInt(i));
                }
            });
    },

    function actuallyRunTests(self, n) {
        self._preTestDeferred.callback(n);
    });
