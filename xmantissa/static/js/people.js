// import Mantissa

if (typeof(Mantissa.People) == 'undefined') {
    Mantissa.People = {};
}

Mantissa.People.Organizer = Nevow.Athena.Widget.subclass('Mantissa.People.Organizer');
Mantissa.People.Organizer.methods(
    function cbPersonError(self, err) {
        alert("Sorry something broke: " + new String(err));
    },

    function replaceTDB(self, data) {
        // this is so bad
        var tdbc = Mantissa.TDB.Controller.get(
            self.nodeByAttribute(
                "athena:class", "Mantissa.TDB.Controller"));
        if(tdbc) {
            tdbc._setTableContent(data[0]);
        }
    },

    function addPerson(self, form) {
        var d = self.callRemote('addPerson', form.firstname.value,
                                             form.lastname.value,
                                             form.email.value);
        form.firstname.value = "";
        form.lastname.value = "";
        form.email.value = "";

        d.addCallback(self.replaceTDB).addErrback(self.cbPersonError);
    });

Mantissa.People.InlinePerson = Nevow.Athena.Widget.subclass('Mantissa.People.InlinePerson');
Mantissa.People.InlinePerson.methods(
    function showActions(self, event) {
        self.personActions = self.nodeByAttribute('class', 'person-actions');
        self.personActions.style.top = event.pageY;
        self.personActions.style.left = event.pageX;

        MochiKit.DOM.showElement(self.personActions);

        self.eventTarget = event.target;
        self.eventTarget.onclick = function() {
            self.hideActions();
            return false;
        }

        var body = document.getElementsByTagName("body")[0];
        body.onclick = function(_event) {
            if(event.target == _event.target) {
                return false;
            }
            var e = _event.target;
            while(e && e != self.node) {
                e = e.parentNode;
            }
            if(e) {
                return false;
            }
            self.hideActions();
            body.onclick = null;
            return false;
        }
    },

    function hideActions(self) {
        self.eventTarget.onclick = function(event) {
            self.showActions(event);
            return false;
        }
            
        MochiKit.DOM.hideElement(self.personActions);
    });

alert(Mantissa.People.InlinePerson);
