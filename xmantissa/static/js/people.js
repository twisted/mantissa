if (typeof(Mantissa) == 'undefined') {
    Mantissa = {};
}

if (typeof(Mantissa.People) == 'undefined') {
    Mantissa.People = {};
}

Mantissa.People.Organizer = Nevow.Athena.Widget.subclass();

Mantissa.People.Organizer.prototype.cbPersonError = function(err) {
    alert("Sorry something broke: " + new String(err));
}

Mantissa.People.Organizer.prototype.replaceTDB = function(data) {
    // this is so bad
    var tdbc = Mantissa.TDB.Controller.get(
        this.nodeByAttribute(
            "athena:class", "Mantissa.TDB.Controller"));
    if(tdbc) {
        tdbc._setTableContent(data[0]);
    }
}

Mantissa.People.Organizer.prototype.addPerson = function(form) {
    var d = this.callRemote('addPerson', form.firstname.value,
                                         form.lastname.value,
                                         form.email.value);
    form.firstname.value = "";
    form.lastname.value = "";
    form.email.value = "";

    d.addCallback(this.replaceTDB).addErrback(this.cbPersonError);
}

Mantissa.People.InlinePerson = Nevow.Athena.Widget.subclass();

Mantissa.People.InlinePerson.method('showActions',
    function(self, event) {
        if(typeof(self.popdownTimeout) == "undefined") {
            self.popdownTimeout = null;
        }
        var personActions = self.nodeByAttribute('class', 'person-actions');

        personActions.style.top = event.pageY;
        personActions.style.left = event.pageX;

        MochiKit.DOM.showElement(personActions);
        var links = personActions.getElementsByTagName("A");
        for(var i = 0; i < links.length; i++) {
            links[i].addEventListener("mouseover", self.engagedLink, false);
        }
    });

Mantissa.People.InlinePerson.method('engagedPopup',
    function(self) {
        clearTimeout(self.popdownTimeout);
        self.popup = self.nodeByAttribute('class', 'person-actions');
    });

Mantissa.People.InlinePerson.method('disengagedPopup',
    function(self, event) {
        self.hideActions(false);
    });

Mantissa.People.InlinePerson.method('engagedLink',
    function(self, event) {
        clearTimeout(self.popdownTimeout);
    });

Mantissa.People.InlinePerson.method('hideActions',
    function(self, force) {
        var reallyHideActions = function() {
            MochiKit.DOM.hideElement(
                self.nodeByAttribute('class', 'person-actions'));
        }

        if(force) {
            reallyHideActions();
        } else {
            self.popdownTimeout = setTimeout(reallyHideActions, 120);
        }
    });
