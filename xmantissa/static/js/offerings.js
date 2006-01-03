
// import Mantissa
// import Mantissa.Forms

if (typeof Mantissa.Offering == 'undefined') {
    Mantissa.Offering = {};
}

Mantissa.Offering.UninstalledOffering = Nevow.Athena.Widget.subclass();
Mantissa.Offering.UninstalledOffering.prototype.installOffering = function(offeringName) {
    return this.callRemote('installOffering', offeringName);
};

Mantissa.Offering.UninstalledOffering.prototype.install = function() {
    var self = this;
    this.node.setAttribute('class', 'installing');
    var d = this.callRemote('install', {});
    d.addCallbacks(function(result) {
        Mantissa.feedback('Installed');
        self.node.setAttribute('class', 'installed');
        self.node.onclick = null;
    }, function(err) {
        self.node.setAttribute('class', 'uninstalled');
        Mantissa.feedback('Failure: ' + err);
    });
};

Mantissa.Offering.SignupConfiguration = Nevow.Athena.Widget.subclass();
Mantissa.Offering.SignupConfiguration.prototype.install = function() {
    var benefactorFactoryNamesAndConf = [];

    /* Collect all the selected provisionable factories.
     */
    this.visitNodes(function(node) {
        if (node.type == 'checkbox' && node.checked) {
            var provName = node.name;
            var provConf = Mantissa.Forms.accumulateInputs(node.parentNode, function(inputNode) {
                return (inputNode != node);
            });
            benefactorFactoryNamesAndConf.push([provName, provConf]);
        }
    });

    if (!benefactorFactoryNamesAndConf.length) {
        Mantissa.feedback("You didn't select any provisionable factories.");
        return;
    }

    /* Find the signup mechanism that was selected, as well as any
     * configuration associated with it..
     */
    var signupMechanism = null;
    var signupChoiceNode = null;

    this.visitNodes(function(node) {
        if (node.type == 'radio' && node.checked) {
            signupMechanism = node.value;
            signupChoiceNode = node;
            return false;
        }
    });

    if (signupMechanism == null) {
        Mantissa.feedback("You didn't select a signup mechanism.");
        return;
    }

    var signupConfiguration = Mantissa.Forms.accumulateInputs(signupChoiceNode.parentNode, function(node) {
        return (node != signupChoiceNode);
    });

    Mantissa.feedback(MochiKit.Base.serializeJSON(benefactorFactoryNamesAndConf));
    Mantissa.feedback(MochiKit.Base.serializeJSON(signupConfiguration));

    var d = server.callRemote('createSignup',
                              signupMechanism,
                              signupConfiguration,
                              benefactorFactoryNamesAndConf);
    d.addBoth(function (result) {
        Mantissa.feedback(result);
    });
};

Mantissa.Offering.SingleEndowment = Nevow.Athena.Widget.subclass();
Mantissa.Offering.SingleEndowment.prototype.__init__ = function(node) {
    Mantissa.Offering.SingleEndowment.upcall(this, '__init__', node);
    this.state = 'check';
    this.factoryFieldset = this.nodeByAttribute('class', 'factory-fieldset');
    this.usernameFieldset = this.nodeByAttribute('class', 'username-fieldset');
};

Mantissa.Offering.SingleEndowment.prototype.loaded = function() {
    this.usernameFieldset.style.display = 'block';
};

Mantissa.Offering.SingleEndowment.prototype.check = function() {
    var self = this;
    self.state = 'ignore';
    var d = self.callRemote('userExists', self.node.username.value);
    d.addCallback(function(userExists) {
        if (userExists) {
            self.state = 'endow';
            self.username = self.node.username.value;
            self.factoryFieldset.style.display = 'block';
            self.usernameFieldset.style.display = 'none';
            self.node.username.value = '';
        } else {
            Mantissa.feedback('No such user.');
        }
    });
    d.addErrback(function(err) {
        alert(err);
    });
};

Mantissa.Offering.SingleEndowment.prototype.endow = function() {
    var self = this;
    var d = self.callRemote('endow', self.username, Mantissa.Forms.accumulateInputs(this.factoryFieldset));
    d.addCallback(function(result) {
        Mantissa.feedback(self.username + ' endowed.');
        self.state = 'check';
        self.factoryFieldset.style.display = 'none';
        self.usernameFieldset.style.display = 'block';
    });
    d.addErrback(function(err) {
        Mantissa.feedback('Crap: ' + err.message);
    });
};

Mantissa.Offering.SingleEndowment.prototype.formSubmitted = function() {
    var handler = this[this.state];
    if (handler != undefined) {
        handler.call(this);
    }
};
