
// import Divmod.Runtime

// import Nevow.Athena
// import Fadomatic

if (typeof(Mantissa) == 'undefined') {
    Mantissa = {};
}

if (typeof(Mantissa.TDB) == 'undefined') {
    Mantissa.TDB = {};
}

Mantissa.TDB.Controller = Nevow.Athena.Widget.subclass();

Mantissa.TDB.Controller.prototype.loaded = function () {
    this.tdbElements = {};
    return this._differentPage('replaceTable');
};

Mantissa.TDB.Controller.prototype._toggleThrobberVisibility = function() {
    if(!this.node.style.opacity || this.node.style.opacity == '1') {
        this.node.style.opacity = '.3';
    } else {
        this.node.style.opacity = '1';
    }

    var t = this._getHandyNode('throbber');

    if(t.style.visibility == 'hidden') {
        t.style.visibility = 'visible';
    } else {
        t.style.visibility = 'hidden';
    }
}

Mantissa.TDB.Controller.prototype._setTableContent = function (tableContent) {
    Divmod.Runtime.theRuntime.setNodeContent(this._getHandyNode("tdb-table"), tableContent);
};

Mantissa.TDB.Controller.prototype._getHandyNode = function(classValue) {
    if(!(classValue in this.tdbElements)) {
        this.tdbElements[classValue] = this.nodeByAttribute('class', classValue);
    }
    return this.tdbElements[classValue];
};

Mantissa.TDB.Controller.prototype._differentPage = function(/*...*/) {
    this._toggleThrobberVisibility();

    var outThis = this;
    var d = this.callRemote.apply(this, arguments);
    d.addCallback(function(result) {
                      var tdbTable = result[0];
                      var tdbState = result[1];
                      outThis._setTableContent(tdbTable);
                      outThis._setPageState.apply(outThis, tdbState);
                  });
    d.addBoth(function(ign) { outThis._toggleThrobberVisibility() });
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

    var prevs = ["prev-page", "first-page"];
    var nexts = ["next-page", "last-page"];

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
    this._toggleThrobberVisibility();

    var outThis = this;
    var d = this.callRemote('performAction', actionID, targetID);
    d.addCallback(function(result) {
                      var tdbTable = result[1][0];
                      var tdbState = result[1][1];
                      outThis._setTableContent(tdbTable);
                      outThis._setPageState.apply(outThis, tdbState);
                      outThis._actionResult(result[0]);
                  });
    d.addBoth(function(ign) { outThis._toggleThrobberVisibility() });
    return false;
};

Mantissa.TDB.Controller.prototype.clickSort = function(attributeID) {
    return this._differentPage('clickSort', attributeID);
};

Mantissa.TDB.Controller.prototype._actionResult = function(message) {
    var resultContainer = this._getHandyNode('tdb-action-result');

    if(resultContainer.childNodes.length)
        resultContainer.removeChild(resultContainer.firstChild);

    var span = document.createElement("span");
    span.appendChild(document.createTextNode(message));
    resultContainer.appendChild(span);

    new Fadomatic(span, 2).fadeOut();
};
