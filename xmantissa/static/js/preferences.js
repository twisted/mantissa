if (typeof(Mantissa) == 'undefined') {
    Mantissa = {};
}

Mantissa.Preferences = Nevow.Athena.Widget.subclass("Mantissa.Preferences");

Mantissa.Preferences.methods(
    function firstElement(self, parent) {
        var ELEMENT_NODE = 1;
        for(var i = 0; i < parent.childNodes.length; i++) {
            var child = parent.childNodes[i];
            if(child.nodeType == ELEMENT_NODE)
                return child;
        }
        return null;
    },

    function getContainers(self, row) {
        return [Nevow.Athena.NodeByAttribute(row, "class", "value-container"),
                Nevow.Athena.NodeByAttribute(row, "class", "control-container")];
    },

    function getText(self, e) {
        var content = e.firstChild.nodeValue.replace(/^\s+/, "");
        return content.replace(/\s+$/, "");
    },

    function edit(self, elem) {
        var containers = self.getContainers(elem.parentNode.parentNode);
        self.selectOptionWithValue(self.firstElement(containers[1]),
                                   self.getText(containers[0]));

        MochiKit.DOM.hideElement(containers[0]);
        MochiKit.DOM.setDisplayForElement("inline", containers[1]);
        MochiKit.DOM.hideElement(elem);
        MochiKit.DOM.setDisplayForElement("inline",
                    Nevow.Athena.NodeByAttribute(elem.parentNode, "class", "save"));
    },

    function getElementValue(self, elem) {
        if(elem.tagName == "INPUT" && elem.type == "text")
            return elem.value;
        if(elem.tagName == "SELECT") {
            var options = elem.getElementsByTagName("option");
            return options[elem.selectedIndex].value;
        }
    },

    function save(self, elem) {
        var control_container = self.getContainers(elem.parentNode.parentNode)[1];
        var D = self.callRemote("savePref",
                                elem.parentNode.parentNode.id, 
                                self.getElementValue(self.firstElement(control_container)));

        D.addCallback(function(ign) { self.updatedPreferences() });
        D.addErrback(function(err) {
            MochiKit.DOM.replaceChildNodes(
                self.nodeByAttribute("class", "pref-error-log"),
                err);
        });
    },

    function selectOptionWithValue(self, elem, value) {
        for( var i = 0; i < elem.childNodes.length; i++ )
            if( elem.childNodes[i].value == value ) {
                elem.selectedIndex = i;
                break;
            }
    },

    function updatedPreferences(self) {
        document.location.reload();
    });
