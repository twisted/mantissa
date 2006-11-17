# -*- test-case-name: xmantissa.test.test_scrolltable -*-

from zope.interface import implements

from nevow.athena import LiveElement, expose

from axiom.attributes import timestamp

from xmantissa.ixmantissa import IWebTranslator, IColumn
from xmantissa.tdb import AttributeColumn, Unsortable

TYPE_FRAGMENT = 'fragment'

# these objects aren't for view junk - they allow the model
# to inform the javascript controller about which columns are
# sortable, as well as supporting non-attribute columns

class TimestampAttributeColumn(AttributeColumn):
    # timestamps are a special case; we need to get the posix timestamp
    # so we can send the attribute value to javascript.  we don't register
    # an adapter for attributes.timestamp because the TDB model uses
    # IColumn.extractValue() to determine the value of the query pivot,
    # and so it needs an extime.Time instance, not a float

    def extractValue(self, model, item):
        val = AttributeColumn.extractValue(self, model, item)
        if val is None:
            raise AttributeError("%r was None" % (self.attribute,))
        return val.asPOSIXTimestamp()

    def getType(self):
        return 'timestamp'

class UnsortableColumn(AttributeColumn):
    def sortAttribute(self):
        return None

class UnsortableColumnWrapper:
    """
    Wraps an L{AttributeColumn} and makes it unsortable

    @ivar col: L{AttributeColumn}
    """
    implements(IColumn)

    def __init__(self, col):
        self.col = col
        self.attribute = col.attribute
        self.attributeID = col.attributeID

    def extractValue(self, model, item):
        return self.col.extractValue(model, item)

    def sortAttribute(self):
        return None

    def getType(self):
        return self.col.getType()

class Scrollable(object):
    """
    Mixin for "model" implementations of an in-browser scrollable list of
    elements.

    @ivar webTranslator: A L{IWebTranslator} provider for resolving and
    creating web links for items.

    @ivar columns: A mapping of attribute identifiers to L{IColumn}
    providers.

    @ivar columnNames: A list of attribute identifiers.

    @ivar isAscending: A boolean indicating the current order of the sort.

    @ivar currentSortColumn: A L{axiom.attributes.SQLAttribute} representing
    the current sort key.
    """
    def __init__(self, webTranslator, columns, defaultSortColumn,
                 defaultSortAscending):
        self.webTranslator = webTranslator
        self.columns = {}
        self.columnNames = []
        for col in columns:
            # see comment in TimestampAttributeColumn
            if isinstance(col, timestamp):
                col = TimestampAttributeColumn(col)
            else:
                col = IColumn(col)

            if defaultSortColumn is None:
                defaultSortColumn = col.sortAttribute()

            attributeID = unicode(col.attributeID, 'ascii')
            self.columns[attributeID] = col
            self.columnNames.append(attributeID)

        self.currentSortColumn = defaultSortColumn
        self.isAscending = defaultSortAscending


    # Override these two in a subclass
    def performCount(self):
        """
        Override this in a subclass.

        @rtype: C{int}
        @return: The total number of elements in this scrollable.
        """
        raise NotImplementedError()


    def performQuery(self, rangeBegin, rangeEnd):
        """
        Override this in a subclass.

        @rtype: C{list}
        @return: Elements from C{rangeBegin} to C{rangeEnd} of the
        underlying data set, as ordered by the value of
        C{currentSortColumn} sort column in the order indicated by
        C{isAscending}.
        """
        raise NotImplementedError()


    # The rest takes care of responding to requests from the client.
    def getTableMetadata(self):
        """
        Retrieve a description of the various properties of this scrolltable.

        @return: A sequence containing 5 elements.  They are, in order, a
        list of the names of the columns present, a mapping of column names
        to two-tuples of their type and a boolean indicating their
        sortability, the total number of rows in the scrolltable, the name
        of the default sort column, and a boolean indicating whether or not
        the current sort order is ascending.
        """
        coltypes = {}
        for (colname, column) in self.columns.iteritems():
            sortable = column.sortAttribute() is not None
            coltype = column.getType()
            if coltype is not None:
                coltype = unicode(coltype, 'ascii')
            coltypes[colname] = (coltype, sortable)

        if self.currentSortColumn:
            csc = unicode(self.currentSortColumn.attrname, 'ascii')
        else:
            csc = None

        return [self.columnNames, coltypes, self.requestCurrentSize(),
                csc, self.isAscending]
    expose(getTableMetadata)


    def resort(self, columnName):
        """
        Re-sort the table.

        @param columnName: the name of the column to sort by.  This is a string
        because it is passed from the browser.
        """
        csc = self.currentSortColumn
        newSortColumn = self.columns[columnName].sortAttribute()
        if newSortColumn is None:
            raise Unsortable('column %r has no sort attribute' % (columnName,))
        if csc is newSortColumn:
            self.isAscending = not self.isAscending
        else:
            self.currentSortColumn = newSortColumn
            self.isAscending = True
        return self.isAscending
    expose(resort)


    def linkToItem(self, item):
        """
        Return a URL that the row for C{item} should link to, by asking the
        L{xmantissa.ixmantissa.IWebTranslator} in C{self.store}

        @return: C{unicode} URL
        """
        return unicode(self.webTranslator.toWebID(item), 'ascii')


    def itemFromLink(self, link):
        """
        Inverse of L{linkToItem}.

        @rtype: L{axiom.item.Item}
        """
        return self.webTranslator.fromWebID(link)


    def requestRowRange(self, rangeBegin, rangeEnd):
        """
        Retrieve display data for the given range of rows.
        """
        return self.constructRows(self.performQuery(rangeBegin, rangeEnd))
    expose(requestRowRange)


    def requestCurrentSize(self):
        return self.performCount()
    expose(requestCurrentSize)


    def performAction(self, name, rowID):
        method = getattr(self, 'action_' + name)
        item = self.itemFromLink(rowID)
        return method(item)
    expose(performAction)


class ScrollableView(object):
    """
    Mixin for structuring model data in the way expected by
    Mantissa.ScrollTable.ScrollingWidget.
    """
    jsClass = u'Mantissa.ScrollTable.ScrollingWidget'
    fragmentName = 'scroller'

    def constructRows(self, items):
        rows = []
        for item in items:
            row = dict((colname, col.extractValue(self, item))
                            for (colname, col) in self.columns.iteritems())
            link = self.linkToItem(item)
            if link is not None:
                row[u'__id__'] = link
            rows.append(row)

        return rows



class ItemQueryScrollingFragment(Scrollable, ScrollableView, LiveElement):
    def __init__(self, store, itemType, baseConstraint, columns,
                 defaultSortColumn=None, defaultSortAscending=True,
                 *a, **kw):

        Scrollable.__init__(self, IWebTranslator(store, None), columns,
                            defaultSortColumn, defaultSortAscending)
        LiveElement.__init__(self, *a, **kw)
        self.store = store
        self.itemType = itemType
        self.baseConstraint = baseConstraint


    def performCount(self):
        return self.store.query(self.itemType, self.baseConstraint).count()


    def performQuery(self, rangeBegin, rangeEnd):
        if self.isAscending:
            sort = self.currentSortColumn.ascending
        else:
            sort = self.currentSortColumn.descending
        return list(self.store.query(self.itemType,
                                     self.baseConstraint,
                                     offset=rangeBegin,
                                     limit=rangeEnd - rangeBegin,
                              sort=sort))
ScrollingFragment = ItemQueryScrollingFragment



class SequenceScrollingFragment(Scrollable, ScrollableView, LiveElement):
    """
    Scrolltable implementation backed by any Python L{axiom.item.Item}
    sequence.
    """
    def __init__(self, store, elements, columns, defaultSortColumn=None,
                 defaultSortAscending=True, *a, **kw):
        Scrollable.__init__(self, IWebTranslator(store, None), columns,
                            defaultSortColumn, defaultSortAscending)

        LiveElement.__init__(self, *a, **kw)
        self.store = store
        self.elements = elements


    def performCount(self):
        return len(self.elements)


    def performQuery(self, rangeBegin, rangeEnd):
        step = 1
        if not self.isAscending:
            # The ranges are from the end, not the beginning.
            rangeBegin = max(0, len(self.elements) - rangeBegin - 1)

            # Python is so very very confusing:
            # s[1:0:-1] == []
            # s[1:None:-1] == [s[0]]
            # s[1:-1:-1] == some crazy thing you don't even want to know
            rangeEnd = max(-1, len(self.elements) - rangeEnd - 1)
            if rangeEnd == -1:
                rangeEnd = None
            step = -1
        return self.elements[rangeBegin:rangeEnd:step]



class StoreIDSequenceScrollingFragment(SequenceScrollingFragment):
    """
    Scrolltable implementation like L{SequenceScrollingFragment} but which is
    backed by a sequence of Item storeID values rather than Items themselves.
    """
    def performQuery(self, rangeBegin, rangeEnd):
        return map(
            self.store.getItemByID,
            super(
                StoreIDSequenceScrollingFragment,
                self).performQuery(rangeBegin, rangeEnd))
