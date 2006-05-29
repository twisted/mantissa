
// import Mantissa.LiveForm

/*
  This just does validation for Mantissa user-info-requiring signup right now,
  but the principles could hopefully be applied to other forms of LiveForm
  validation eventually.
 */

/*
  XXX TODO: I really want to say "package Mantissa.Validate" or something.
 */

Mantissa.Validate.SignupForm = Mantissa.LiveForm.FormWidget.subclass(
    "Mantissa.Validate.SignupForm");

Mantissa.Validate.SignupForm.methods(
    function __init__(self, node) {
        Mantissa.Validate.SignupForm.upcall(self, '__init__', node);
        self.domain = document.location.hostname;
        var domarr = self.domain.split(".");
        if (domarr[0] === 'www') {
            domarr.unshift();
            self.domain = domarr.join('.');
        }
        self.inputCount = 0;
        var junk = self.gatherInputs();
        for (var yuck in junk) {self.inputCount++;}
        // minus one for domain, plus one for confirm...
        self.verifiedCount = 0;
        self.testedInputs = {};

        self.passwordInput = self.nodeByAttribute("name", "password");

        self.submitButton = self.nodeByAttribute("type", "submit");
    },

    // see LiveForm for explanation
    function runFader(self, fader) {
        return fader.fadeIn();
    },

    function submitSuccess(self, result) {
        var d = Mantissa.Validate.SignupForm.upcall(self, 'submitSuccess', result);
        d.addCallback(function() {
            window.location = '/login';
        });
        return d;
    },

    function defaultUsername(self, inputnode) {
        if (inputnode.value.length == 0) {
            inputnode.value = (self.nodeByAttribute("name", "firstName").value.toLowerCase()
                               + '.' +
                               self.nodeByAttribute("name", "lastName").value.toLowerCase());
        }
    },
    function verifyNotEmpty(self, inputnode) {
        /*
          This is bound using an athena handler to all the input nodes.

          We need to look for a matching feedback node for this input node.
         */
        self.verifyInput(inputnode, inputnode.value != '');
    },
    function verifyUsernameAvailable(self, inputnode) {
        var username = inputnode.value;
        self.callRemote("usernameAvailable",username, self.domain).addCallback(
            function (result) {
                self.verifyInput(inputnode, result);
            });
    },
    function verifyStrongPassword(self, inputnode) {
        self.verifyInput(
            inputnode,
            inputnode.value.length > 4);
    },
    function verifyPasswordsMatch(self, inputnode) {
        self.verifyInput(
            inputnode,
            (self.testedInputs['password']) &&
            (inputnode.value === self.passwordInput.value));
    },
    function verifyValidEmail(self, inputnode) {
        var cond = null;
        var addrtup = inputnode.value.split("@");
        // require localpart *and* domain
        if (addrtup.length == 2) {
            var addrloc = addrtup[0];
            // localpart can't be empty
            if (addrloc.length > 0) {
                // domain can't be empty
                var addrdom = addrtup[1].split('.');
                if (addrdom.length >= 1) {
                    for (var i = 0; i < addrdom.length; i++) {
                        var requiredLength;
                        if (i === (addrdom.length - 1)) {
                            // TLDs are all 2 or more chars
                            requiredLength = 2;
                        } else {
                            // other domains can be one letter
                            requiredLength = 1;
                        }
                        if (addrdom[i].length < requiredLength) {
                            // WHOOPS
                            cond = false;
                            break;
                        } else {
                            // okay so far...
                            cond = true;
                        }
                    }
                }
            } else {
                cond = false;
            }
        } else {
            cond = false;
        }
        self.verifyInput(inputnode, cond);
    },
    function verifyInput(self, inputnode, condition) {
        var statusNode = self._findStatusElement(inputnode);
        var status = '';
        var wasPreviouslyVerified = !!self.testedInputs[inputnode.name];

        if (condition) {
            statusNode.style.backgroundColor = 'green';
        } else {
            statusNode.style.backgroundColor = 'red';
        }

        if (condition != wasPreviouslyVerified) {
            self.testedInputs[inputnode.name] = condition;
            if (condition) {
                self.verifiedCount++;
            } else {
                self.verifiedCount--;
            }
            self.submitButton.disabled = !(
                self.verifiedCount === self.inputCount);
        }
    },
    function _findStatusElement(self, inputnode) {
        var fieldgroup = inputnode.parentNode;
        while (fieldgroup.getAttribute("class") != "verified-field") {
            fieldgroup = fieldgroup.parentNode;
        }
        var theNodes = fieldgroup.childNodes;
        for (var maybeStatusNodeIdx in theNodes) {
            var maybeStatusNode = theNodes[maybeStatusNodeIdx];
            if (typeof maybeStatusNode.getAttribute != 'undefined') {
                if (maybeStatusNode.getAttribute("class") == "verify-status") {
                    return maybeStatusNode;
                }
            }
        }
    },
    function gatherInputs(self) {
        inputs = Mantissa.Validate.SignupForm.upcall(
            self, 'gatherInputs');
        delete inputs['confirmPassword'];
        delete inputs['__submit__'];
        // screw you, hidden fields!
        inputs['domain'] = [self.domain];
        return inputs;
    });
