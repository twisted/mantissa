// import Mantissa
// import Mantissa.ScrollTable

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

Mantissa.People.PersonDetail = Nevow.Athena.Widget.subclass('PersonDetail');

Mantissa.People.PersonDetail.methods(
    function __init__(self, node) {
        self._nodeCache = {};
        Mantissa.People.PersonDetail.upcall(self, "__init__", node);
    },

    function _getEnclosingRow(self, node) {
        while(node.tagName.toLowerCase() != "tr") {
            node = node.parentNode;
        }
        return node;
    },

    /**
     * Display the "add" form that is associated with the given add link.
     * The add form is the form that gets used to attach a new piece
     * of data to a person.  The type of the data (email address, phone
     * number) is determined by what section of the page the add link
     * appears in, but we're not really concerned much about the type
     *
     * @param addLink: node
     */
    function showAddForm(self, addLink) {
        var sectionName = self._getEnclosingRow(addLink).className;
        if(!(sectionName in self._nodeCache)) {
            self._nodeCache[sectionName] = {};
        }
        var addForm = Nevow.Athena.FirstNodeByAttribute(
                        addLink.parentNode, "class", "add-contact-info");

        addForm.style.display = "";
        self._nodeCache[sectionName]["add-form"] = addForm;

        addLink.style.display = "none";
        self._nodeCache[sectionName]["add-link"] = addLink;
    },

    /**
     * Tell python that the user doesn't care about the datum
     * that is associated with C{deleteLink}.
     *
     * @param deleteLink: node
     */
    function deleteContactInfoItem(self, deleteLink) {
        var viewContainer = deleteLink.parentNode;
        var value = self._getValueNode(viewContainer).firstChild.nodeValue;
        self.callRemote("deleteContactInfoItem",
                        self._getEnclosingRow(deleteLink).className,
                        value).addCallback(
            function() {
                var item = viewContainer.parentNode;
                item.parentNode.removeChild(item);
            });
    },

    function _getValueNode(self, node) {
        return Nevow.Athena.FirstNodeByAttribute(node, "class", "value");
    },

    /**
     * Save changes to the datum associated with C{saveLink}
     *
     * @param saveLink: node
     */
    function saveContactInfoItem(self, saveLink) {
        var sectionName = self._getEnclosingRow(saveLink).className;
        var section = self._nodeCache[sectionName];
        var viewNode = self._getValueNode(section["view-container"]);
        var editInput = section["edit-container"].getElementsByTagName("input")[0];

        return self.callRemote("editContactInfoItem",
                        sectionName,
                        viewNode.firstChild.nodeValue,
                        editInput.value).addCallback(
            function() {
                viewNode.firstChild.nodeValue = editInput.value;
                section["view-container"].style.display = "";
                section["edit-container"].style.display = "none";
            });
    },

    /**
     * Toggle the visibility of the form that's used to
     * upload person mugshots
     */
    function toggleEditMugshotForm(self) {
        var form = document.forms["mugshot"];
        if(form.style.visibility == "hidden") {
            form.style.visibility = "";
        } else {
            form.style.visibility = "hidden";
        }
    },

    /**
     * Display the edit form form the datum associated with C{editForm}
     *
     * @param editLink: node
     */
    function showEditForm(self, editLink) {
        var sectionName = self._getEnclosingRow(editLink).className;
        if(!(sectionName in self._nodeCache)) {
            self._nodeCache[sectionName] = {};
        }

        var section = self._nodeCache[sectionName];
        section["view-container"] = editLink.parentNode;
        section["edit-container"] = Nevow.Athena.FirstNodeByAttribute(
                                        editLink.parentNode.parentNode,
                                        "class",
                                        "contact-info-edit-container");
        section["view-container"].style.display = "none";
        section["edit-container"].style.display = "";
    },

    /**
     * Cancel an in-progress edit of the datum associated with C{cancelLink}
     * Revert the value in the edit box, and hide it.
     *
     * @param cancelLink: node
     */
    function cancelEditForm(self, cancelLink) {
        var section = self._nodeCache[self._getEnclosingRow(cancelLink).className];
        section["view-container"].style.display = "";
        section["edit-container"].style.display = "none";
    },

    /**
     * Cancel an in-progress add of a new piece of contact information
     * Blank the value in the add form's text box, and hide the form.
     *
     * @param cancelLink: node
     */
    function cancelAddForm(self, cancelLink) {
        var section = self._nodeCache[self._getEnclosingRow(cancelLink).className];
        section["add-form"].getElementsByTagName("input")[0].value = "";
        section["add-form"].style.display = "none";

        section["add-link"].style.display = "";
    },

    /**
     * Tell the server that we'd like to associate a new piece of
     * contact information with our person.  The value of the
     * contact information is obtained from the text box of the
     * add form.
     *
     * @param createLink: node
     */
    function createContactInfoItem(self, createLink) {
        var sectionName = self._getEnclosingRow(createLink).className;
        var section = self._nodeCache[sectionName];
        var input = section["add-form"].getElementsByTagName("input")[0];
        return self.callRemote("createContactInfoItem", sectionName, input.value).addCallback(
            function(html) {
                var e = document.createElement("div");
                section["add-link"].parentNode.insertBefore(e, section["add-link"]);
                Divmod.Runtime.theRuntime.setNodeContent(
                    e,
                    '<div xmlns="http://www.w3.org/1999/xhtml">' + html + '</div>');

                section["add-link"].style.display = "";
                section["add-form"].style.display = "none";
                input.value = "";
                return e;
            });
    });
