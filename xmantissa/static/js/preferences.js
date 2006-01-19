function firstElement(parent) {
    var ELEMENT_NODE = 1;
    for(var i = 0; i < parent.childNodes.length; i++) {
        var child = parent.childNodes[i];
        if(child.nodeType == ELEMENT_NODE)
            return child;
    }
    return null;
}

function firstElementWithTag(parent, tagName) {
    var elems = parent.getElementsByTagName(tagName);
    if(elems.length)
        return elems[0];
    return null;
}

function firstWithClass(parent, tagName, className) {
    var elems = parent.getElementsByTagName(tagName);
    for(var i = 0; i < elems.length; i++) {
        var elem = elems[i];
        if(elem.className == className)
            return elem;
    }
    return null;
}

function setDisplay(elem, value) {
    elem.style.display = value;
}

function getContainers(row) {
    control_cell = firstWithClass(row, "td", "control-cell");
    var container_parent = firstElementWithTag(control_cell, "span");
    var control_container = firstWithClass(container_parent, "span", "control-container");
    var value_container = firstWithClass(container_parent, "span", "value-container");
    return [value_container, control_container];
}

function getText(e) {
    var content = e.firstChild.nodeValue.replace(/^\s+/, "");
    return content.replace(/\s+$/, "");
}

function edit(elem) {
    var containers = getContainers(elem.parentNode.parentNode);
    selectOptionWithValue(firstElement(containers[1]), getText(containers[0]));

    setDisplay(containers[0], "none");
    setDisplay(containers[1], "inline");
    setDisplay(elem, "none");
    setDisplay(firstWithClass(elem.parentNode, "a", "save"), "inline");
    return false;
}

function getElementValue(elem) {
    if(elem.tagName == "INPUT" && elem.type == "text")
        return elem.value;
    if(elem.tagName == "SELECT")
        return selectedValue(elem);
}

function selectedValue(select) {
    var options = select.getElementsByTagName("option");
    for(var i = 0; i < options.length; i++)
        if(i == select.selectedIndex)
            return options[i].value;
    return null;
}

function save(elem) {
    var control_container = getContainers(elem.parentNode.parentNode)[1];
    server.handle("savePref", elem.parentNode.parentNode.id, 
                  getElementValue(firstElement(control_container)));
    return false;
}

function selectOptionWithValue( elem, value ) {
    for( var i = 0; i < elem.childNodes.length; i++ )
        if( elem.childNodes[i].value == value ) {
            elem.selectedIndex = i;
            break;
        }
}

function updatedPreference() {
    document.location.reload();
}
