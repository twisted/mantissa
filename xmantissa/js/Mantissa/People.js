// import Mantissa.LiveForm
// import Mantissa.ScrollTable

/**
 * ScrollTable action which allows the user to edit the contact details for the
 * selected person.
 */
Mantissa.People.EditAction = Mantissa.ScrollTable.Action.subclass(
    'Mantissa.People.EditAction');
Mantissa.People.EditAction.methods(
    /**
     * Initialize the action by calling the base initializer with edit-specific
     * values.
     */
    function __init__(self) {
        Mantissa.People.EditAction.upcall(
            self, '__init__', 'edit', 'Edit',
            function(peopleScroller, row, editWidgetInfo) {
                var parent = peopleScroller.widgetParent;
                var d = parent.addChildWidgetFromWidgetInfo(editWidgetInfo);
                d.addCallback(function(widget) {
                        parent.setDetailWidget(widget);
                    });
            });
    });



/**
 * ScrollTable action which allows the user to delete the selected person.
 */
Mantissa.People.DeleteAction = Mantissa.ScrollTable.Action.subclass(
    'Mantissa.People.DeleteAction');
Mantissa.People.DeleteAction.methods(
    /**
     * Initialize the action by calling the base initializer with
     * delete-specific values.
     */
    function __init__(self) {
        Mantissa.People.DeleteAction.upcall(
            self, '__init__', 'delete', 'Delete',
            function(peopleScroller, row, ignored) {
                var index = peopleScroller.model.findIndex(row.__id__);
                peopleScroller.removeRow(index);
            });
    });



/**
 * Container for person interaction user interface elements.
 *
 * This also provides APIs for different parts of the UI to interact with each
 * other so they they don't directly depend on each other.
 *
 * @ivar existingDetailWidget: The current widget displayed in the detail area,
 *     or C{null} if there is none.
 */
Mantissa.People.Organizer = Nevow.Athena.Widget.subclass(
    'Mantissa.People.Organizer');
Mantissa.People.Organizer.methods(
    /**
     * Initialize C{existingDetailWidget} to C{null}.
     */
    function __init__(self, node) {
        Mantissa.People.Organizer.upcall(self, '__init__', node);
        self.existingDetailWidget = null;
    },

    function cbPersonError(self, err) {
        alert("Sorry something broke: " + new String(err));
    },

    /**
     * Replace the current detail view with the node from the given
     * L{Nevow.Athena.Widget}.
     */
    function setDetailWidget(self, widget) {
        var detail = self.nodeById('detail');
        while (detail.childNodes.length) {
            detail.removeChild(detail.childNodes[0]);
        }
        detail.appendChild(widget.node);
        if (self.existingDetailWidget !== null) {
            self.existingDetailWidget.detach();
        }
        self.existingDetailWidget = widget;
    },

    /**
     * Get an add person widget from the server and put it in the detail area.
     */
    function displayAddPerson(self) {
        var result = self.callRemote('getAddPerson');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.setDetailWidget(widget);
            });
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


/**
 * A flexible-height scrolling widget which allows contact information for
 * people to be edited.
 */
Mantissa.People.PersonScroller = Mantissa.ScrollTable.FlexHeightScrollingWidget.subclass(
    'Mantissa.People.PersonScroller');
Mantissa.People.PersonScroller.methods(
    function __init__(self, node, metadata) {
        self.actions = [Mantissa.People.EditAction(),
                        Mantissa.People.DeleteAction()];
        Mantissa.People.PersonScroller.upcall(
            self, '__init__', node, metadata, 10);
    });


Mantissa.People.ContactInfo = Nevow.Athena.Widget.subclass('Mantissa.People.ContactInfo');

Mantissa.People.ContactInfo.methods(
    function __init__(self, node) {
        self._nodeCache = {};
        Mantissa.People.ContactInfo.upcall(self, "__init__", node);
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
                /* XXX Remove the widget associated with that node */
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
        var createdDeferred = self.callRemote("createContactInfoItem", sectionName, input.value);
        createdDeferred.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        createdDeferred.addCallback(
            function(widget) {
                section["add-link"].parentNode.insertBefore(widget.node, section["add-link"]);
                section["add-link"].style.display = "";
                section["add-form"].style.display = "none";
                input.value = "";
                return widget.node;
            });
        return createdDeferred;
    });


/**
 * Specialized L{Mantissa.LiveForm.FormWidget} which doesn't reset its inputs
 * to their default values after being submitted.
 */
Mantissa.People.EditPersonForm = Mantissa.LiveForm.FormWidget.subclass(
    'Mantissa.People.EditPersonForm');
Mantissa.People.EditPersonForm.methods(
    /**
     * Override the parent behavior so that the newly entered values remain in
     * the form, since they are the values which are present on the server.
     */
    function reset(self) {
    });
