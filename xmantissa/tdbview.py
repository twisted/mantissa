from zope.interface import implements

from nevow import tags, livepage
from nevow.rend import Fragment

from formless.annotate import nameToLabel

from xmantissa.publicresource import getLoader
from xmantissa.fragmentutils import PatternDictionary
from xmantissa import ixmantissa

# review the need to pass around instances of columns,
# rather than classes, same for actions also

class ColumnViewBase:
    def __init__(self, attributeID, displayName=None,
                 width=None, typeHint=None):
        """@param typeHint: text|datetime|action or None"""

        self.attributeID = attributeID
        if displayName is None:
            displayName = nameToLabel(attributeID)
        self.displayName = displayName
        self.width = width
        self.typeHint = typeHint

    def stanFromValue(self, idx, item, value):
        # called with the result of extractValue
        return str(value)

    def getWidth(self):
        if self.width is None:
            return ''
        else:
            return self.width

class DateColumnView(ColumnViewBase):
    def __init__(self, attributeID, displayName=None, width=None,
                 typeHint='datetime'):

        ColumnViewBase.__init__(self, attributeID, displayName,
                                width, typeHint)

    def stanFromValue(self, idx, item, value):
        # XXX timezones
        return value.asHumanly()

class ActionsColumnView(ColumnViewBase):
    def __init__(self, actions, width=None, typeHint='actions'):
        ColumnViewBase.__init__(self, 'Actions', width=width, typeHint=typeHint)
        self.actions = actions

    def stanFromValue(self, idx, item, value):
        # Value will generally be 'None' in this case...
        tag = tags.div()
        for action in self.actions:
            actionable = action.actionable(item)
            if actionable:
                iconURL = action.iconURL
            else:
                iconURL = action.disabledIconURL

            stan = tags.img(src=iconURL, **{'class' : 'tdb-action'})

            if actionable:
                handler = 'server.handle("performAction", %r, %r); return false'
                handler %= (action.actionID, idx)
                stan = tags.a(href='#', onclick=handler)[stan]

            tag[stan]

        # at some point give the javascript the description to show
        # or something
        return tag

class Action:
    def __init__(self, actionID, iconURL, description, disabledIconURL=None):
        self.actionID = actionID
        self.iconURL = iconURL
        self.disabledIconURL = disabledIconURL
        self.description = description

    def performOn(self, item):
        """perform this action on the given item, returning
           None or a completion message that might be useful
           to the originator of the action"""
        raise NotImplementedError()

    def actionable(self, item):
        """return a boolean indicating whether it makes sense to
           perform this action on the given item"""
        raise NotImplementedError()

class TabularDataView(Fragment):
    implements(ixmantissa.INavigableFragment)

    docFactory = getLoader('tdb')
    live = True
    title = ''
    fragmentName = ''

    def __init__(self, model, columnViews, actions=()):
        Fragment.__init__(self, model)

        self.columnViews = list(columnViews)
        if actions:
            self.columnViews.append(ActionsColumnView(actions))
        self.actions = {}
        for action in actions:
            self.actions[action.actionID] = action
        self.patterns = PatternDictionary(self.docFactory)

    def constructTable(self):
        modelData = self.original.currentPage()
        if len(modelData) == 0:
            return self.patterns['no-rows']()

        tablePattern = self.patterns['table']
        rowPattern = self.patterns['row']
        cellPattern = self.patterns['cell']

        headers = []
        for cview in self.columnViews:
            model = self.original
            column = model.columns.get(cview.attributeID)

            if column is None:
                sortable = False
            else:
                sortable = column.sortAttribute() is not None

            if cview.attributeID == model.currentSortColumn.attributeID:
                headerPatternName = ['sorted-column-header-descending',
                                     'sorted-column-header-ascending'][model.isAscending]
            else:
                headerPatternName = ['column-header',
                                     'sortable-column-header'][sortable]

            header = self.patterns[headerPatternName].fillSlots(
                        'name', cview.displayName).fillSlots(
                                'width', cview.getWidth())

            if sortable:
                header = header.fillSlots('onclick',
                            'server.handle("clickSort", "%s")'%
                            (cview.attributeID,))

            headers.append(header)

        tablePattern = tablePattern.fillSlots('column-headers', headers)

        rows = []
        for idx, row in enumerate(modelData):
            cells = []
            for cview in self.columnViews:
                value = row.get(cview.attributeID)
                cellContents = cview.stanFromValue(
                        idx, row['__item__'], value)
                cellStan = cellPattern.fillSlots(
                                'value', cellContents) .fillSlots(
                                        'typeHint', cview.typeHint)
                cells.append(cellStan)
            rows.append(rowPattern.fillSlots('cells', cells))

        return tablePattern.fillSlots('rows', rows)

    def render_table(self, ctx, data):
        return ctx.tag[self.constructTable()]

    def render_actions(self, ctx, data):
        return '(Actions not yet implemented)'

    def goingLive(self, ctx, client):
        client.call('setPageState', self.original.hasPrevPage(),
                    self.original.hasNextPage())

    def replaceTable(self):
        yield (livepage.set('tdb', self.constructTable()), livepage.eol)
        yield livepage.js.setPageState(self.original.hasPrevPage(),
                                       self.original.hasNextPage())

    def handle_nextPage(self, ctx):
        self.original.nextPage()
        return self.replaceTable()

    def handle_prevPage(self, ctx):
        self.original.prevPage()
        return self.replaceTable()

    def handle_firstPage(self, ctx):
        self.original.firstPage()
        return self.replaceTable()

    def handle_lastPage(self, ctx):
        self.original.lastPage()
        return self.replaceTable()

    def handle_performAction(self, ctx, actionID, targetID):
        modelData = list(self.original.currentPage())
        target = modelData[int(targetID)]['__item__']
        action = self.actions[actionID]
        result = action.performOn(target)
        if result is None:
            result = ''

        yield (livepage.js.actionResult(result), livepage.eol)
        yield self.replaceTable()

    def handle_clickSort(self, ctx, attributeID):
        if attributeID == self.original.currentSortColumn.attributeID:
            self.original.resort(attributeID, not self.original.isAscending)
        else:
            self.original.resort(attributeID)
        yield self.replaceTable()

    def head(self):
        yield tags.script(type='text/javascript',
                          src='/static/mantissa/js/tdb.js')
        yield tags.script(type='text/javascript',
                          src='/static/mantissa/js/fadomatic.js')
