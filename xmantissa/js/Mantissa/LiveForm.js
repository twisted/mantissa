
// import Divmod
// import Divmod.Runtime

// import Nevow
// import Nevow.Athena

// import Mantissa

Mantissa.LiveForm.FormWidget = Nevow.Athena.Widget.subclass('Mantissa.LiveForm.FormWidget');
Mantissa.LiveForm.FormWidget.DOM_DESCEND = Divmod.Runtime.Platform.DOM_DESCEND;
Mantissa.LiveForm.FormWidget.DOM_CONTINUE = Divmod.Runtime.Platform.DOM_CONTINUE;

Mantissa.LiveForm.MessageFader = Divmod.Class.subclass("Divmod.Class.MessageFader");

/**
   Fade a node in, then out again.
 */
Mantissa.LiveForm.MessageFader.methods(
    function __init__(self, node) {
        self.node = node;
        self.timer = null;
        self.inRate = 1.0;      // in opacity / second
        self.outRate = 0.5;
        self.messageDelay = 5.0; // number of seconds message is left on-screen
    },

    /*
     * Cause the referenced Node to become fully opaque.  It must currently be
     * fully transparent.  Returns a Deferred which fires when this has been
     * done.
     */
    function fadeIn(self) {
        var currentOpacity = 0.0;
        var TICKS_PER_SECOND = 30.0;
        var fadedInDeferred = Divmod.Defer.Deferred();
        var inStep = function () {
            currentOpacity += (self.inRate / TICKS_PER_SECOND)
            if (currentOpacity > 1.0) {
                self.node.style.opacity = '1.0';
                self.timer = null;
                fadedInDeferred.callback(null);
            } else {
                self.node.style.opacity = currentOpacity;
                self.timer = setTimeout(inStep, 1000 * 1.0 / TICKS_PER_SECOND);
            }
        };

        /* XXX TODO - "block" is not the right thing to do here. The wrapped
         * node might be a table cell or something.
         */
        self.node.style.display = 'block';
        inStep();
        return fadedInDeferred;
    },

    /*
     * Cause the referenced Node to become fully transparent.  It must
     * currently be fully opaque.  Returns a Deferred which fires when this
     * has been done.
     */
    function fadeOut(self) {
        var fadedOutDeferred = Divmod.Defer.Deferred();
        var currentOpacity = 0.0;
        var TICKS_PER_SECOND = 30.0;

        var outStep = function () {
            currentOpacity -= (self.outRate / TICKS_PER_SECOND);
            if (currentOpacity < 0.0) {
                self.node.style.display = 'none';
                self.timer = null;
                fadedOutDeferred.callback(null);
            } else {
                self.node.style.opacity = currentOpacity;
                self.timer = setTimeout(outStep, 1000 * 1.0 / TICKS_PER_SECOND);
            }
        };

        outStep();
        return fadedOutDeferred;
    },

    /*
     * Go through one fade-in/fade-out cycle.  Return a Deferred which fires
     * when both steps have finished.
     */
    function start(self) {
        // kick off the timer loop
        self.fadeIn().addCallback(function() { return self.fadeOut(); });
    });


Mantissa.LiveForm.FormWidget.methods(
    function submit(self) {
        var d = self.callRemote('invoke', self.gatherInputs());

        self.showProgressMessage();

        d.addCallback(function(result) {
            return self.submitSuccess(result);
        });
        d.addErrback(function(err) {
            return self.submitFailure(err);
        });
        return d;
    },

    function showProgressMessage(self) {
        var pm = self.nodeByAttribute("class", "progress-message", null);
        if (pm !== null) {
            pm.style.display = 'block';
        }
    },

    function hideProgressMessage(self) {
        var pm = self.nodeByAttribute("class", "progress-message", null);
        if (pm !== null) {
            pm.style.display = 'none';
        }
    },

    function submitSuccess(self, result) {
        var resultstr;

        if (!result) {
            resultstr = 'Success!';
        } else {
            resultstr = ''+result;
        }

        Divmod.log('liveform', 'Form submitted: ' + resultstr);

        self.node.reset();
        self.hideProgressMessage();

        var succm = self.nodeByAttribute('class', 'success-message', null);
        if (succm === null) {
            return Divmod.Defer.succeed(null);
        }
        succm.appendChild(document.createTextNode(resultstr));

        return self.runFader(Mantissa.LiveForm.MessageFader(succm));
    },

    // Not the best factoring, but we use this as a hook in
    // Mantissa.Validate.SignupForm - if you can factor this better please do
    // so.

    function runFader(self, fader) {
        return fader.start();
    },

    function submitFailure(self, err) {
        Divmod.log('liveform', 'Error submitting form: ' + err);
        return err;
    },

    function traverse(self, visitor) {
        return Divmod.Runtime.theRuntime.traverse(self.node, visitor);
    },

    function getFormName(self) {
        // XXX TODO: the real way to do this would be to have a JSON object
        // sent from the server as part of the initialization process.  I'm
        // not sure where to squirrel that away right now, and I only need
        // this one string.  Feel free to fix.
        return Nevow.Athena.getAttribute(
            self.node, Nevow.Athena.XMLNS_URI, 'athena', 'formname');
    },

    /**
     * Returns a list of input nodes.
     */
    function gatherInputs(self) {
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
                        } else if (aNode.tagName.toLowerCase() == 'select') {
                            if (aNode.type == 'select-one') {
                                pushOneValue(aNode.name, aNode.value);
                            } else {
                                // If multiple values can be selected, get them
                                var values = [];
                                for (var i = 0; i < aNode.options.length; i++) {
                                    if (aNode.options[i].selected) {
                                        values.push(aNode.options[i].value);
                                    }
                                }
                                pushOneValue(aNode.name, values);
                            }
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
