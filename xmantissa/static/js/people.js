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
