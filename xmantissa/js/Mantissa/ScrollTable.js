// import Mantissa
// import MochiKit
// import MochiKit.Base
// import MochiKit.Iter
// import MochiKit.DOM


Mantissa.ScrollTable.NoSuchWebID = Divmod.Error.subclass("Mantissa.ScrollTable.NoSuchWebID");
Mantissa.ScrollTable.NoSuchWebID.methods(
    function __init__(self, webID) {
        self.webID = webID;
    },

    function toString(self) {
        return "WebID " + self.webID + " not found";
    });


Mantissa.ScrollTable.Action = Divmod.Class.subclass('Mantissa.ScrollTable.Action');
/**
 * An action that can be performed on a scrolltable row.
 * (Currently on a single scrolltable row at a time).
 *
 * @ivar name: internal name for this action.  this will be used server-side
 *             to look up the action method.
 *
 * @ivar displayName: external name for this action.
 *
 * @ivar handler: optional.  function that will be called when the remote
 *                method successfully returns.  it will be passed the
 *                L{ScrollingWidget} the row was clicked in, the row that was
 *                clicked (a mapping of column names to values) and the result
 *                of the remote call that was made.  if not set, no action
 *                will be taken.  Alternatively, you can subclass and override
 *                L{handleSuccess}.
 *
 * @ivar icon: optional.  if set, then it will be used for the src attribute of
 *             an <IMG> element that will get placed inside the action link,
 *             instead of C{name}.
 */
Mantissa.ScrollTable.Action.methods(
    function __init__(self, name, displayName, handler/*=undefined*/, icon/*=undefined*/) {
        self.name = name;
        self.displayName = displayName;
        self._successHandler = handler;
        self.icon = icon;
    },

    /**
     * Called by onclick handler created in L{toNode}.
     * Responsible for calling remote method, and dispatching the result to
     * C{self.handler}, if one is set.
     *
     * Arguments are the same as L{toNode}
     *
     * @rtype: L{Divmod.Defer.Deferred}
     */
    function enact(self, scrollingWidget, row) {
        var D = scrollingWidget.callRemote(
                    "performAction", self.name, row.__id__);
        return D.addCallbacks(
                function(result) {
                    return self.handleSuccess(scrollingWidget, row, result);
                },
                function(err) {
                    return self.handleFailure(scrollingWidget, row, err);
                });
    },

    /**
     * Called when the remote method successfully returns, with its result.
     * Calls the function supplied as C{handler} to L{__init__}, if defined.
     *
     * First two arguments are the same as L{toNode}
     */
    function handleSuccess(self, scrollingWidget, row, result) {
        if(self._successHandler) {
            return self._successHandler(scrollingWidget, row, result);
        }
    },

    /**
     * Called when the remote method, or one of its callbacks throws an error.
     * Displays an error dialog to the user.
     *
     * First two arguments are the same as L{toNode}
     */
    function handleFailure(self, scrollingWidget, row, err) {
        scrollingWidget.showErrorDialog("performAction", err);
    },

    /**
     * Called by L{Mantissa.ScrollTable.ScrollingWidget}.
     * Responsible for turning this action into a link node.
     *
     * @param scrollingWidget: L{Mantissa.ScrollTable.ScrollingWidget}
     * @param row: L{Object} mapping column names to column values of the row
     *             that this action will act on when clicked
     */
    function toNode(self, scrollingWidget, row) {
        var onclick = function() {
            self.enact(scrollingWidget, row);
            return false;
        }
        var linkBody;
        if(self.icon) {
            linkBody = MochiKit.DOM.IMG({border: 0, src: self.icon});
        } else {
            linkBody = self.displayName;
        }
        return MochiKit.DOM.A({onclick: onclick, href: "#"}, linkBody);
    },

    /**
     * Called by L{Mantissa.ScrollTable.ScrollingWidget}.
     *
     * @type row: C{object}
     * @return: boolean indicating whether this action should be enabled for
     * C{row}
     */
    function enableForRow(self, row) {
        return true;
    });

Mantissa.ScrollTable.ScrollModel = Divmod.Class.subclass('Mantissa.ScrollTable.ScrollModel');
Mantissa.ScrollTable.ScrollModel.methods(
    function __init__(self) {
        self._rows = [];
        self._totalRowCount = 0;
    },

    /**
     * @rtype: integer
     * @return: The number of rows in the model which we have already fetched.
     */
    function rowCount(self) {
        return self._rows.length;
    },

    /**
     * @rtype: integer
     * @return: The total number of rows in the model, i.e. the maximum number
     * of rows we could fetch
     */
    function totalRowCount(self) {
        return self._totalRowCount;
    },

    /**
     * Change the total number of rows in the model.
     * @type count: integer
     */
    function setTotalRowCount(self, count) {
        self._totalRowCount = count;
    },

    /**
     * Retrieve the index for the row data associated with the given webID.
     *
     * @type webID: string
     *
     * @rtype: integer
     *
     * @throw NoSuchWebID: Thrown if the given webID corresponds to no row in
     * the model.
     */
    function findIndex(self, webID) {
        for (var i = 0; i < self._rows.length; i++) {
            if (self._rows[i] != undefined && self._rows[i].__id__ == webID) {
                return i;
            }
        }
        throw Mantissa.ScrollTable.NoSuchWebID(webID);
    },

    /**
     * Set the data associated with a particular row.
     *
     * @type index: integer
     * @param index: The index of the row for which to set the data.
     *
     * @type data: The data to associate with the row.
     *
     * @throw Divmod.IndexError: Thrown if the row's index is less than zero.
     * @throw Error: Thrown if the row data's __id__ property is not a string.
     */
    function setRowData(self, index, data) {
        if (index < 0) {
            throw Divmod.IndexError("Specified index out of bounds in setRowData.");
        }
        /*
         * XXX I hate `typeof'.  It is an abomination.  Why the hell is
         *
         *  typeof '' == 'string'
         *
         * but not
         *
         *  '' instanceof String?"
         *
         */
        if (typeof data.__id__ != 'string') {
            throw new Error("Specified row data has invalid __id__ property.");
        }
        self._rows[index] = data;
    },

    /**
     * Retrieve the row data for the row at the given index.
     *
     * @type index: integer
     *
     * @rtype: object
     * @return: The structured data associated with the row at the given index.
     *
     * @throw Divmod.IndexError: Thrown if the given index is out of bounds.
     */
    function getRowData(self, index) {
        if (index < 0 || index >= self._rows.length) {
            throw Divmod.IndexError("Specified index out of bounds in getRowData.");
        }
        if (self._rows[index] === undefined) {
            return undefined;
        }
        return self._rows[index];
    },

    /**
     * Retrieve an array of indices for which local data is available.
     */
    function getRowIndices(self) {
        var indices = Divmod.dir(self._rows);
        for (var i = 0; i < indices.length; ++i) {
            indices[i] = parseInt(indices[i]);
        }
        return indices.sort(
            function(a, b) {
                if (a < b) {
                    return -1;
                }
                if (a > b) {
                    return 1;
                }
                return 0;
            });
    },

    /**
     * Find the row data for the row with web id C{webID}.
     *
     * @type webID: string
     *
     * @rtype: object
     * @return: The structured data associated with the given webID.
     *
     * @throw Error: Thrown if the given webID is not found.
     */
    function findRowData(self, webID) {
        return self.getRowData(self.findIndex(webID));
    },

    /**
     * Find the first row which appears after C{row} in the scrolltable and
     * satisfies C{predicate}
     *
     * @type webID: string
     * @param webID: The web ID of the node at which to begin.
     *
     * @type predicate: function(rowIndex, rowData, rowNode) -> boolean
     * @param predicate: A optional callable which, if supplied, will be called
     * with each row to determine if it suitable to be returned.
     *
     * @rtype: string
     * @return: The web ID for the first set of arguments that satisfies
     * C{predicate}.  C{null} is returned if no rows are found after the given
     * web ID.
     */
    function findNextRow(self, webID, predicate) {
        var row;
        for (var i = self.findIndex(webID) + 1; i < self.rowCount(); ++i) {
            row = self.getRowData(i);
            if (row != undefined) {
                if (!predicate || predicate.call(null, i, row, row.__node__)) {
                    return row.__id__;
                }
            }
        }
        return null;
    },

    /**
     * Same as L{findNextRow}, except returns the first row which appears before C{row}
     */
    function findPrevRow(self, webID, predicate) {
        var row;
        for (var i = self.findIndex(webID) - 1; i > -1; --i) {
            row = self.getRowData(i);
            if (row != undefined) {
                if (!predicate || predicate.call(null, i, row, row.__node__)) {
                    return row.__id__;
                }
            }
        }
        return null;
    },

    /**
     * Remove a particular row from the scrolltable.
     *
     * @type webID: integer
     * @param webID: The index of the row to remove.
     *
     * @return: The row data which was removed.
     */
    function removeRow(self, index) {
        return self._rows.splice(index, 1)[0];
    },

    /**
     * Remove all rows from the scrolltable.
     */
    function empty(self) {
        self._rows = [];
    });

Mantissa.ScrollTable.PlaceholderModel = Divmod.Class.subclass('Mantissa.ScrollTable.PlaceholderModel');
Mantissa.ScrollTable.PlaceholderModel.methods(
    function __init__(self) {
        self._placeholderRanges = [];
    },

    /**
     * Find the index of the placeholder which spans the area that the row at
     * C{rowIndex} will appear at
     *
     * @param rowIndex: integer
     *
     * @rtype: integer
     */
    function findPlaceholderIndexForRowIndex(self, rowIndex) {
        var pranges = self._placeholderRanges,
            len = pranges.length,
            lo = 0, hi = len, mid, midnew;

        while(true) {
            midnew = Math.floor((lo + hi) / 2);
            if(len-1 < midnew || midnew < 0 || mid == midnew) {
                return null;
            }
            mid = midnew;
            if(pranges[mid].stop <= rowIndex) {
                lo = mid + 1;
            } else if(rowIndex < pranges[mid].start) {
                hi = mid - 1;
            } else {
                return mid;
            }
       }
    },

    /**
     * Find the index of the first placeholder that starts after the row at
     * index C{rowIndex}.
     *
     * @param rowIndex: index of the reference row
     * @type rowIndex: integer
     *
     * @rtype: placeholder or null
     */
    function findFirstPlaceholderIndexAfterRowIndex(self, rowIndex) {
        var pranges = self._placeholderRanges,
            len = pranges.length,
            lo = 0, hi = len, mid;

        while(true) {
            mid = Math.floor((lo + hi) / 2);
            if(len-1 < mid || mid < 0) {
                return null;
            }
            /* this is difficult to think about.  what we're trying to say is
             * that we're done when we find the placeholder such that:
             *       * the placeholder starts after the index of the row we want
             *       * the placeholder before it stops before the index of the row we want
             *    OR
             *       * the placeholder starts after the index of the row we want
             *       * there is no placeholder before it
             *
             *  example:
             *
             *  | start: 0, stop: 1 |
             *  | start: 1, stop: 2 |
             *  | start: 3, stop: 4 |
             *  | start: 5, stop: 6 |
             *
             *  for a row index of 2, we want the 3 - 4 placeholder because:
             *       * 1 - 2 stops before the index of the row we want
             *       * 3 - 4 starts after the index of the row we want
             */
            if(pranges[mid].start <= rowIndex) {
                lo = mid + 1;
            } else if(0 < mid && rowIndex < pranges[mid-1].stop-1) {
                hi = mid - 1;
            } else {
                return mid;
            }
        }
    },

    /**
     * Called after a row has been removed.  Adjusts the placeholder state to
     * take this into account.
     *
     * @param rowIndex: index of the row that was removed
     * @type rowIndex: integer
     */
    function removedRow(self, rowIndex) {
        var i = self.findFirstPlaceholderIndexAfterRowIndex(rowIndex),
            pranges = self._placeholderRanges;
        if(i == null) {
            return;
        }
        for(; i < pranges.length; i++) {
            pranges[i].start--;
            pranges[i].stop--;
        }
    },

    /**
     * Find the placeholder object stored at index C{index}
     *
     * @type index: integer
     * @rtype: placeholder
     */
    function getPlaceholderWithIndex(self, index) {
        return self._placeholderRanges[index];
    },

    /**
     * Get the number of placeholders
     *
     * @rtype: integer
     */
    function getPlaceholderCount(self) {
        return self._placeholderRanges.length;
    },

    /**
     * Create and register a placeholder which extends from the zeroth row to
     * the end of the last row, overwriting any other placeholders.
     *
     * @param totalRowCount: total number of rows
     * @param node: same as L{createPlaceholder}'s C{node} argument
     */
    function registerInitialPlaceholder(self, totalRowCount, node) {
        self._placeholderRanges = [self.createPlaceholder(0, totalRowCount, node)];
    },

    /**
     * Replace placeholder with index C{index} with C{replacement}
     *
     * @type index: integer
     * @type replacement: placeholder
     */
    function replacePlaceholder(self, index, replacement) {
        self._placeholderRanges[index] = replacement;
    },

    /**
     * Divide the placeholder with index C{index} into two placeholders,
     * C{above} and C{below}.
     *
     * @type index: integer
     * @type above: placeholder
     * @type below: placeholder
     */
    function dividePlaceholder(self, index, above, below) {
        self._placeholderRanges.splice.apply(
            self._placeholderRanges, [index, 1].concat([above, below]));
    },

    /**
     * Remove the placeholder at C{index}
     *
     * @type index: integer
     */
    function removePlaceholder(self, index) {
        self._placeholderRanges.splice(index, 1);
    },

    /**
     * Remove all placeholders
     */
    function empty(self) {
        self._placeholderRanges = [];
    },

    /**
     * Create a placeholder which starts at C{start}, stops at C{stop}, and
     * is represented by the DOM node C{node}
     *
     * @param start: the index of the row that the placeholder starts at
     * @param stop: the index of the row that the placeholder stops at
     *
     * @return: object with "start" and "stop" members, corresponding to the
     * arguments of this method
     *
     * For a scrolltable like this:
     * | 0: REAL ROW    |
     * | 1: REAL ROW    |
     * | 2: PLACEHOLDER |
     * | 3: REAL ROW    |
     * the placeholder at index #2 would have start=2 and stop=3
     */
    function createPlaceholder(self, start, stop, node) {
        return {start: start, stop: stop, node: node};
    });


Mantissa.ScrollTable.ScrollingWidget = Nevow.Athena.Widget.subclass('Mantissa.ScrollTable.ScrollingWidget');

Mantissa.ScrollTable.ScrollingWidget.methods(
    function __init__(self, node) {
        Mantissa.ScrollTable.ScrollingWidget.upcall(self, '__init__', node);

        self._rowTimeout = null;
        self._requestWaiting = false;
        self._moreAfterRequest = false;

        self.scrollingDown = true;
        self.lastScrollPos = 0;

        self._scrollViewport = self.nodeByAttribute('class', 'scroll-viewport');
        self._headerRow = self.nodeByAttribute('class', 'scroll-header-row');

        /*
         * A list of Deferreds which have been returned from the L{scrolled}
         * method and have yet to be fired.
         */
        self._scrollDeferreds = [];

        self.model = null;
        self.placeholderModel = Mantissa.ScrollTable.PlaceholderModel();
        self.initializationDeferred = self.initialize();
    },

    /**
     * Retrieve the structural definition of this table.
     *
     * @return: A Deferred which fires with an array with five elements.  They
     * are::
     *
     *    An array of strings naming the columns in this table.
     *
     *    An array of two-arrays giving the type and sortability of the columns
     *    in this table.
     *
     *    An integer giving the number of rows in this table.
     *
     *    A string giving the name of the column by which the table is
     *    currently ordered.
     *
     *    A boolean indicating whether the ordering is currently ascending
     *    (true) or descending (false).
     */
    function getTableMetadata(self) {
        return self.callRemote("getTableMetadata");
    },

    /**
     * Create a ScrollModel and then populate it with an initial set of rows.
     */
    function initialize(self) {
        /*
         * XXX - Make table metadata into arguments to __init__ to save a
         * round-trip.
         */
        return self.getTableMetadata().addCallback(
            function(metadata) {
                self.model = Mantissa.ScrollTable.ScrollModel();
                self.setTableMetadata.apply(self, metadata);
                return self._getSomeRows(true);
            });
    },

    /**
     * Set up the tabular structure of this ScrollTable.
     *
     * @type columnNames: C{Array} of C{String}
     * @param columnNames: Names of the columns visible in this ScrollTable.
     *
     * @type columnTypes: C{Array} of C{String}
     * @param columnTypes: Names of the types of the columns visible in this
     * ScrollTable.
     *
     * @type rowCount: C{Integer}
     * @param rowCount: The total number of rows in the model.
     *
     * @type currentSort: C{String}
     * @param currentSort: The name of the column by which the model is
     * ordered.
     *
     * @type isAscendingNow: C{Boolean}
     * @param isAscendingNow: Whether the sort is ascending.
     *
     * @return: C{undefined}
     */
    function setTableMetadata(self, columnNames, columnTypes, rowCount, currentSort, isAscendingNow) {
        self.columnNames = columnNames;
        self.columnTypes = columnTypes;

        if(self.actions && 0 < self.actions.length) {
            self.columnNames.push("actions");
        }

        self.resetColumns();
        self._setSortHeader(currentSort, isAscendingNow);
        self.model.setTotalRowCount(rowCount);
        self.padViewportWithPlaceholderRow(rowCount);
    },

    /**
     * Update internal state associated with displaying column data.
     *
     * Call this whenever the return value of skipColumn might have changed.
     */
    function resetColumns(self) {
        /* set _columnOffsets before calling _getRowHeight() so that
         * _getRowGuineaPig() can call _createRow() */
        self._columnOffsets = self._getColumnOffsets(self.columnNames);
        self._rowHeight = self._getRowHeight();

        while (self._headerRow.firstChild) {
            self._headerRow.removeChild(self._headerRow.firstChild);
        }

        self._headerNodes = self._createRowHeaders(self.columnNames);
        for (var i = 0; i < self._headerNodes.length; ++i) {
            self._headerRow.appendChild(self._headerNodes[i]);
        }
    },

    /**
     * Retrieve a range of row data from the server.
     *
     * @type firstRow: integer
     * @param firstRow: zero-based index of the first message to retrieve.
     *
     * @type lastRow: integer
     * @param lastRow: zero-based index of the message after the last message
     * to retrieve.
     */
    function getRows(self, firstRow, lastRow) {
        return self.callRemote("requestRowRange", firstRow, lastRow);
    },

    /**
     * Retrieve a range of row data from the server and store it locally.
     *
     * @type firstRow: integer
     * @param firstRow: zero-based index of the first message to retrieve.
     *
     * @type lastRow: integer
     * @param lastRow: zero-based index of the message after the last message
     * to retrieve.
     */
    function requestRowRange(self, firstRow, lastRow) {
        return self.getRows(firstRow, lastRow).addCallback(
            function(rows) {
                self._storeRows(firstRow, lastRow, rows);
                return rows;
            });
    },

    function _storeRows(self, firstRow, lastRow, rows) {
        var rowNodes = [];
        for (var i = firstRow; i < rows.length + firstRow; ++i) {
            row = rows[i - firstRow];
            if (i >= self.model.rowCount() || self.model.getRowData(i) == undefined) {
                row.__node__ = self._createRow(i, row);
                self.model.setRowData(i, row);
                rowNodes.push({index: i, node: row.__node__});
            }
        }
        self._addRowsToViewport(rowNodes);
    },

    /**
     * Add C{rows} to the scroll viewport, replacing or splitting any
     * placeholder rows that are in the way.
     *
     * @param rows: array of objects with "index" and "node" members
     */
    function _addRowsToViewport(self, rows) {
        /* this could be made faster, if we have more than one row that falls
         * inside a single placeholder - we only need to split it once instead
         * of once per row, i think */
        var sviewport = self._scrollViewport,
            pmodel = self.placeholderModel,
            placeholder, placeholders, placeholderEntry, above, below;

        var maybeCreatePlaceholder = function(start, stop, replacing) {
            if(start < stop) {
                var obj = self.placeholderModel.createPlaceholder(
                            start, stop, self.makePlaceholderRowElement(
                                            (stop - start) * self._rowHeight));
                sviewport.insertBefore(obj.node, replacing);
                return obj;
            }
        }

        for(var i = 0; i < rows.length; i++) {
            placeholderIndex = pmodel.findPlaceholderIndexForRowIndex(rows[i].index);
            if(placeholderIndex !== null) {
                placeholder = pmodel.getPlaceholderWithIndex(placeholderIndex);

                above = maybeCreatePlaceholder(
                            placeholder.start, rows[i].index, placeholder.node);

                sviewport.insertBefore(rows[i].node, placeholder.node);

                below = maybeCreatePlaceholder(
                            rows[i].index+1, placeholder.stop, placeholder.node);

                sviewport.removeChild(placeholder.node);

                if(above && below) {
                    pmodel.dividePlaceholder(placeholderIndex, above, below);
                } else if(above || below) {
                    pmodel.replacePlaceholder(placeholderIndex, above || below);
                } else {
                    pmodel.removePlaceholder(placeholderIndex);
                }
            } else {
                sviewport.appendChild(rows[i].node);
            }
        }
    },

    /**
     * Remove the indicated row's data from the model and remove its DOM nodes
     * from the document.
     *
     * @type index: integer
     * @param index: The index of the row to remove.
     *
     * @return: The row data for the removed row.
     */
    function removeRow(self, index) {
        var rowData = self.model.removeRow(index);
        rowData.__node__.parentNode.removeChild(rowData.__node__);
        self.placeholderModel.removedRow(index);
        return rowData;
    },

    /**
     * Retrieve a node which is the same height as rows in the table will be.
     */
    function _getRowGuineaPig(self) {
        return MochiKit.DOM.TR(
            {"style": "visibility: hidden",
             "class": "scroll-row",
             "valign": "center"},
            MochiKit.DOM.TD(
                {"class": "scroll-cell"},
                MochiKit.DOM.A({"href": "#"}, "TEST!!!")));
    },

    /**
     * Determine the height of a row in this scrolltable.
     */
    function _getRowHeight(self) {
        var node = self._getRowGuineaPig();
        var rowHeight;

        /*
         * Put the node into the document so that the browser actually figures
         * out how tall it is.  Don't put it into the scrolltable itself or
         * anything clever like that, in case the scrolltable has some style
         * applied to it that would mess things up. (XXX The body could have a
         * style applied to it that could mess things up? -exarkun)
         */
        var tableNode = MochiKit.DOM.TABLE(null, node);
        document.body.appendChild(tableNode);
        rowHeight = Divmod.Runtime.theRuntime.getElementSize(node).h;
        document.body.removeChild(tableNode);

        if (rowHeight == 0) {
            rowHeight = Divmod.Runtime.theRuntime.getElementSize(self._headerRow).h;
        }

        if (rowHeight == 0) {
            rowHeight = 20;
        }

        return rowHeight;
    },

    /**
     * Set the display height of the scroll view DOM node to a height
     * appropriate for displaying the given number of rows, by appending
     * C{rowCount} placeholder rows to it
     *
     * @type rowCount: integer
     * @param rowCount: The number of rows which should fit into the view node.
     */
    function padViewportWithPlaceholderRow(self, rowCount) {
        var row = self.makePlaceholderRowElement(rowCount * self._rowHeight);
        self._scrollViewport.appendChild(row);

        self.placeholderModel.registerInitialPlaceholder(rowCount, row);
    },

    /**
     * This method is responsible for returning the height of the scroll
     * viewport in pixels.  The result is used to calculate the number of
     * rows needed to fill the screen.
     *
     * Under a variety of conditions (for example, a "display: none" style
     * applied to the viewport node), the browser may not report a height for
     * the viewport.  In this case, fall back to the size of the page.  This
     * will result in too many rows being requested, maybe, which is not very
     * harmful.
     */
    function getScrollViewportHeight(self) {
        var height = Divmod.Runtime.theRuntime.getElementSize(
            self._scrollViewport).h;

        /*
         * Firefox returns 0 for the clientHeight of display: none elements, IE
         * seems to return the height of the element before it was made
         * invisible.  There also seem to be some cases where the height will
         * be 0 even though the element has been added to the DOM and is
         * visible, but the browser hasn't gotten around to sizing it
         * (presumably in a different thread :( :( :() yet.  Default to the
         * full window size for these cases.
         */

        if (height == 0 || isNaN(height)) {
            /*
             * Called too early, just give the page height.  at worst we'll end
             * up requesting 5 extra rows or whatever.
             */
            height = Divmod.Runtime.theRuntime.getPageSize().h;
        }
        return height;
    },

    /**
     * Figure out the start and end indexes of rows that should be requested
     *
     * @param scrollingDown: A flag indicating whether we are scrolling down,
     * and so whether the requested rows should be below the current position
     * or not.
     *
     * @return: pair of [startIndex, stopIndex] or null if there isn't a
     * useful row range to request
     */
    function _calculateDesiredRowRange(self, scrollingDown) {
        var scrollViewportHeight = self.getScrollViewportHeight();
        var desiredRowCount = Math.ceil(scrollViewportHeight / self._rowHeight);
        var firstRow = Math.floor(self._scrollViewport.scrollTop / self._rowHeight);
        var requestNeeded = false;
        var i;

        /*
         * Never do less than 1 row of work.  The most likely cause of
         * desiredRowCount being 0 is that the browser screwed up some height
         * calculation.  We'll at least try to get 1 row (and maybe we should
         * actually try to get more than that).
         */
        if (desiredRowCount < 1) {
            desiredRowCount = 1;
        }

        if (scrollingDown) {
            for (i = 0; i < desiredRowCount; i++) {
                if (firstRow >= self.model.rowCount() || self.model.getRowData(firstRow) == undefined) {
                    requestNeeded = true;
                    break;
                }
                firstRow++;
            }
        } else {
            for (i = 0; i < desiredRowCount; i++) {
                if (self.model.getRowData(firstRow + desiredRowCount - 1) == undefined) {
                    requestNeeded = true;
                    break;
                }
                firstRow--;
            }
        }
        if(!requestNeeded) {
            return;
        }
        return [firstRow, firstRow+desiredRowCount];
    },

    /**
     * Retrieve some rows from the server which are likely to be useful given
     * the current state of this ScrollingWidget.  Update the ScrollModel when
     * the results arrive.
     *
     * @param scrollingDown: A flag indicating whether we are scrolling down,
     * and so whether the requested rows should be below the current position
     * or not.
     *
     * @return: A Deferred which fires with an Array of rows retrieve when
     * the update has finished.
     */
    function _getSomeRows(self, scrollingDown) {
        var range = self._calculateDesiredRowRange(scrollingDown);

        /* do we have the rows we need ? */
        if (!range) {
            return Divmod.Defer.succeed([]);
        }

        return self.requestRowRange.apply(self, range);
    },

    /**
     * Convert a Date instance to a human-readable string.
     *
     * @type when: C{Date}
     * @param when: The time to format as a string.
     *
     * @type now: C{Date}
     * @param now: If specified, the date which will be used to determine how
     * much context to provide in the returned string.
     *
     * @rtype: C{String}
     * @return: A string describing the date C{when} with as much information
     * included as is required by context.
     */
    function formatDate(self, date, /* optional */ now) {
        return date.toUTCString();
    },

    /**
     * @param columnName: The name of the column for which this is a value.
     *
     * @param columnType: A string which might indicate the data type of the
     * values in this column (if you have the secret decoder ring).
     *
     * @param columnValue: An object received from the server.
     *
     * @return: The object to put into the DOM for this value.
     */
    function massageColumnValue(self, columnName, columnType, columnValue) {
        if(columnType == 'timestamp') {
            return self.formatDate(new Date(columnValue * 1000));
        }
	if(columnValue ==  null) {
            return '';
	}
        return columnValue;
    },

    /**
     * Make an element which will be displayed for the value of one column in
     * one row.
     *
     * @param colName: The name of the column for which to make an element.
     *
     * @param rowData: An object received from the server.
     *
     * @return: A DOM node.
     */
    function makeCellElement(self, colName, rowData) {
        var attrs = {"class": "scroll-cell"};
        if(self.columnWidths && colName in self.columnWidths) {
            attrs["style"] = "width:" + self.columnWidths[colName];
        }
        var node = MochiKit.DOM.TD(
            attrs,
            /* unfortunately we have to put a link inside each cell - IE
             * doesn't seem to display rows if they are anchors with
             * display: table-row
             */
            MochiKit.DOM.A({"style": "display: block",
                            "href": rowData.__id__},
                self.massageColumnValue(
                    colName,
                    self.columnTypes[colName][0],
                    rowData[colName])));

        if (self.columnTypes[colName][0] == "fragment") {
            Divmod.Runtime.theRuntime.setNodeContent(node.firstChild,
                '<div xmlns="http://www.w3.org/1999/xhtml">' + rowData[colName] + '</div>');
        }
        return node;
    },

    /**
     * Execute C{thunk} while ignoring DOM events originating from C{node}.
     * Do this by temporarily removing C{node} from the document.
     *
     * @type thunk: function
     * @type node: node
     *
     * @return: undefined
     */
    function whileIgnoringDOMEvents(self, thunk, node) {
        var parent = node.parentNode;
        if(parent == null) {
            throw new Error(node + " does not have a parent");
        }
        var nextsib = node.nextSibling,
            cleanup = function() {
                if(nextsib) {
                    parent.insertBefore(node, nextsib);
                } else {
                    parent.appendChild(node);
                }
            };

        parent.removeChild(node);

        try {
            thunk();
        } catch(e) {
            cleanup();
            throw e;
        }
        cleanup();
    },

    /**
     * Remove all row nodes, including placeholder nodes from the scrolltable
     * viewport node.  Also empty the model.
     */
    function empty(self) {
        var sviewport = self._scrollViewport;

        self.whileIgnoringDOMEvents(
            function() {
                while(sviewport.firstChild) {
                    sviewport.removeChild(sviewport.firstChild);
                }
            },
            sviewport);

        self.model.empty();
        self.placeholderModel.empty();
    },

    /**
     * Remove all rows from scrolltable, as well as our cache of
     * fetched/unfetched rows, scroll the table to the top, and
     * refill it.
     */
    function emptyAndRefill(self) {
        self.empty();
        return self.refill();
    },

    /**
     * Request the current size (number of rows) from the server
     */
    function getSize(self) {
        return self.callRemote("requestCurrentSize");
    },

    /**
     * Refill an empty scrolltable by asking for more rows, creating
     * placeholder rows and adding a screenful of fresh rows.
     *
     * @return: Deferred firing with pair of [total size, fetched rows]
     */
    function refill(self) {
        var range = self._calculateDesiredRowRange(true);
        if(range[0] != 0) {
            throw new Error("expected first needed row to have index 0");
        }

        var result = Divmod.Defer.gatherResults(
                        [self.getSize(),
                         self.getRows(0, range[1])]);

        return result.addCallback(
                function(response) {
                    self.padViewportWithPlaceholderRow(response[0]);
                    self.model.setTotalRowCount(response[0]);
                    self._storeRows.apply(self, range.concat([response[1]]));
                    return response;
                });
    },

    /**
     * Tell the server to change the sort key for this table.
     *
     * @type columnName: string
     * @param columnName: The name of the new column by which to sort.
     */
    function resort(self, columnName) {
        var result = self.callRemote("resort", columnName);
        result.addCallback(function(isAscendingNow) {
                self._setSortHeader(columnName, isAscendingNow);
                self.emptyAndRefill();
            });
        return result;
    },

    /**
     * @type rowData: object
     *
     * @return: actions that are enabled for row C{rowData}
     * @rtype: array of L{Mantissa.ScrollTable.Action} instances
     */
    function getActionsForRow(self, rowData) {
        var enabled = [];
        for(var i = 0; i < self.actions.length; i++) {
            if(self.actions[i].enableForRow(rowData)) {
                enabled.push(self.actions[i]);
            }
        }
        return enabled;
    },

    /**
     * Make a node with some event handlers to perform actions on the row
     * specified by C{rowData}.
     *
     * @param rowData: Some data received from the server.
     *
     * @return: A DOM node.
     */
    function _makeActionsCells(self, rowData) {
        var actions = self.getActionsForRow(rowData);
        for(var i = 0; i < actions.length; i++) {
            actions[i] = actions[i].toNode(self, rowData);
        }
        var attrs = {"class": "scroll-cell"};
        if(self.columnWidths && "actions" in self.columnWidths) {
            attrs["style"] = "width:" + self.columnWidths["actions"];
        }
        return MochiKit.DOM.TD(attrs, actions);
    },

    /**
     * Make a DOM node for the given row.
     *
     * @param rowOffset: The index in the scroll model of the row data being
     * rendered.
     *
     * @param rowData: The row data for which to make an element.
     *
     * @return: A DOM node.
     */
    function _createRow(self, rowOffset, rowData) {
        var cells = [];

        for(var colName in rowData) {
            if(!(colName in self._columnOffsets) || self.skipColumn(colName)) {
                continue;
            }
            cells.push([colName, self.makeCellElement(colName, rowData)]);
        }
        if(self.actions && 0 < self.actions.length) {
            cells.push(["actions", self._makeActionsCells(rowData)]);
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

        var nodes = [];
        for (var i = 0; i < cells.length; ++i) {
            nodes.push(cells[i][1]);
        }
        return self.makeRowElement(rowOffset, rowData, nodes);
    },

    /**
     * Create a element to represent the given row data in the scrolling
     * widget.
     *
     * @param rowOffset: The index in the scroll model of the row data being
     * rendered.
     *
     * @param rowData: The row data for which to make an element.
     *
     * @param cells: Array of elements which represent the column data for this
     * row.
     *
     * @return: An element
     */
    function makeRowElement(self, rowOffset, rowData, cells) {
        var style = "height: " + self._rowHeight + "px";
        if(rowOffset % 2) {
            style += "; background-color: #F0F0F0";
        }
        return MochiKit.DOM.TR(
            {"class": "scroll-row",
             "style": style,
             "valign": "center"},
            cells);
    },

    /**
     * Make a placeholder row
     *
     * @type height: integer
     * @param height: the height of the placeholder row
     *
     * @rtype: node
     */
    function makePlaceholderRowElement(self, height) {
        return MochiKit.DOM.TR(
                {"class": "placeholder-scroll-row",
                 "style": "height: " + height + "px"},
                MochiKit.DOM.TD({"class": "placeholder-cell"}));
    },

    /**
     * @param name: column name
     * @return: boolean, indicating whether this column should not be rendered
     */
    function skipColumn(self, name) {
        return false;
    },

    /**
     * Return an object the properties of which are named like columns and
     * refer to those columns' display indices.
     */
    function _getColumnOffsets(self, columnNames) {
        var columnOffsets = {};
        for( var i = 0; i < columnNames.length; i++ ) {
            if(self.skipColumn(columnNames[i])) {
                continue;
            }
            columnOffsets[columnNames[i]] = i;
        }
        return columnOffsets;
    },

    /**
     * Return an Array of nodes to be used as column headers.
     *
     * @param columnNames: An Array of strings naming the columns in this
     * table.
     */
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

        var headerNodes = [];
        var sortable, attrs;

        for (var i = 0; i < columnNames.length; i++ ) {
            if(self.skipColumn(columnNames[i])) {
                continue;
            }

            var columnName = columnNames[i];
            var displayName;

            if(self.columnAliases && columnName in self.columnAliases) {
                displayName = self.columnAliases[columnName];
            } else {
                displayName = capitalize(columnName);
            }

            attrs = {"class": "scroll-column-header"};

            if(self.columnWidths && columnName in self.columnWidths) {
                attrs["style"] = "width:" + self.columnWidths[columnName];
            }

            if(columnName == "actions") {
                attrs["class"] = "actions-column-header";
            } else {
                sortable = self.columnTypes[columnName][1];

                if(sortable) {
                    attrs["class"] = "sortable-" + attrs["class"];
                    /*
                    * Bind the current value of columnName instead of just closing
                    * over it, since we're mutating the local variable in a loop.
                    */
                    attrs["onclick"] = (function(whichColumn) {
                            return function() {
                                /* XXX real-time feedback, ugh */
                                self.resort(whichColumn);
                            }
                        })(columnName);
                }
            }

            var headerNode = MochiKit.DOM.TD(attrs, displayName);
            headerNodes.push(headerNode);

        }
        return headerNodes;
    },

    /**
     * Update the view to reflect a new sort state.
     *
     * @param currentSortColumn: The name of the column by which the scrolling
     * widget's rows are now ordered, or null if there isn't a current sort
     * column
     *
     * @param isAscendingNow: A flag indicating whether the sort is currently
     * ascending.
     *
     */
    function _setSortHeader(self, currentSortColumn, isAscendingNow) {
        self.currentSort = currentSortColumn;
        self.ascending = isAscendingNow;

        if(currentSortColumn == null) {
            return;
        }

        /*
         * Remove the sort direction arrow from whichever header has it.
         */
        for (var j = 0; j < self._headerNodes.length; j++) {
            while(1 < self._headerNodes[j].childNodes.length) {
                self._headerNodes[j].removeChild(self._headerNodes[j].lastChild);
            }
        }

        /*
         * Put the appropriate sort direction arrow on whichever header
         * corresponds to the new current sort column.
         */
        var c;
        if(isAscendingNow) {
            c = '\u2191'; // up arrow
        } else {
            c = '\u2193'; // down arrow
        }
        var sortOffset = self._columnOffsets[currentSortColumn];
        var sortHeader = self._headerNodes[sortOffset];
        if (sortHeader != undefined) {
            var sortNode = MochiKit.DOM.SPAN({"class": "sort-arrow"}, c)
            sortHeader.appendChild(sortNode);
        }
    },

    /**
     * Called in response to only user-initiated scroll events.
     */
    function onScroll(self) {
        var scrollingDown = self.lastScrollPos < self._scrollViewport.scrollTop;
        self.lastScrollPos = self._scrollViewport.scrollTop;
        self.scrolled(undefined, scrollingDown);
    },

    /**
     * Respond to an event which may have caused to become visible rows for
     * which we do not data locally cached.  Retrieve some data, maybe, if
     * necessary.
     *
     * @type proposedTimeout: integer
     * @param proposedTimeout: The number of milliseconds to wait before
     * requesting data.  Defaults to 250ms.
     *
     * @type scrollingDown: boolean
     * @param scrollingDown: True if the viewport was scrolled down, false
     * otherwise.  Defaults to true.
     */
    function scrolled(self, /* optional */ proposedTimeout, scrollingDown) {
        var result = Divmod.Defer.Deferred();
        self._scrollDeferreds.push(result);

        if (proposedTimeout === undefined) {
            proposedTimeout = 250;
        }
        if(scrollingDown === undefined) {
            scrollingDown = true;
        }
        if (self._requestWaiting) {
            self._moreAfterRequest = true;
            return result;
        }
        if (self._rowTimeout !== null) {
            clearTimeout(self._rowTimeout);
        }

        self._rowTimeout = setTimeout(
            function () {
                self._rowTimeout = null;
                self._requestWaiting = true;
                self._getSomeRows(scrollingDown).addBoth(
                    function (rows) {
                        self._requestWaiting = false;
                        if (self._moreAfterRequest) {
                            self._moreAfterRequest = false;
                            self.scrolled();
                        } else {
                            var scrollDeferreds = self._scrollDeferreds;
                            self._scrollDeferreds = [];
                            for (var i = 0; i < scrollDeferreds.length; ++i) {
                                scrollDeferreds[i].callback(null);
                            }
                        }
                        self.cbRowsFetched(rows.length);
                    });
            },
            proposedTimeout);
        return result;
    },

    /**
     * Callback for some event.  Don't implement this.
     */
    function cbRowsFetched(self) {
    }
    );

/**
 * ScrollingWidget subclass which adjusts its height each time the viewport is
 * refilled, setting it to the same height as the total height of all
 * available rows, up until C{self.maxRows}.  Example where maxRows is 3 and
 * row height is 10px:
 *
 * if there is 1 row in the model:
 *
 * |HEADERS HEADERS HEADERS|
 * -------------------------
 * |THE ONLY ROW           | <- 10px, no scrollbar
 *
 * 2 rows in the model:
 *
 * |HEADERS HEADERS HEADERS|
 * -------------------------
 * |THE FIRST ROW          | \__ 10px + 10px = 20px, no scrollbar
 * |THE SECOND ROW         | /
 *
 * 3 or more rows in the model (>= maxRows):
 *
 * |HEADERS HEADERS HEADERS|
 * -------------------------
 * | THE FIRST ROW       | | \
 * | THE SECOND ROW      | |  >- 10px + 10px + 10px = 30px, scrollbar
 * | THE THIRD ROW       | | /
 *          |
 *         \|/
 *  rest of the rows obscured
 */

Mantissa.ScrollTable.FlexHeightScrollingWidget = Mantissa.ScrollTable.ScrollingWidget.subclass('Mantissa.ScrollingWidget.FlexHeightScrollingWidget');
Mantissa.ScrollTable.FlexHeightScrollingWidget.methods(
    /**
     * Override default implementation so we can store C{maxRows} and set the
     * initial height once initialization is complete
     */
    function __init__(self, node, maxRows/*=undefined*/) {
        Mantissa.ScrollTable.FlexHeightScrollingWidget.upcall(self, "__init__", node);
        self.maxRows = maxRows;
        self.initializationDeferred.addCallback(
            function(passThrough) {
                self._setScrollViewportHeight();
                return passThrough;
            });
    },

    /**
     * Helper method which sets the height of the scrolltable so that it's
     * tall enough to accomodate (without a scrollbar) any number of rows <=
     * C{self.maxRows}
     */
    function _setScrollViewportHeight(self) {
        var rowCount = self.model.totalRowCount();
        if(self.maxRows) {
            rowCount = Math.min(rowCount, self.maxRows);
        }
        self._scrollViewport.style.height = (rowCount * self._rowHeight) + "px";
    },

    /**
     * Override default implementation to never request less than
     * C{self.maxRows} if we're starting from the zeroth row (e.g. after the
     * scrolltable has been emptied or when we make the initial fetch)
     */
    function _calculateDesiredRowRange(self, scrollingDown) {
        var res = Mantissa.ScrollTable.FlexHeightScrollingWidget.upcall(
                    self, "_calculateDesiredRowRange", scrollingDown);
        if(res && res[0] == 0 && res[1] < self.maxRows-1) {
            res[1] = self.maxRows-1;
        }
        return res;
    },

    /**
     * Override default implementation so that we can adjust the height of the
     * scrolltable after the scrolltable has been refilled
     */
    function refill(self) {
        var D = Mantissa.ScrollTable.FlexHeightScrollingWidget.upcall(self, "refill");
        return D.addCallback(
            function(passThrough) {
                self._setScrollViewportHeight();
                return passThrough;
            });
    })
