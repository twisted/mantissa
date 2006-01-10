
// import Divmod
// import Mantissa
// import Nevow.Athena

if (Mantissa.LiveForm == undefined) {
    Mantissa.LiveForm = {};
}

Mantissa.LiveForm.FormWidget = Nevow.Athena.Widget.subclass();

Mantissa.LiveForm.FormWidget.method(
    'submit',
    function (self) {
        return self.callRemote('invoke', self.gatherInputs()).addCallback(
            function(result) {
                self.node.reset();
                Divmod.log('liveform', 'Form submitted: ' + result);
            }).addErrback(
                function(err) {
                    Divmod.log('liveform', 'Error submitting form: ' + err);
                    return err;
                });
    });

Mantissa.LiveForm.FormWidget.DOM_DESCEND = 'Mantissa.LiveForm.FormWidget.DOM_DESCEND';
Mantissa.LiveForm.FormWidget.DOM_CONTINUE = 'Mantissa.LiveForm.FormWidget.DOM_CONTINUE';

Mantissa.LiveForm.FormWidget.method(
    'traverse',
    function(self, visitor) {
        var deque = [self.node];
        while (deque.length != 0) {
            var curnode = deque.shift();
            var visitorResult = visitor(curnode);
            switch (visitorResult) {
            case Mantissa.LiveForm.FormWidget.DOM_DESCEND:
                for (var i = 0; i < curnode.childNodes.length; i++) {
                    // "maybe you could make me care about how many stop
                    // bits my terminal has!  that would be so retro!"
                    deque.push(curnode.childNodes[i]);
                }
                break;
            case Mantissa.LiveForm.FormWidget.DOM_CONTINUE:
                break;
            default :
                throw new Error(
                    "traverse() visitor returned illegal value: " + visitorResult);
                break;
            }
        }
    });


Mantissa.LiveForm.FormWidget.method(
    'getFormName',
    function (self) {
        // XXX TODO: the real way to do this would be to have a JSON object
        // sent from the server as part of the initialization process.  I'm
        // not sure where to squirrel that away right now, and I only need
        // this one string.  Feel free to fix.
        return Nevow.Athena.getAttribute(
            self.node, Nevow.Athena.XMLNS_URI, 'athena', 'formname');
    });

Mantissa.LiveForm.FormWidget.method(
    'gatherInputs',
    /**
     * Returns a list of text nodes.
     */
    function (self) {
        var inputs = {};

        var pushOneValue = function(name, value) {
            if (inputs[name] == undefined) {
                inputs[name] = [];
            }
            // Divmod.log("inputs", "adding input: " + name + " = " + value);
            inputs[name].push(value);
        };

        // First we gather our widget children.
        for (var i = 0; i < self.childWidgets.length; i++) {
            var wdgt = self.childWidgets[i];
            if ((wdgt.getFormName != undefined)
                && (wdgt.gatherInputs != undefined)) {
                var inputname = wdgt.getFormName();
                pushOneValue(inputname, wdgt.gatherInputs());
            }
        }

        // Now we go after some nodes.
        self.traverse(function (aNode) {
                if (aNode === self.node) {
                    return Mantissa.LiveForm.FormWidget.DOM_DESCEND;
                }
                if (Nevow.Athena.athenaIDFromNode(aNode) != null) {
                    // It's a widget.  We caught it in our other pass; let's
                    // not look at any of its nodes.
                    return Mantissa.LiveForm.FormWidget.DOM_CONTINUE;
                } else {
                    if (aNode.tagName) {
                        // It's an element
                        if (aNode.tagName.toLowerCase() == 'input') {
                            // It's an input

                            // If it's a checkbox or radio, we care about its
                            // checked-ness.
                            var aValue = null;
                            if (aNode.type.toLowerCase() == 'checkbox') {
                                aValue = aNode.checked;
                            } else if (aNode.type.toLowerCase() == 'radio') {
                                aValue = aNode.checked;
                            } else {
                                aValue = aNode.value;
                            }
                            pushOneValue(aNode.name, aValue);
                        } else if (aNode.tagName.toLowerCase() == 'textarea') {
                            // It's also an input, just not an input
                            // input.
                            var aValue = aNode.value;
                            pushOneValue(aNode.name, aValue);
                        } else {
                            // Examine the children, since it is some
                            // other kind of element.
                            return Mantissa.LiveForm.FormWidget.DOM_DESCEND;
                        }
                        // Inputs should not have sub-inputs; hooray a
                        // free optimization.
                        return Mantissa.LiveForm.FormWidget.DOM_CONTINUE;
                    }
                    // It's a text node... do we really need to
                    // descend?
                    return Mantissa.LiveForm.FormWidget.DOM_DESCEND;
                }
            });
        return inputs;
    });
