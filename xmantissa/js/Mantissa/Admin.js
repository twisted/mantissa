
// import Divmod.Runtime

// import Mantissa.TDB
// import Mantissa.LiveForm

Mantissa.Admin = {};

/**
 * Special TDB with support for retrieving additional detailed information
 * about particular users from the server and displaying it on the page
 * someplace.
 *
 * XXX TODO: Replace this with a scrolltable.
 */
Mantissa.Admin.LocalUserBrowser = Mantissa.TDB.Controller.subclass('Mantissa.Admin.LocalUserBrowser');
Mantissa.Admin.LocalUserBrowser.methods(
    function _getUserDetailElement(self) {
        if (self._userDetailElement == undefined) {
            var n = document.createElement('div');
            n.setAttribute('class', 'user-detail');
            self.node.appendChild(n);
            self._userDetailElement = n;
        }
        return self._userDetailElement;
    },

    /**
     * Called by a TDB action click handler.  Retrieves information about the
     * clicked user from the server and dumps it into a node (created for this
     * purpose, on demand).  Removes the existing content of that node if
     * there is any.
     *
     * XXX - Can't use an index here - must use a unique, stable identifier.
     */
    function updateUserDetail(self, node, idx, event, action) {
        self._updateUserDetail(idx, action);
        return false;
    },

    function _updateUserDetail(self, index, action) {
        var d = self.callRemote('getActionFragment', index, action);
        d.addCallback(
            function(widgetInfo) {
                return self.addChildWidgetFromWidgetInfo(widgetInfo);
            });
        d.addCallback(
            function(widget) {
                var n = self._getUserDetailElement();
                n.appendChild(widget.node);
            });
        return d
    });
