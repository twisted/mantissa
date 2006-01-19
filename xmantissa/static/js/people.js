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
        self.eventTarget = event.target;
        self.eventTarget.onclick = function() { self.hideActions(); return false };

        self.personActions = self.nodeByAttribute('class', 'person-actions');
        self.personActions.style.top = event.pageY;
        self.personActions.style.left = event.pageX;

        MochiKit.DOM.showElement(self.personActions);
    });

Mantissa.People.InlinePerson.method('hideActions',
    function(self) {
        self.eventTarget.onclick = function(event) { self.showActions(event); return false };
        MochiKit.DOM.hideElement(self.personActions);
    });

