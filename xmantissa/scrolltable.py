# -*- test-case-name: xmantissa.test.test_scrolltable -*-

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
        return AttributeColumn.extractValue(self, model, item).asPOSIXTimestamp()

class UnsortableColumn(AttributeColumn):
    def sortAttribute(self):
        return None

class ScrollingFragment(LiveElement):
    jsClass = u'Mantissa.ScrollTable.ScrollingWidget'

    title = ''
    live = 'athena'
    fragmentName = 'scroller'


    def __init__(self, store, itemType, baseConstraint, columns,
                 defaultSortColumn=None, defaultSortAscending=True,
                 actions=(), *a, **kw):

        LiveElement.__init__(self, *a, **kw)
        self.store = store
        self.wt = IWebTranslator(self.store, None)
        self.itemType = itemType
        self.baseConstraint = baseConstraint

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
        self.currentRowSet = None
        self.currentRowRange = None

        self.actions = actions

    def requestCurrentSize(self):
        return self.store.query(self.itemType, self.baseConstraint).count()
    expose(requestCurrentSize)

    def getTableMetadata(self):
        coltypes = {}
        for (colname, column) in self.columns.iteritems():
            sortable = column.sortAttribute() is not None
            coltype = column.getType()
            if coltype is not None:
                coltype = unicode(coltype, 'ascii')
            coltypes[colname] = (coltype, sortable)

        if 0 < len(self.actions):
            coltypes[u'actions'] = (u'actions', False)
            self.columnNames.append(u'actions')

        return [self.columnNames, coltypes, self.requestCurrentSize(),
                unicode(self.currentSortColumn.attrname,
                        'ascii'), self.isAscending]
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

    def performQuery(self, rangeBegin, rangeEnd):
        self.currentRowRange = (rangeBegin, rangeEnd)

        if self.isAscending:
            sort = self.currentSortColumn.ascending
        else:
            sort = self.currentSortColumn.descending
        self.currentRowSet = []
        for item in self.store.query(self.itemType,
                                     self.baseConstraint,
                                     offset=rangeBegin,
                                     limit=rangeEnd-rangeBegin,
                                     sort=sort):
            self.currentRowSet.append(item)
        return self.currentRowSet

    def constructRows(self, items):
        rows = []
        for item in items:
            row = dict((colname, col.extractValue(self, item))
                            for (colname, col) in self.columns.iteritems())
            if self.wt is not None:
                row[u'__id__'] = unicode(self.wt.toWebID(item), 'ascii')
            rows.append(row)

        if 0 < len(self.actions):
            for (item, row) in zip(items, rows):
                row[u'actions'] = []
                for action in self.actions:
                    if action.actionable(item):
                        if action.iconURL is not None:
                            iconURL = unicode(action.iconURL, 'ascii')
                        else:
                            iconURL = None

                        row['actions'].append(
                                {u'actionID': unicode(action.actionID, 'ascii'),
                                 u'iconURL': iconURL})

        return rows

    def requestRowRange(self, rangeBegin, rangeEnd):
        return self.constructRows(self.performQuery(rangeBegin, rangeEnd))
    expose(requestRowRange)

    def performAction(self, actionID, targetID):
        item = self.wt.fromWebID(targetID)
        for action in self.actions:
            if action.actionID == actionID:
                return action.performOn(item)
    expose(performAction)
