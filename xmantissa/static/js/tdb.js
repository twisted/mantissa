
// import Nevow.Athena

if (typeof(Mantissa) == 'undefined') {
    Mantissa = {};
}

if (typeof(Mantissa.TDB) == 'undefined') {
    Mantissa.TDB = {};
}

Mantissa.TDB.Controller = Nevow.Athena.Widget.subclass();

Mantissa.TDB.Controller.prototype.loaded = function () {
    return this._differentPage('replaceTable');
};

Mantissa.TDB.Controller.prototype._setTableContent = function (tableContent) {
    /* alert("STC: "+tableContent); */
    this._getHandyNode("tdb-table").innerHTML = tableContent;
};

Mantissa.TDB.Controller.prototype._getHandyNode = function(classValue) {
    return Nevow.Athena.NodeByAttribute(this.node, 'class', classValue);
};

Mantissa.TDB.Controller.prototype._differentPage = function(/*...*/) {
    var outThis = this;
    var d = this.callRemote.apply(this, arguments);
    d.addCallback(function(result) {
                      var tdbTable = result[0];
                      var tdbState = result[1];
                      outThis._setTableContent(tdbTable);
                      outThis._setPageState.apply(outThis, tdbState);
                  });
    return false;
};

Mantissa.TDB.Controller.prototype._setPageState = function (hasPrevPage, hasNextPage, curPage, itemsPerPage, items) {
    var cp = this._getHandyNode("tdb-control-panel");
    var self = this;
    if(items == 0) {
        cp.style.display = "none";
    } else {
        cp.style.display = "table-cell";
    }
    function setValue(eid, value) {
        var e = self._getHandyNode(eid);
        if(e.childNodes.length == 0) {
            e.appendChild(document.createTextNode(value));
        } else {
            e.firstChild.nodeValue = value;
        }
    }

    var offset = (curPage - 1) * itemsPerPage + 1;
    var end = offset + itemsPerPage - 1;
    if(items < end) {
        end = items;
    }
    setValue("tdb-item-start", offset);
    setValue("tdb-item-end", end);
    setValue("tdb-total-items", items);

    function enable(things) {
        for(var i = 0; i < things.length; i++) {
            var thing = things[i];
            self._getHandyNode(thing).style.display = "inline";
            self._getHandyNode(thing + "-disabled").style.display = "none";
        }
    }

    function disable(things) {
        for(var i = 0; i < things.length; i++) {
            var thing = things[i];
            self._getHandyNode(thing + "-disabled").style.display = "inline";
            self._getHandyNode(thing).style.display = "none";
        }
    }

    const prevs = ["prev-page", "first-page"];
    const nexts = ["next-page", "last-page"];

    if (hasPrevPage) {
        enable(prevs);
    } else {
        disable(prevs);
    }
    if (hasNextPage) {
        enable(nexts);
    } else {
        disable(nexts);
    }

    this.alternateBgColors();
};

Mantissa.TDB.Controller.prototype.prevPage = function() {
    return this._differentPage('prevPage');
};

Mantissa.TDB.Controller.prototype.nextPage = function() {
    return this._differentPage('nextPage');
};

Mantissa.TDB.Controller.prototype.firstPage = function() {
    return this._differentPage('firstPage');
};

Mantissa.TDB.Controller.prototype.lastPage = function() {
    return this._differentPage('lastPage');
};

Mantissa.TDB.Controller.prototype.performAction = function(actionID, targetID) {
    return this._differentPage('performAction', actionID, targetID);
};

Mantissa.TDB.Controller.prototype.clickSort = function(attributeID) {
    return this._differentPage('clickSort', attributeID);
}

Mantissa.TDB.Controller.prototype.alternateBgColors = function() {
    const ELEMENT_NODE = 1;
    var elementNodes = 0;
    var elements = this._getHandyNode('tdbtbody').childNodes;
    var classes = ["tdb-row", "tdb-row-alt"];

    for(var i = 0; i < elements.length; i++)
        /* we want to ignore whitespace */
        if(elements[i].nodeType == ELEMENT_NODE) {
            elements[i].className = classes[elementNodes % classes.length];
            elementNodes += 1;
        }
}

function actionResult(message) {
    var resultContainer = this._getHandyNode('tdb-action-result');

    if(resultContainer.childNodes.length)
        resultContainer.removeChild(resultContainer.firstChild);

    var span = document.createElement("span");
    span.appendChild(document.createTextNode(message));
    resultContainer.appendChild(span);

    new Fadomatic(span, 2).fadeOut();
}
