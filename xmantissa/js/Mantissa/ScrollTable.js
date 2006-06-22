// import Mantissa

Mantissa.ScrollTable.ScrollingWidget = Nevow.Athena.Widget.subclass('Mantissa.ScrollTable.ScrollingWidget');

Mantissa.ScrollTable.ScrollingWidget.methods(
    function __init__(self, node) {
        Mantissa.ScrollTable.ScrollingWidget.upcall(self, '__init__', node);
        self._rows = [];
        self._rowTimeout = null;
        self._requestWaiting = false;
        self._moreAfterRequest = false;

        self.scrollingDown = true;
        self.lastScrollPos = 0;

        self._scrollContent = self.nodeByAttribute("class", "scroll-content");
        self._scrollViewport = self.nodeByAttribute('class', 'scroll-viewport');
        self._headerRow = self.nodeByAttribute('class', 'scroll-header-row');
        self.setRowHeight();

        self.callRemote("getTableMetadata").addCallback(
            function(metadata) {
                /*
                argument passing convention!  woo, someday soon Javascript
                will have all the expressiveness of PL/1.  Maybe then we can
                decide what registers get used to store variables, too!!!!
                */

                (function(columnNames, columnTypes, rowCount, currentSort, isAscendingNow) {
                    /*
                    (OK, seriously, there should be some kind of
                    multiple-value-unpacking that's easier than this, since we
                    want to decrease the number of round-trips as much as
                    possible...)
                    */

                    self.columnTypes = metadata[1];

                    self._createRowHeaders(columnNames);
                    self.setSortInfo(currentSort, isAscendingNow);
                    self.setViewportHeight(rowCount);

                    // Go suuuper fast for the first request

                    self.scrolled(10);

                }).apply(null, metadata);
            });
    },

    function setRowHeight(self) {
        var r = MochiKit.DOM.DIV({"style": "visibility: hidden",
                                  "class": "scroll-row"},
                    [MochiKit.DOM.DIV({"class": "scroll-cell",
                                       "style": "float: none"}, "TEST!!!")]);

        self._scrollContent.appendChild(r);
        var rowHeight = Divmod.Runtime.theRuntime.getElementSize(r).h;
        if(rowHeight == 0) {
            rowHeight = Divmod.Runtime.theRuntime.getElementSize(self._headerRow).h;
        }
        if(rowHeight == 0) {
            rowHeight = 20;
        }
        self._scrollContent.removeChild(r);

        self._rowHeight = rowHeight;
    },

    function setViewportHeight(self, rowCount) {
        var scrollContentHeight = self._rowHeight * rowCount;
        self._scrollContent.style.height = scrollContentHeight + 'px';
    },

    function adjustViewportHeight(self, rowCount) {
        var height = parseInt(self._scrollContent.style.height);
        self._scrollContent.style.height = height + (self._rowHeight * rowCount) + "px";
    },

    function _getSomeRows(self, scrollingDown) {
        var scrollViewportHeight = Divmod.Runtime.theRuntime.getElementSize(self._scrollViewport).h;
        if(!scrollViewportHeight) {
            scrollViewportHeight = parseInt(self._scrollViewport.style.height);
        }
        if(!scrollViewportHeight) {
            scrollViewportHeight = 400;
        }
        var desiredRowCount = Math.ceil(scrollViewportHeight / self._rowHeight);
        var firstRow = Math.floor(self._scrollViewport.scrollTop / self._rowHeight);
        var requestNeeded = false;

        if(scrollingDown) {
            for (var i = 0; i < desiredRowCount; i++) {
                if (typeof self._rows[firstRow] === 'undefined') {
                    requestNeeded = true;
                    break;
                }
                firstRow++;
            }
        } else {
            for (i = 0; i < desiredRowCount; i++) {
                if (typeof self._rows[firstRow+desiredRowCount-1] === 'undefined') {
                    requestNeeded = true;
                     break;
                }
                firstRow--;
            }
        }

        /* do we have the rows we need ? */

        if(!requestNeeded) {
            return Divmod.Defer.succeed(1);
        }

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
        var tzoff = (new Date()).getTimezoneOffset() * 60;
        if(columnType == 'timestamp') {
            return self.formatDate(new Date((columnValue - tzoff) * 1000));
        }
	if(columnValue ==  null) {
            return '';
	}
        return columnValue;
    },

    function makeCellElement(self, colName, rowData) {
        var attrs = {"class": "scroll-cell"};
        if(self.columnWidths && colName in self.columnWidths) {
            attrs["style"] = "width:" + self.columnWidths[colName];
        }
        var node = MochiKit.DOM.DIV(attrs,
                                     self.massageColumnValue(
                                         colName, self.columnTypes[colName][0], rowData[colName]));
        if(self.columnTypes[colName][0] == "fragment") {
            Divmod.Runtime.theRuntime.setNodeContent(node,
                '<div xmlns="http://www.w3.org/1999/xhtml">' + rowData[colName] + '</div>');
        }
        return node;
    },

    function clickEventForAction(self, actionID, rowData) {
        /* override tsis to set a custom onclick for this action */
    },

    function makeActionsCells(self, rowData) {
        var icon, actionID, onclick, content;
        var actions = [];

        var makeOnClick = function(actionID) {
            return function(event) {
                var D = self.callRemote("performAction", actionID, rowData["__id__"]);
                D.addCallback(function(ign) { self.emptyAndRefill() });
                D.addErrback(alert);
                return false;
            }
        }
        var actionData = rowData["actions"];
        for(var i = 0; i < actionData.length; i++) {
            icon = actionData[i]["iconURL"];
            actionID = actionData[i]["actionID"];
            onclick = self.clickEventForAction(actionID, rowData);

            if(!onclick) {
                onclick = makeOnClick(actionID);
            }

            if(icon) {
                content = MochiKit.DOM.IMG({"src": icon, "border": 0});
            } else { content = actionID; }

            actions.push(MochiKit.DOM.A({"href": "#",
                                         "onclick": onclick}, content));
        }

        var attrs = {"class": "scroll-cell"};
        if(self.columnWidths && "actions" in self.columnWidths) {
            attrs["style"] = "width:" + self.columnWidths["actions"];
        }
        return MochiKit.DOM.DIV(attrs, actions);
    },

    function _createRow(self, rowOffset, rowData) {
        var cells = [];

        for(var colName in rowData) {
            if(!(colName in self._columnOffsets) || self.skipColumn(colName)) {
                continue;
            }
            if(colName == "actions") {
                cells.push([colName, self.makeActionsCells(rowData)]);
            } else {
                cells.push([colName, self.makeCellElement(colName, rowData)]);
            }
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

        rowNode.style.position = "absolute";
        rowNode.style.top = (rowOffset * self._rowHeight) + "px";

        self._rows[rowOffset] = [rowData, rowNode];
        self._scrollContent.appendChild(rowNode);
    },

    function makeRowElement(self, rowOffset, rowData, cells) {
        var attrs = {"class": "scroll-row",
                     "style": "height:" + self._rowHeight + "px"};
        if("actions" in rowData) {
            /* XXX HACK, actions break if the row is clickable */
            return MochiKit.DOM.DIV(attrs, cells);
        }
        return MochiKit.DOM.A(
            {"class": "scroll-row",
             "style": "height:" + self._rowHeight + "px",
             "href": rowData["__id__"]},
            cells);
    },

    /**
     * @param name: column name
     * @return: boolean, indicating whether this column should not be rendered
     */
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
        var sortable, attrs;
        for( var i = 0; i < columnNames.length; i++ ) {
            if(self.skipColumn(columnNames[i])) {
                continue;
            }
            columnOffsets[columnNames[i]] = i;
            (function () {
                var columnName = columnNames[i];
                var displayName;

                if(self.columnAliases && columnName in self.columnAliases) {
                    displayName = self.columnAliases[columnName];
                } else {
                    displayName = capitalize(columnName);
                }

                /*
                 * ^ Thank you, brilliant JavaScript designers, for inventing
                 * a whole new language.  This is _way_ better than (let ()).
                 */
                sortable = self.columnTypes[columnName][1];
                attrs = {"class": "scroll-column-header"};
                if(columnName == "actions") {
                    attrs["class"] = "actions-column-header";
                }
                if(self.columnWidths && columnName in self.columnWidths) {
                    attrs["style"] = "width:" + self.columnWidths[columnName];
                }
                if(sortable) {
                    attrs["class"] = "sortable-" + attrs["class"];
                    attrs["onclick"] = function() {
                        /* XXX real-time feedback, ugh */
                        self.callRemote("resort", columnName).addCallback(
                            function(isAscendingNow) {
                                self.setSortInfo(columnName, isAscendingNow);
                                self.emptyAndRefill();
                            });
                    }
                }


                var headerNode = MochiKit.DOM.DIV(attrs, displayName);
                headerRow.appendChild(headerNode);
                headerNodes.push(headerNode);
            })();
        }
        self._headerNodes = headerNodes;
        self._columnOffsets = columnOffsets;
    },

    /**
     * Remove all rows from scrolltable, as well as our cache of
     * fetched/unfetched rows, scroll the table to the top, and
     * refill it
     */
    function emptyAndRefill(self) {
        self._scrollViewport.scrollTop = 0;
        for (var whichRow = 0; whichRow < self._rows.length; whichRow++) {
            if (self._rows[whichRow] != undefined) {
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

    /* Called in response to *user* initiated scroll events */
    function onScroll(self) {
        var scrollingDown = self.lastScrollPos < self._scrollViewport.scrollTop;
        self.lastScrollPos = self._scrollViewport.scrollTop;
        self.scrolled(undefined, scrollingDown);
    },

    function nonEmptyRowCount(self) {
        return MochiKit.Base.filter(null, self._rows).length;
    },

    function scrolled(self, proposedTimeout, scrollingDown) {
        if (typeof proposedTimeout === 'undefined') {
            proposedTimeout = 250;
        }
        if(scrollingDown == undefined) {
            scrollingDown = true;
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
                var rowCount = self.nonEmptyRowCount();
                self._getSomeRows(scrollingDown).addBoth(
                    function (rslt) {
                        self._requestWaiting = false;
                        if (self._moreAfterRequest) {
                            self._moreAfterRequest = false;
                            self.scrolled();
                        }
                        self.cbRowsFetched(self.nonEmptyRowCount() - rowCount);
                        return rslt;
                    });
            },
            proposedTimeout);
    },

    function cbRowsFetched(self) {});
