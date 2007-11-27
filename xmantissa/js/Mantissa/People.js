// import Mantissa.LiveForm
// import Mantissa.ScrollTable

Mantissa.People.OrganizerView = Divmod.Class.subclass(
    'Mantissa.People.OrganizerView');
/**
 * View abstraction for L{Mantissa.People.Organizer}.
 *
 * @ivar nodeById: Callable which takes a node ID and returns a node.
 * @type nodeById: C{Function}
 */
Mantissa.People.OrganizerView.methods(
    function __init__(self, nodeById) {
        self.nodeById = nodeById;
    },

    /**
     * Set the "top" style property of the I{organizer} node, positioning it
     * within its parent.
     */
    function setOrganizerPosition(self) {
        var organizerNode = self.nodeById('organizer');
        var organizerTop = Divmod.Runtime.theRuntime.findPosY(
            organizerNode.parentNode);
        organizerNode.style.top = organizerTop + 'px';
    },

    /**
     * Remove the existing detail node and insert the specified one in its
     * place.
     *
     * @type nodes: A DOM node.
     */
    function setDetailNode(self, node) {
        self.clearDetailNodes();
        self.nodeById('detail').appendChild(node);
    },

    /**
     * Remove any existing detail nodes.
     */
    function clearDetailNodes(self) {
        var detailNode = self.nodeById('detail');
        while(0 < detailNode.childNodes.length) {
            detailNode.removeChild(detailNode.childNodes[0]);
        }
    },

    /**
     * Show the edit link.
     */
    function showEditLink(self) {
        self.nodeById('edit-link').style.display = '';
    },

    /**
     * Hide the edit link.
     */
    function hideEditLink(self) {
        self.nodeById('edit-link').style.display = 'none';
    },

    /**
     * Show the delete link.
     */
    function showDeleteLink(self) {
        self.nodeById('delete-link').style.display = '';
    },

    /**
     * Hide the delete link.
     */
    function hideDeleteLink(self) {
        self.nodeById('delete-link').style.display = 'none';
    },

    /**
     * Show the "cancel form" link.
     */
    function showCancelFormLink(self) {
        self.nodeById('cancel-form-link').style.display = '';
    },

    /**
     * Hide the "cancel form" link.
     */
    function hideCancelFormLink(self) {
        self.nodeById('cancel-form-link').style.display = 'none';
    });


/**
 * Container for person interaction user interface elements.
 *
 * This also provides APIs for different parts of the UI to interact with each
 * other so they they don't directly depend on each other.
 *
 * @ivar existingDetailWidget: The current widget displayed in the detail area,
 *     or C{null} if there is none.
 *
 * @ivar storeOwnerPersonName: The name of the "store owner person" (this
 * person can't be deleted).
 * @type storeOwnerPersonName: C{String}
 *
 * @ivar initialPersonName: The name of the person to load at
 * initialization time.  Defaults to C{undefined}.
 * @type initialPersonName: C{String} or C{undefined}
 *
 * @ivar initialState: The name for the state the person-detail area of the
 * view should be in after initialization.  Acceptable values are:
 * C{undefined} (blank view) or C{"edit"} (load the edit form for
 * L{initialPersonName}).  Defaults to C{undefined}.
 * @type initialState: C{String} or C{undefined}
 *
 * @ivar currentlyViewingName: The name of the person currently being viewed.
 * @type currentlyViewingName: C{String} or C{null}
 *
 * @type view: L{Mantissa.People.OrganizerView}
 */
Mantissa.People.Organizer = Nevow.Athena.Widget.subclass(
    'Mantissa.People.Organizer');
Mantissa.People.Organizer.methods(
    function __init__(self, node, storeOwnerPersonName, initialPersonName, initialState) {
        Mantissa.People.Organizer.upcall(self, '__init__', node);
        self.existingDetailWidget = null;
        self.storeOwnerPersonName = storeOwnerPersonName;
        self.view = self._makeView();
        self.view.setOrganizerPosition();
        self.initialPersonName = initialPersonName;
        if(initialPersonName === undefined) {
            self.currentlyViewingName = null;
        } else {
            self.currentlyViewingName = initialPersonName;
        }
        if(initialState === 'edit') {
            self.displayEditPerson();
        }
    },

    /**
     * Construct a L{Mantissa.People.OrganizerView}.
     *
     * @rtype: L{Mantissa.People.OrganizerView}
     */
    function _makeView(self) {
        return Mantissa.People.OrganizerView(
            function nodeById(id) {
                return self.nodeById(id);
            });
    },

    /**
     * Called by our child L{Mantissa.People.PersonScroller} when it has
     * finished initializing.  We take this opportunity to call
     * L{selectInPersonList} with L{initialPersonName}, if it's not
     * C{undefined}.
     */
    function personScrollerInitialized(self) {
        if(self.initialPersonName !== undefined) {
            self.selectInPersonList(self.initialPersonName);
        }
    },

    /**
     * Detach the existing detail widget, if there is one, and replace the
     * existing detail nodes with the node for the given widget.
     */
    function setDetailWidget(self, widget) {
        self.view.setDetailNode(widget.node);
        if (self.existingDetailWidget !== null) {
            self.existingDetailWidget.detach();
        }
        self.existingDetailWidget = widget;
    },

    /**
     * Get an add person widget from the server and put it in the detail area.
     */
    function displayAddPerson(self) {
        self.view.hideEditLink();
        self.view.hideDeleteLink();
        self.view.hideCancelFormLink();
        var result = self.callRemote('getAddPerson');
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.view.showCancelFormLink();
                widget.observeSubmission(
                    function(name) {
                        self._cbPersonModified(name);
                    });
                self.setDetailWidget(widget);
            });
        return false;
    },

    /**
     * Called when a person has been added, with their name.  Updates the
     * person list, and selects the newly-created person.
     */
    function _cbPersonModified(self, name) {
        self.displayPersonInfo(name);
        var result = self.refreshPersonList();
        result.addCallback(
            function(ignore) {
                self.selectInPersonList(name);
            });
        return result;
    },

    /**
     * Get our child L{Mantissa.People.PersonScroller}.
     *
     * @rtype: L{Mantissa.People.PersonScroller}
     */
    function getPersonScroller(self) {
        return self.childWidgets[0];
    },

    /**
     * Call C{emptyAndRefill} on our child L{Mantissa.People.PersonScroller}.
     */
    function refreshPersonList(self) {
        return self.getPersonScroller().emptyAndRefill();
    },

    /**
     * Call C{selectNamedPerson} on our child
     * L{Mantissa.People.PersonScroller}.
     */
    function selectInPersonList(self, name) {
        return self.getPersonScroller().selectNamedPerson(name);
    },

    /**
     * Shows a form for editing the person with L{nickname}.
     */
    function displayEditPerson(self) {
        var result = self.callRemote(
            'getEditPerson', self.currentlyViewingName);
        result.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        result.addCallback(
            function(widget) {
                self.view.hideEditLink();
                self.view.hideDeleteLink();
                self.view.showCancelFormLink();
                self.setDetailWidget(widget);
                widget.observeSubmission(
                    function(name) {
                        if(self.currentlyViewingName === self.storeOwnerPersonName) {
                            self.storeOwnerPersonNameChanged(name);
                        }
                        self._cbPersonModified(name);
                    });
            });
        return result;
    },

    /**
     * Update L{storeOwnerPersonName}, and notify our person scroller of the
     * change.
     *
     * @param name: The new name of the store-owner person.
     * @type name: C{String}
     */
    function storeOwnerPersonNameChanged(self, name) {
        self.storeOwnerPersonName = name;
        var personScroller = self.getPersonScroller();
        personScroller.storeOwnerPersonNameChanged(name);
    },

    /**
     * DOM event handler which calls L{displayEditPerson}.
     */
    function dom_displayEditPerson(self) {
        self.displayEditPerson();
        return false;
    },

    /**
     * Delete the person currently being viewed by calling the remote
     * C{deletePerson} method.
     */
    function deletePerson(self) {
        var result = self.callRemote(
            'deletePerson', self.currentlyViewingName);
        result.addCallback(
            function(passThrough) {
                self.view.clearDetailNodes();
                self.view.hideEditLink();
                self.view.hideDeleteLink();
                self.refreshPersonList();
                return passThrough;
            });
        return result;
    },

    /**
     * DOM event handler which calls L{deletePerson}.
     */
    function dom_deletePerson(self) {
        self.deletePerson();
        return false;
    },

    /**
     * "Cancel" the currently displayed form by loading the last-viewed
     * person.
     */
    function cancelForm(self) {
        self.view.clearDetailNodes();
        if(self.currentlyViewingName !== null) {
            self.displayPersonInfo(self.currentlyViewingName);
        }
        self.view.hideCancelFormLink();
    },

    /**
     * DOM event handler which calls L{cancelForm}.
     */
    function dom_cancelForm(self) {
        self.cancelForm();
        return false;
    },

    /**
     * Get a person info widget for the person with the specified name and put
     * it in the detail area.
     *
     * @type name: String
     * @param name: The I{name} of the L{xmantissa.people.Person} for
     *     which to load an info widget.
     */
    function displayPersonInfo(self, name) {
        self.view.hideEditLink();
        self.view.hideDeleteLink();
        self.view.hideCancelFormLink();
        self.currentlyViewingName = name;
        var result = self.callRemote('getContactInfoWidget', name);
        result.addCallback(
            function(markup) {
                self.view.setDetailNode(
                    Divmod.Runtime.theRuntime.parseXHTMLString(
                        markup).documentElement);
                self.view.showEditLink();
                if(name !== self.storeOwnerPersonName) {
                    self.view.showDeleteLink();
                }
            });
    });


Mantissa.People.PersonScroller = Mantissa.ScrollTable.ScrollTable.subclass(
    'Mantissa.People.PersonScroller');
/**
 * A flexible-height scrolling widget which allows contact information for
 * people to be edited.
 *
 * @ivar storeOwnerPersonName: The name of the "store owner" person.
 * @type storeOwnerPersonName: C{String}
 *
 * @ivar _nameToRow: A mapping of person names to DOM row nodes.
 */
Mantissa.People.PersonScroller.methods(
    function __init__(self, node, currentSortColumn, columnList,
        defaultSortAscending, storeOwnerPersonName) {
        Mantissa.People.PersonScroller.upcall(
            self, '__init__', node, currentSortColumn, columnList,
            defaultSortAscending);
        self.storeOwnerPersonName = storeOwnerPersonName;
        self._nameToRow = {};
    },

    /**
     * Update L[storeOwnerPersonName}.
     *
     * @param name: The new name of the store-owner person.
     * @type name: C{String}
     */
    function storeOwnerPersonNameChanged(self, name) {
        self.storeOwnerPersonName = name;
    },

    /**
     * Extend the base implementation with parent-widget load notification.
     */
    function loaded(self) {
        var initDeferred = Mantissa.People.PersonScroller.upcall(
            self, 'loaded');
        initDeferred.addCallback(
            function(passThrough) {
                self.widgetParent.personScrollerInitialized();
                return passThrough;
            });
        return initDeferred;
    },

    /**
     * Override the base implementation to not show any feedback.
     */
    function startShowingFeedback(self) {
        return {stop: function() {}};
    },

    /**
     * Get some DOM which visually represents the VIP status of a person.
     *
     * @param isVIP: Whether the person is a VIP.
     * @type isVIP: C{Boolean}
     *
     * @rtype: L{MochiKit.DOM.IMG}
     */
    function _getVIPColumnDOM(self, isVIP) {
        if(isVIP) {
            return MochiKit.DOM.IMG({src: "/Mantissa/images/vip-flag.png"});
        }
    },

    /**
     * Apply the I{person-list-selected-person-row} class to C{node}, and
     * remove it from the previously-selected row.
     */
    function _rowSelected(self, node) {
        if(self._selectedRow === node) {
            return;
        }
        node.setAttribute('class', 'person-list-selected-person-row');
        if(self._selectedRow !== undefined) {
            self._selectedRow.setAttribute('class', 'person-list-person-row');
        }
        self._selectedRow = node;
    },

    /**
     * Select the row of the person named C{name}.
     *
     * @param name: A person name.
     * @type name: C{String}
     */
    function selectNamedPerson(self, name) {
        self._rowSelected(self._nameToRow[name]);
    },

    /**
     * DOM event handler for when a cell is clicked.  Calls
     * L{Mantissa.People.Organizer.displayPersonInfo} on our parent organizer
     * with the name of the clicked person.
     *
     * @return: C{false}
     * @rtype: C{Boolean}
     */
    function dom_cellClicked(self, node) {
        self._rowSelected(node);
        self.widgetParent.displayPersonInfo(
            MochiKit.DOM.scrapeText(node));
        return false;
    },

    /**
     * Override the base implementation to make the whole row clickable.
     */
    function makeRowElement(self, rowOffset, rowData, cells) {
        var node = MochiKit.DOM.DIV(
            {"class": "person-list-person-row"},
            cells);
        self._nameToRow[rowData.name] = node;
        self.connectDOMEvent("onclick", "dom_cellClicked", node);
        return node;
    },

    /**
     * Override the base implementation to return an image node for the VIP
     * status cell, and a simpler, easier-to-style node for the person name
     * cell
     */
    function makeCellElement(self, colName, rowData) {
        if(colName == 'vip') {
            return self._getVIPColumnDOM(rowData.vip);
        }
        var columnObject = self.columns[colName];
        var columnValue = columnObject.extractValue(rowData);
        var columnNode = columnObject.valueToDOM(columnValue, self);

        if(rowData.vip) {
            className = 'people-table-vip-person-name';
        } else {
            className = 'people-table-person-name';
        }
        if(rowData.name == self.storeOwnerPersonName) {
            columnNode = [
                columnNode,
                MochiKit.DOM.IMG(
                    {'class': 'mantissa-star-icon',
                     'src': '/Mantissa/images/star-icon.png'})];
        }
        return MochiKit.DOM.SPAN({'class': className}, columnNode);
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


Mantissa.People._SubmitNotificationForm = Mantissa.LiveForm.FormWidget.subclass(
    'Mantissa.People._SubmitNotificationForm');
/**
 * L{Mantissa.LiveForm.FormWidget} subclass which notifies registered
 * observers with the value of the form's I{nickname} input after a successful
 * submission.
 *
 * @ivar observers: An array of observer functions which have been registered.
 */
Mantissa.People._SubmitNotificationForm.methods(
    function __init__(self, node, formName) {
        Mantissa.People._SubmitNotificationForm.upcall(
            self, '__init__', node, formName);
        self.observers = [];
    },

    /**
     * Register a callable to be invoked with a nickname string after a
     * successful submission.
     *
     * @param observer: A one-argument callable.
     */
    function observeSubmission(self, observer) {
        self.observers.push(observer);
    },

    /**
     * Handle creation success by invoking any registered observers.
     */
    function submitSuccess(self, result) {
        var nickname = self.gatherInputAccessors().nickname[0].get();
        for (var i = 0; i < self.observers.length; ++i) {
            self.observers[i](nickname);
        }
    });


/**
 * Specialized L{Mantissa.People._SubmitNotificationForm} which doesn't reset
 * its inputs to their default values after being submitted.
 */
Mantissa.People.EditPersonForm = Mantissa.People._SubmitNotificationForm.subclass(
    'Mantissa.People.EditPersonForm');
Mantissa.People.EditPersonForm.methods(
    /**
     * Override the parent behavior so that the newly entered values remain in
     * the form, since they are the values which are present on the server.
     */
    function reset(self) {
    });


/**
 * Trivial L{Mantissa.People._SubmitNotificationForm} subclass, used for
 * adding new people to the address book.
 */
Mantissa.People.AddPersonForm = Mantissa.People._SubmitNotificationForm.subclass(
    'Mantissa.People.AddPersonForm');


Mantissa.People._SubmitNotificationFormWrapper = Nevow.Athena.Widget.subclass(
    'Mantissa.People._SubmitNotificationFormWrapper');
/**
 * Trivial L{Nevow.Athena.Widget} subclass which forwards L{observeSubmission}
 * calls to its child form.
 */
Mantissa.People._SubmitNotificationFormWrapper.methods(
    /**
     * Notify our child widget.
     */
    function observeSubmission(self, observer) {
        self.childWidgets[0].observeSubmission(observer);
    });


/**
 * Overall representation of the interface for adding a new person.  Doesn't do
 * much except expose a method of the L{AddPersonForm} it contains to outside
 * widgets.
 */
Mantissa.People.AddPerson = Mantissa.People._SubmitNotificationFormWrapper.subclass(
    'Mantissa.People.AddPerson');


/**
 * Overall representation of the interface for editing an existing person.
 * Doesn't do much except expose a method of the L{EditPersonForm} it contains
 * to outside widgets.
 */
Mantissa.People.EditPerson = Mantissa.People._SubmitNotificationFormWrapper.subclass(
    'Mantissa.People.EditPerson');
