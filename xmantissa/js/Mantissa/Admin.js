
// import Divmod.Runtime

// import Mantissa.ScrollTable
// import Mantissa.LiveForm

Mantissa.Admin = {};

/**
 * Trivial L{Mantissa.ScrollTable.Action} subclass which sets a handler that
 * calls L{Mantissa.Admin.LocalUserBrowser.updateUserDetail} on the instance
 * that the action was activated in.
 */
Mantissa.Admin.EndowDepriveAction = Mantissa.ScrollTable.Action.subclass(
                                        'Mantissa.Admin.EndowDepriveAction');
Mantissa.Admin.EndowDepriveAction.methods(
    function __init__(self, name, displayName) {
        Mantissa.Admin.EndowDepriveAction.upcall(
            self, "__init__", name, displayName,
            function(localUserBrowser, row, result) {
                return localUserBrowser.updateUserDetail(result);
            });
    });

/**
 * Scrolltable with support for retrieving additional detailed information
 * about particular users from the server and displaying it on the page
 * someplace.
 */
Mantissa.Admin.LocalUserBrowser = Mantissa.ScrollTable.FlexHeightScrollingWidget.subclass('Mantissa.Admin.LocalUserBrowser');
Mantissa.Admin.LocalUserBrowser.methods(
    function __init__(self, node) {
        self.actions = [Mantissa.Admin.EndowDepriveAction("endow", "Endow"),
                        Mantissa.Admin.EndowDepriveAction("deprive", "Deprive")];

        Mantissa.Admin.LocalUserBrowser.upcall(self, "__init__", node, 10);
    },

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
     * Called by L{Mantissa.Admin.EndowDepriveAction}.  Retrieves information
     * about the clicked user from the server and dumps it into a node
     * (created for this purpose, on demand).  Removes the existing content of
     * that node if there is any.
     */
    function updateUserDetail(self, result) {
        var D = self.addChildWidgetFromWidgetInfo(result);
        return D.addCallback(
            function(widget) {
                var n = self._getUserDetailElement();
                while(0 < n.childNodes.length) {
                    n.removeChild(n.firstChild);
                }
                n.appendChild(widget.node);
            });
    });
