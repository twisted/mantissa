from zope.interface import implements

from nevow import tags, athena, flat

from formless.annotate import nameToLabel

from xmantissa.fragmentutils import PatternDictionary, dictFillSlots
from xmantissa import ixmantissa

# review the need to pass around instances of columns,
# rather than classes, same for actions also

class ColumnViewBase(object):
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

    def onclick(self, idx, item, value):
        return None

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
                linkstan = action.toLinkStan(idx, item)
                if linkstan is None:
                    handler = 'Mantissa.TDB.Controller.get(this).performAction(%r, %r); return false'
                    handler %= (action.actionID, idx)
                    stan = tags.a(href='#', onclick=handler)[stan]
                else:
                    stan = linkstan

            tag[stan]

        # at some point give the javascript the description to show
        # or something
        return tag

class Action(object):
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

    def toLinkStan(self, idx, item):
        return None

class ToggleAction(Action):

    def actionable(self, item):
        return True

    def isOn(self, idx, item):
        raise NotImplementedError()

    def toLinkStan(self, idx, item):
        handler = 'Mantissa.TDB.Controller.get(this).performAction(%r, %r); return false'
        handler %= (self.actionID, idx)
        iconURL = (self.disabledIconURL, self.iconURL)[self.isOn(idx, item)]
        img = tags.img(src=iconURL, **{'class': 'tdb-action'})
        return tags.a(href='#', onclick=handler)[img]

class TabularDataView(athena.LiveFragment):
    implements(ixmantissa.INavigableFragment)

    jsClass = u'Mantissa.TDB.Controller'

    fragmentName = 'tdb'
    live = 'athena'
    title = ''
    patterns = None

    def __init__(self, model, columnViews, actions=(), width=''):
        super(TabularDataView, self).__init__(model)
        self.columnViews = list(columnViews)
        if actions:
            self.columnViews.append(ActionsColumnView(actions))
        self.actions = {}
        for action in actions:
            self.actions[action.actionID] = action
        self.width = width

    def constructTable(self):
        if self.patterns is None:
            self.patterns = PatternDictionary(self.docFactory)

        modelData = self.original.currentPage()
        if len(modelData) == 0:
            return self.patterns['no-rows']()

        tablePattern = self.patterns['table']


        headers = self.constructColumnHeaders()
        rows = self.constructRows(modelData)

        tablePattern = tablePattern.fillSlots('column-headers', list(headers))
        
        return tablePattern.fillSlots(
                'rows', list(rows)).fillSlots('width', self.width)

    def constructColumnHeaders(self):
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
                            'Mantissa.TDB.Controller.get(this).clickSort("%s")'%
                            (cview.attributeID,))

            yield header

    def constructRows(self, modelData):
        rowPattern = self.patterns['row']
        cellPattern = self.patterns['cell']

        for idx, row in enumerate(modelData):
            cells = []
            for cview in self.columnViews:
                value = row.get(cview.attributeID)
                cellContents = cview.stanFromValue(
                        idx, row['__item__'], value)
                handler = cview.onclick(idx, row['__item__'], value)
                cellStan = dictFillSlots(cellPattern,
                                         {'value': cellContents,
                                          'onclick': handler,
                                          'class': cview.typeHint})

                cells.append(cellStan)

            yield dictFillSlots(rowPattern,
                                {'cells': cells,
                                 'class': 'tdb-row-%s' % (idx,)})

    def render_table(self, ctx, data):
        return ctx.tag[self.constructTable()]

    def render_navigation(self, ctx, data):
        patterns = PatternDictionary(self.docFactory)
        return ctx.tag[patterns['navigation']()]

    def render_actions(self, ctx, data):
        return '(Actions not yet implemented)'

    iface = allowedMethods = {'getPageState': True,
                              'nextPage': True,
                              'prevPage': True,
                              'firstPage': True,
                              'lastPage': True,
                              'performAction': True,
                              'clickSort': True,
                              'replaceTable': True}
    def replaceTable(self):
        # XXX TODO: the flatten here is encoding/decoding like 4 times; this
        # could be a lot faster.
        return unicode(flat.flatten(self.constructTable()), 'utf-8'), self.getPageState()

    def getPageState(self):
        tdm = self.original
        return (tdm.hasPrevPage(), tdm.hasNextPage(),
                tdm.pageNumber, tdm.itemsPerPage, tdm.totalItems)

    def nextPage(self):
        self.original.nextPage()
        return self.replaceTable()

    def prevPage(self):
        self.original.prevPage()
        return self.replaceTable()

    def firstPage(self):
        self.original.firstPage()
        return self.replaceTable()

    def lastPage(self):
        self.original.lastPage()
        return self.replaceTable()

    def itemFromTargetID(self, targetID):
        modelData = list(self.original.currentPage())
        return modelData[targetID]['__item__']

    def performAction(self, actionID, targetID):
        target = self.itemFromTargetID(int(targetID))
        action = self.actions[actionID]
        result = action.performOn(target)
        return result, self.replaceTable()

    def clickSort(self, attributeID):
        if attributeID == self.original.currentSortColumn.attributeID:
            self.original.resort(attributeID, not self.original.isAscending)
        else:
            self.original.resort(attributeID)
        self.original.firstPage()
        return self.replaceTable()

    def head(self):
        return None
