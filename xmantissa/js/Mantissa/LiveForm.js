// import Divmod
// import Divmod.Runtime

// import Nevow
// import Nevow.Athena

// import Mantissa


Mantissa.LiveForm.RepeatedLiveFormWrapper = Nevow.Athena.Widget.subclass(
    'Mantissa.LiveForm.RepeatedLiveFormWrapper');
/**
 * Widget which wraps a L{Mantissa.LiveForm.FormWidget}.
 */
Mantissa.LiveForm.RepeatedLiveFormWrapper.methods(
    function __init__(self, node, formName) {
        Mantissa.LiveForm.RepeatedLiveFormWrapper.upcall(
            self, '__init__', node);
        self.formName = formName;
    },

    /**
     * Remove our node from the DOM
     */
    function dom_unrepeat(self) {
        self.detach();
        self.node.parentNode.removeChild(self.node);
        return false;
    },

    /**
     * Defer to our child liveform.
     */
    function gatherInputs(self) {
        return self.childWidgets[0].gatherInputs();
    },

    /**
     * Defer to our child liveform.
     */
    function setInputValues(self, values) {
        return self.childWidgets[0].setInputValues(values);
    });

Mantissa.LiveForm.RepeatableForm = Nevow.Athena.Widget.subclass(
    'Mantissa.LiveForm.RepeatableForm');
/**
 * Widget which knows how to ask its server for a copy of a liveform, and how
 * to insert the liveform into the document.
 */
Mantissa.LiveForm.RepeatableForm.methods(
    function __init__(self, node, formName) {
        Mantissa.LiveForm.RepeatableForm.upcall(self, '__init__', node);
        self.formName = formName;
    },

    /**
     * Implement C{gatherInputs} so we can pretend to be a liveform, by
     * accumulating the result of broadcasting the method call to all of our
     * child widgets.
     */
    function gatherInputs(self) {
        var inputs = [];
        for(var i = 0; i < self.childWidgets.length; i++) {
            inputs.push(self.childWidgets[i].gatherInputs());
        }
        return inputs;
    },

    /**
     * Call C{setInputValues} on each child widget with the associated set of
     * values of the input list, or (for API compatibility with
     * L{Mantissa.LiveForm.FormWidget}) on the first child if the input is not
     * a list.
     */
    function setInputValues(self, valuesArray) {
        /**
         * is there a better way to differentiate between arrays and objects?
         */
        if(valuesArray.length === undefined) {
            self.childWidgets[0].setInputValues(valuesArray);
        } else {
            for(var i = 0; i < valuesArray.length; i++) {
                self.childWidgets[i].setInputValues(valuesArray[i]);
            }
        }
    },

    /**
     * Request a copy of the form we are associated with, and insert the resulting
     * widget's node into the DOM.
     */
    function repeat(self) {
        var result = self.callRemote('repeatForm');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.node.appendChild(widget.node);
            });
        return result;

    },

    /**
     * DOM event handler which calls L{repeat}.
     */
    function dom_repeat(self) {
        self.repeat();
        return false;
    });


/**
 * Error, generally received from the server, indicating that some input was
 * rejected and the form action was not taken.
 *
 * At some future point, the attributes offered by this class (or another class
 * which may supercede it) should be expanded to indicate more precisely which
 * input was rejected (eg, by supplying a key or list of keys for input nodes
 * corresponding to the rejected values).
 *
 * @ivar message: A string giving an explaination of why the input was
 *     rejected.
 */
Mantissa.LiveForm.InputError = Divmod.Error.subclass("Mantissa.LiveForm.InputError");
Mantissa.LiveForm.InputError.methods(
    function __init__(self, message) {
        self.message = message;
    });


Mantissa.LiveForm.BadInputName = Divmod.Error.subclass("Mantissa.LiveForm.BadInputName");
/**
 * Thrown when there is an input name passed to one of L{FormWidget}'s methods
 * doesn't correspond to an input in the widget's document
 */
Mantissa.LiveForm.BadInputName.methods(
    function __init__(self, name) {
        self.name = name;
    },

    function toString(self) {
        return "no element with name " + self.name;
    });

Mantissa.LiveForm.NodeCountMismatch = Divmod.Error.subclass("Mantissa.LiveForm.NodeCountMismatch");
/**
 * Thrown where there is a mismatch between the number of values in one of the
 * input lists passed to L{FormWidget.setInputValues} and the number of actual
 * nodes in the document for that key
 */
Mantissa.LiveForm.NodeCountMismatch.methods(
    function __init__(self, nodeName, givenNodes, actualNodes) {
        self.nodeName = nodeName;
        self.givenNodes = givenNodes;
        self.actualNodes = actualNodes;
    },

    function toString(self) {
        return "you supplied " + self.givenNodes +
               " values for input " + self.nodeName +
               " but there are " + self.actualNodes +
               " nodes";
    });


Mantissa.LiveForm.MessageFader = Divmod.Class.subclass("Divmod.Class.MessageFader");
/**
 * Fade a node in, then out again.
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
            currentOpacity += (self.inRate / TICKS_PER_SECOND);
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
        return self.fadeIn().addCallback(function() { return self.fadeOut(); });
    });


Mantissa.LiveForm.FormWidget = Nevow.Athena.Widget.subclass('Mantissa.LiveForm.FormWidget');
/**
 * Represent a form which can be submitted via Athena remote method calls.
 */
Mantissa.LiveForm.FormWidget.DOM_DESCEND = Divmod.Runtime.Platform.DOM_DESCEND;
Mantissa.LiveForm.FormWidget.DOM_CONTINUE = Divmod.Runtime.Platform.DOM_CONTINUE;
Mantissa.LiveForm.FormWidget.methods(
    function __init__(self, node, formName) {
        Mantissa.LiveForm.FormWidget.upcall(self, '__init__', node);
        self.formName = formName;
    },

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

    /**
     * Try to find the first node with class=C{className}, and display it as a
     * block element if we find it
     */
    function _showMessage(self, className) {
        var m = self.nodeByAttribute("class", className, null);
        if(m != null) {
            m.style.display = "block";
        }
    },

    /**
     * Try to find the first node with class=C{className}, and hide it if we
     * find it
     */
    function _hideMessage(self, className) {
        var m = self.nodeByAttribute("class", className, null);
        if(m != null) {
            m.style.display = "none";
        }
    },

    function showProgressMessage(self) {
        self._showMessage("progress-message");
    },

    function hideProgressMessage(self) {
        self._hideMessage("progress-message");
    },

    function showSuccessMessage(self) {
        self._showMessage("success-message");
    },

    function hideSuccessMessage(self) {
        self._hideMessage("success-message");
    },

    /**
     * If C{self.node} is a form element, reset its inputs to their default values.
     *
     * Note that this is broken if live renderer for this LiveForm is on any
     * element other than the form element.  This should probably be
     * implemented by keeping a structured representation of the form inputs
     * separate from the DOM (perhaps backed by DOM objects - but the API
     * should avoid DOM concerns) and performing such actions as form resets
     * through that interface instead.  This will have the advantage that
     * subforms can be handled explicitly, either to include them (as happens
     * now, by accident) or exclude them (which is currently impossible).  This
     * will also vastly simplify C{gatherInputs} and {setInputValues} and their
     * associated helper methods.
     */
    function reset(self) {
        if (self.node.tagName.toLowerCase() == "form") {
            self.node.reset();
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

        self.reset();

        self.hideProgressMessage();

        var succm = self.nodeByAttribute('class', 'success-message', null);
        if (succm === null) {
            return Divmod.Defer.succeed(null);
        }
        succm.appendChild(document.createTextNode(resultstr));

        self.showSuccessMessage();
        var deferred = Divmod.Defer.Deferred();
        setTimeout(
            function() {
                self.hideSuccessMessage();
                deferred.callback(null);
            }, 800);
        return deferred;
    },

    // Not the best factoring, but we use this as a hook in
    // Mantissa.Validate.SignupForm - if you can factor this better please do
    // so.

    function runFader(self, fader) {
        return fader.start();
    },

    function submitFailure(self, err) {
        self.hideProgressMessage();
        var error = err.check(Mantissa.LiveForm.InputError);
        if (error !== null) {
            return self.displayInputError(error);
        } else {
            Divmod.log('liveform', 'Error submitting form: ' + err);
            return err;
        }
    },

    /**
     * Display the given error about rejected input to the user.
     *
     * @type err: L{Mantissa.LiveForm.InputError}.
     * @param err: The exception received from the server.
     */
    function displayInputError(self, error) {
        try {
            var statusNode = self.nodeById('input-error-message');
        } catch (err) {
            if (err instanceof Divmod.Runtime.NodeNotFound) {
                return;
            }
        }
        while (statusNode.childNodes.length) {
            statusNode.removeChild(statusNode.childNodes[0]);
        }
        statusNode.appendChild(document.createTextNode(error.message))
    },

    function traverse(self, visitor) {
        return Divmod.Runtime.theRuntime.traverse(self.node, visitor);
    },

    /**
     * Helper function which returns an object with C{get} and C{set} members
     * for getting and setting the value(s) of a <select> element.  For a
     * <select> with single selection, the return value of C{get} and the
     * argument passed to C{set} will be atoms.  For multiple-select nodes,
     * they will be lists.  For multiple-select nodes, it will unselect all
     * selected <option> nodes whose values aren't in the list it is passed.
     */
    function _getAccessorsForSelectNode(self, aNode) {
        var set = function(values) {
            values = Divmod.objectify(values, values);
            for(var i = 0; i < aNode.options.length; i++) {
                aNode.options[i].selected = (aNode.options[i].value in values);
            }
        };

        if (aNode.type == 'select-one') {
            return {get: function() {
                        return aNode.value
                    },
                    set: function(value) {
                        set([value]);
                    }};
        }

        var get = function() {
            var values = [];
            for (var i = 0; i < aNode.options.length; i++) {
                if (aNode.options[i].selected) {
                    values.push(aNode.options[i].value);
                }
            }
            return values;
        };

        return {get: get, set: set};
    },

    /**
     * Gather all form input nodes below C{self.node}, without traversing into
     * child widgets.  "Form input nodes" means <input>, <textarea> and
     * <select>
     *
     * @return: mapping of node names to arrays of objects with C{get} and
     * C{set} members, where C{get} is thunk which returns the value of the
     * node, and C{set} is a one argument function which changes the value of
     * the node
     */
    function gatherInputAccessors(self) {
        var makeAttributeAccessors = function(attr, node) {
            return {get: function() { return node[attr] },
                    set: function(v) { node[attr] = v }};
        };
        var accessors = {};
        var pushAccessors = function(node, accs) {
            if (accessors[node.name] == undefined) {
                accessors[node.name] = [];
            }
            accessors[node.name].push(accs);
        };

        self.traverse(
            function(aNode) {
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

                            var attr = 'value';
                            // If it's a checkbox or radio, we care about its
                            // checked-ness.
                            if (aNode.type.toLowerCase() == 'checkbox' ||
                                aNode.type.toLowerCase() == 'radio') {
                                attr = 'checked';
                            }
                            pushAccessors(aNode, makeAttributeAccessors(attr, aNode));
                        } else if (aNode.tagName.toLowerCase() == 'textarea') {
                            pushAccessors(aNode, makeAttributeAccessors('value', aNode));
                        } else if (aNode.tagName.toLowerCase() == 'select') {
                            pushAccessors(aNode, self._getAccessorsForSelectNode(aNode));
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
        return accessors;
    },

    /**
     * Returns a mapping of input node names to arrays of input node values
     */
    function gatherInputs(self) {
        var inputs = {};

        var pushOneValue = function(name, value) {
            if (inputs[name] == undefined) {
                inputs[name] = [];
            }
            inputs[name].push(value);
        };

        // First we gather our widget children.
        for (var i = 0; i < self.childWidgets.length; i++) {
            var wdgt = self.childWidgets[i];
            if ((wdgt.formName != undefined)
                    && (wdgt.gatherInputs != undefined)) {
                var inputname = wdgt.formName;
                pushOneValue(inputname, wdgt.gatherInputs());
            }
        }

        var accessors = self.gatherInputAccessors();
        for(var nodeName in accessors) {
            for(i = 0; i < accessors[nodeName].length; i++) {
                pushOneValue(nodeName, accessors[nodeName][i].get());
            }
        }
        return inputs;
    },

    /**
     * Set the values of inputs whose names are keys in C{valueMap} to the
     * corresponding values.  Values should be lists, where the length of each
     * list is the same as the number of elements.  e.g.:
     *
     * >>> setInputValues({foo: [1, 2]})
     *
     * will set the first element with name="foo" to 1 and the second to 2.
     *
     * for multiple-select <select>s, the values should be lists of more
     * values:
     *
     * >>> setInputValues({foo: [["bar", "baz"]]})
     *
     * will select the <option>s inside the first (and only)
     * <select name="foo" /> which have value="bar" & value="baz"
     *
     * @param valueMap: mapping of input node names to values
     *
     * @raises L{Mantissa.LiveForm.BadInputName}: if a key in C{valueMap}
     * doesn't correspond to an input element of this form
     *
     * @raises L{Mantissa.LiveForm.NodeCountMismatch}: if the number of values
     * given for an input name doesn't match the number of inputs with that
     * name
     */
    function setInputValues(self, valueMap) {
        var i, accessors = self.gatherInputAccessors();
        for(var nodeName in valueMap) {
            if(accessors[nodeName] === undefined) {
                throw Mantissa.LiveForm.BadInputName(nodeName);
            }
            if(accessors[nodeName].length != valueMap[nodeName].length) {
                throw Mantissa.LiveForm.NodeCountMismatch(
                        nodeName,
                        valueMap[nodeName].length,
                        accessors[nodeName].length);
            }
            for(i = 0; i < accessors[nodeName].length; i++) {
                accessors[nodeName][i].set(valueMap[nodeName][i]);
            }
        }
    });
