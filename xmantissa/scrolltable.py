# -*- test-case-name: xmantissa.test.test_scrolltable -*-
from epsilon.extime import Time
from nevow.athena import LiveFragment
from xmantissa.ixmantissa import IWebTranslator

class ScrollingFragment(LiveFragment):
    jsClass = u'Mantissa.ScrollTable.ScrollingWidget'

    title = ''
    live = 'athena'
    fragmentName = 'scroller'

    iface = allowedMethods = dict(requestRowRange=True,
                                  requestCurrentSize=True,
                                  resort=True,
                                  getTableMetadata=True)

    def __init__(self, store, itemType, baseConstraint, columns, defaultSortColumn=None, *a, **kw):
        LiveFragment.__init__(self, *a, **kw)
        self.store = store
        self.wt = IWebTranslator(self.store, None)
        self.itemType = itemType
        self.baseConstraint = baseConstraint
        self.columns = columns
        if defaultSortColumn is None:
            defaultSortColumn = getattr(itemType, columns[0])
        self.currentSortColumn = defaultSortColumn
        self.isAscending = True
        self.currentRowSet = None
        self.currentRowRange = None

    def requestCurrentSize(self):
        return self.store.query(self.itemType, self.baseConstraint).count()

    def getTableMetadata(self):
        coltypes = dict((unicode(colname, 'ascii'),
                         unicode(attr.__class__.__name__, 'ascii')) for (colname, attr)
                            in self.itemType.getSchema() if colname in self.columns)

        return [self.columns, coltypes, self.requestCurrentSize(),
                unicode(self.currentSortColumn.attrname,
                        'ascii'), self.isAscending]

    def resort(self, columnName):
        """
        Re-sort the table.

        @param columnName: the name of the column to sort by.  This is a string
        because it is passed from the browser.
        """
        # XXX maybe figure out what columns are sortable...?
        csc = self.currentSortColumn
        newSortColumn = getattr(self.itemType, columnName)
        if csc is newSortColumn:
            self.isAscending = not self.isAscending
        else:
            self.currentSortColumn = newSortColumn
            self.isAscending = True
        return self.isAscending

    def squishValue(self, value):
        if isinstance(value, Time):
            return value.asPOSIXTimestamp()
        return value

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
            row = dict((colname, self.squishValue(getattr(item, colname))) for colname in self.columns)
            if self.wt is not None:
                row[u'__id__'] = unicode(self.wt.toWebID(item), 'ascii')
            rows.append(row)
        return rows

    def requestRowRange(self, rangeBegin, rangeEnd):
        return self.constructRows(self.performQuery(rangeBegin, rangeEnd))
