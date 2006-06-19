var MantissaShell = {};

/**
 * Return the first immediate child of C{node} which has the class name "subtabs"
 */
MantissaShell.getSubtabs = function(node) {
    for(var i = 0; i < node.childNodes.length; i++) {
        if(node.childNodes[i].className == "subtabs") {
            return node.childNodes[i];
        }
    }
}

/**
 * Called when a subtab is hovered over.
 * This action indicates that a user is still interacting with the menu bar,
 * and so it cancels the popdown timeout that gets started when the mouse
 * leaves the top level menu
 */
MantissaShell.subtabHover = function(node) {
    if(MantissaShell._TIMEOUT) {
        clearTimeout(MantissaShell._TIMEOUT);
        MantissaShell._TIMEOUT = null;
    }
}

/**
 * Called when the divmod "start menu" button is hovered over.
 * It cleans up the top level menu before it gets displayed
 */
MantissaShell.menuButtonHover = function() {
    var subtabs, child;
    var menu = document.getElementById("divmod-menu");
    for(var i = 0; i < menu.childNodes.length; i++) {
        child = menu.childNodes[i];
        if(child.tagName) {
            subtabs = MantissaShell.getSubtabs(child);
            if(subtabs && subtabs.style.display != "none") {
                subtabs.style.display = "none";
            }
        }
    }
}

/**
 * Pair of functions that toggle the menu container's class to work around IE's
 * lack of :hover support for anything other than <a> elements.
 */
MantissaShell.menuClick = function(node) {
    var menu = document.getElementById("divmod-menu"),
        nodeClickHandler = node.onclick,
        bodyMouseUpHandler = document.body.onmouseup;

    menu.style.display = "";
    node.onclick = null;
    document.body.onmouseup = function(event) {
        menu.style.display = "none";
        document.body.onmouseup = bodyMouseUpHandler;
        setTimeout(function() {
            node.onclick = nodeClickHandler;
        }, 1);
        return false;
    }
};

/**
 * Called when a top level tab is hovered over.
 * This makes the tab's submenu visibile, if there is one.
 *
 * We use JS for this because we want the submenu to appear directly to
 * the right of the parent item when hovered over, but we don't want to
 * have to fix the width of the parent menu
 */
MantissaShell.tabHover = function(node) {
    var subtabs = MantissaShell.getSubtabs(node.parentNode);

    if(!subtabs) {
        return;
    }

    if(!subtabs.style.left) {
        subtabs.style.left = node.clientWidth + "px";
        subtabs.style.marginTop = -node.clientHeight + "px";
    }
    subtabs.style.display = "";
}

/**
 * Called when the mouse leaves a top level tab.
 * This starts a 100usec timer, which, when it expires, will make the
 * start menu disappear.
 * See also the docstring for C{subtabHover}
 */
MantissaShell.tabUnhover = function(node) {
    var subtabs = MantissaShell.getSubtabs(node.parentNode);
    if(subtabs) {
        MantissaShell._TIMEOUT = setTimeout(function() {
            subtabs.style.display = "none";
            MantissaShell._TIMEOUT = null;
        }, 100);
    }
}


/**
 * Called when the user clicks the small search button.
 * This toggles the visibility of the search form.
 */
MantissaShell.searchButtonClicked = function(node) {
    node.blur();

    var imgstate, color;
    var sfcont = document.getElementById("search-form-container");

    if(!sfcont.style.right) {
        sfcont.style.right = sfcont.clientWidth + "px";
    }

    if(sfcont.style.display == "none") {
        sfcont.style.display = "";
        imgstate = "selected";
        color = "#999999";
    } else {
        sfcont.style.display = "none";
        imgstate = "unselected";
        color = "";
    }

    node.firstChild.src = "/Mantissa/images/search-button-" + imgstate + ".png";
    node.parentNode.style.backgroundColor = color;
}
