// import Mantissa

Mantissa.ScrollTable = {};

Mantissa.ScrollTable.ScrollingWidget = Nevow.Athena.Widget.subclass('Mantissa.ScrollTable.ScrollingWidget');

Mantissa.ScrollTable.ScrollingWidget.methods(
    function __init__(self, node) {
        Mantissa.ScrollTable.ScrollingWidget.upcall(self, '__init__', node);
        self._rows = [];
        self._rowTimeout = null;
        self._requestWaiting = false;
        self._moreAfterRequest = false;

        self._scrollContent = self.nodeByAttribute("class", "scroll-content");
        self._scrollViewport = self.nodeByAttribute('class', 'scroll-viewport');
        self._headerRow = self.nodeByAttribute('class', 'scroll-header-row');
        self.callRemote("getTableMetadata").addCallback(
            function(metadata) {
                /*
                  argument passing convention!  woo, someday soon Javascript
                  will have all the expressiveness of PL/1.  Maybe then we can
                  decide what registers get used to store variables, too!!!!
                */
                var columnNames = metadata[0];
                self.columnTypes = metadata[1];
                var rowCount = metadata[2];
                var currentSort = metadata[3];
                var isAscendingNow = metadata[4];

                /*
                  (OK, seriously, there should be some kind of
                  multiple-value-unpacking that's easier than this, since we
                  want to decrease the number of round-trips as much as
                  possible...)
                */

                self._createRowHeaders(columnNames);
                self.setSortInfo(currentSort, isAscendingNow);
                self.setViewportHeight(rowCount);
                // Go suuuper fast for the first request
                self.scrolled(10);
            });
    },

    function setViewportHeight(self, rowCount) {
        var rowHeight = self._headerRow.clientHeight;
        if (rowHeight == 0) {
            rowHeight = 20; /* IE can't see clientHeight on some nodes...? */
        }
        /* actually this is wrong, we should calculate from a dummy
            row, but blah templates or something. */

        self._rowHeight = rowHeight;
        var scrollContentHeight = rowHeight * rowCount;
        self._scrollContent.style.height = scrollContentHeight + 'px';
    },

    function adjustViewportHeight(self, rowCount) {
        var height = parseInt(self._scrollContent.style.height);
        self._scrollContent.style.height = height + (self._rowHeight * rowCount) + "px";
    },

    function _getSomeRows(self) {
        var scrollViewportHeight = self._scrollViewport.clientHeight;
        var desiredRowCount = Math.ceil((scrollViewportHeight) / self._rowHeight);

        var firstRow = Math.floor(self._scrollViewport.scrollTop / self._rowHeight);

        var requestNeeded = false;

        for (var i = 0; i < desiredRowCount; i++) {
            if (typeof self._rows[firstRow] === 'undefined') {
                requestNeeded = true;
                break;
            }
            firstRow++;
        }

        if (!requestNeeded) {
            return Divmod.Defer.succeed(1);
        }

        /* do we have the rows we need ? */

        return self.callRemote("requestRowRange", firstRow, firstRow + desiredRowCount).addCallback(
            function(rowData) {
                return self.createRows(firstRow, rowData);
            });
    },

    function createRows(self, idx, rowData) {
        MochiKit.Base.map(
            function(row) {
                if (typeof self._rows[idx] === 'undefined') {
                    self._createRow(idx, row);
                }
                idx++;
            },
            rowData);
    },

    function formatDate(self, date) {
        return date.toUTCString();
    },
    
    function massageColumnValue(self, columnName, columnType, columnValue) {
        if(columnType == 'timestamp') {
            return self.formatDate(new Date(columnValue * 1000));
        }
	if(columnValue ==  null) {
            return '';
	}
        return columnValue;
    },

    function makeCellElement(self, colName, rowData) {
        return MochiKit.DOM.DIV({"class": "scroll-cell"},
                                self.massageColumnValue(
                                     colName, self.columnTypes[colName], rowData[colName]));
    },

    function _createRow(self, rowOffset, rowData) {
        var cells = [];

        for(var colName in rowData) {
            if(!(colName in self._columnOffsets) || self.skipColumn(colName)) {
                continue;
            }
            cells.push([colName, self.makeCellElement(colName, rowData)]);
        }

        cells = cells.sort(
            function(data1, data2) {
                var a = self._columnOffsets[data1[0]];
                var b = self._columnOffsets[data2[0]];

                if (a<b) {
                    return -1;
                }
                if (a>b) {
                    return 1;
                }
                return 0;
            });

        cells = MochiKit.Base.map.apply(null, [null].concat(cells))[1];
        var rowNode = self.makeRowElement(rowOffset, rowData, cells);

        self._rows[rowOffset] = [rowData, rowNode];
        self._scrollContent.appendChild(rowNode);
    },

    function makeRowElement(self, rowData, cells) {
        return MochiKit.DOM.A(
            {"class": "scroll-row",
             "href": rowData['__id__']},
            cells);
    },

    function skipColumn(self, name) {
        return false;
    },

    function _createRowHeaders(self, columnNames) {
        var capitalize = function(s) {
            var words = s.split(/ /);
            var capped = "";
            for(var i = 0; i < words.length; i++) {
                capped += words[i].substr(0, 1).toUpperCase();
                capped += words[i].substr(1, words[i].length) + " ";
            }
            return capped;
        }

        var headerRow = self._headerRow;
        var columnOffsets = {};
        var headerNodes = [];
        for( var i = 0; i < columnNames.length; i++ ) {
            if(self.skipColumn(columnNames[i])) {
                continue;
            }
            columnOffsets[columnNames[i]] = i;
            (function () {
                var bindName = columnNames[i];
                var displayName;

                if(self.columnAliases && bindName in self.columnAliases) {
                    displayName = self.columnAliases[bindName];
                } else {
                    displayName = capitalize(bindName);
                }
                    
                /*
                 * ^ Thank you, brilliant JavaScript designers, for inventing
                 * a whole new language.  This is _way_ better than (let ()).
                 */
                var headerNode = self.makeHeaderRow(bindName, displayName);
                headerRow.appendChild(headerNode);
                headerNodes.push(headerNode);
            })();
        }
        self._headerNodes = headerNodes;
        self._columnOffsets = columnOffsets;
    },

    function makeHeaderRow(self, bindName, displayName) {
        return MochiKit.DOM.DIV({"class": "scroll-column-header",
                    onclick: function () {
                    /* XXX real-time feedback, ugh */
                    self.callRemote("resort", bindName).addCallback(
                        function(isAscendingNow) {
                            self.setSortInfo(bindName, isAscendingNow);
                            self.emptyAndRefill();
                        })
                        }}, displayName);
    },

    function emptyAndRefill(self) {
        for (var whichRow = 0; whichRow < self._rows.length; whichRow++) {
            if (typeof self._rows[whichRow] !== 'undefined') {
                var rowNode = self._rows[whichRow][1];
                rowNode.parentNode.removeChild(rowNode);
            }
        }
        self._rows = [];
        self.scrolled();
    },

    function setSortInfo(self, currentSortColumn, isAscendingNow) {
        for(var j = 0; j < self._headerNodes.length; j++) {
            while(1 < self._headerNodes[j].childNodes.length) {
                self._headerNodes[j].removeChild(self._headerNodes[j].lastChild);
            }
        }
        var c;
        if(isAscendingNow) {
            c = '\u2191'; // up arrow
        } else {
            c = '\u2193'; // down arrow
        }
        self._headerNodes[self._columnOffsets[currentSortColumn]].appendChild(
            MochiKit.DOM.SPAN({"class": "sort-arrow"}, c));
    },

    function scrolled(self, proposedTimeout) {
        if (typeof proposedTimeout === 'undefined') {
            proposedTimeout = 250;
        }
        if (self._requestWaiting) {
            self._moreAfterRequest = true;
            return;
        }
        if (self._rowTimeout !== null) {
            clearTimeout(self._rowTimeout);
        }
        self._rowTimeout = setTimeout(
            function () {
                self._rowTimeout = null;
                self._requestWaiting = true;
                var rowCount = self._rows.length;
                self._getSomeRows().addBoth(
                    function (rslt) {
                        self._requestWaiting = false;
                        if (self._moreAfterRequest) {
                            self._moreAfterRequest = false;
                            self.scrolled();
                        }
                        if(rowCount < self._rows.length) {
                            self.cbRowsFetched();
                        }
                        return rslt;
                        
                    });
            },
            proposedTimeout);
    },

    function cbRowsFetched(self) {});
