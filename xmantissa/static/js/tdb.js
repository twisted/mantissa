function TabularDataBrowserController() {}

TabularDataBrowserController.prototype = {
    prevPage : function() {
        server.handle('prevPage');
        return false;
    },

    nextPage : function() {
        server.handle('nextPage');
        return false;
    },

    firstPage : function() {
        server.handle('firstPage');
        return false;
    },

    lastPage : function() {
        server.handle('lastPage');
        return false;
    }
}

/*
 Right now, we'll use a global, but in the near future we should associate a
 TDBController object with each TDB on the page; this means somehow
 associating it with the containing node.
 */

var gTDBController = new TabularDataBrowserController();

function getTDBController(element) {
    return gTDBController;
}

function alternateBgColors(elements, classes) {
    const ELEMENT_NODE = 1;
    var elementNodes = 0;

    for(var i = 0; i < elements.length; i++)
        /* we want to ignore whitespace */
        if(elements[i].nodeType == ELEMENT_NODE) {
            elements[i].className = classes[elementNodes % classes.length];
            elementNodes += 1;
        }
}

function setPageState(hasPrevPage, hasNextPage) {
    function enable(things) {
        for(var i = 0; i < things.length; i++) {
            var thing = things[i];
            document.getElementById(thing).style.display = "inline";
            document.getElementById(thing + "-disabled").style.display = "none";
        }
    }

    function disable(things) {
        for(var i = 0; i < things.length; i++) {
            var thing = things[i];
            document.getElementById(thing + "-disabled").style.display = "inline";
            document.getElementById(thing).style.display = "none";
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

    var tdb = document.getElementById("tdb").firstChild;
    alternateBgColors(tdb.getElementsByTagName("tbody")[0].childNodes,
                      ["tdb-row", "tdb-row-alt"]);
}

function actionResult(message) {
    var resultContainer = document.getElementById('tdb-action-result');

    if(resultContainer.childNodes.length)
        resultContainer.removeChild(resultContainer.firstChild);

    var span = document.createElement("span");
    span.appendChild(document.createTextNode(message));
    resultContainer.appendChild(span);

    new Fadomatic(span, 2).fadeOut();
}
