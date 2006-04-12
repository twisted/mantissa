
// import Mantissa
// import Mantissa.LiveForm

Mantissa.Offering.UninstalledOffering = Nevow.Athena.Widget.subclass('Mantissa.Offering.UninstalledOffering');
Mantissa.Offering.UninstalledOffering.methods(
    function installOffering(self, offeringName) {
        return self.callRemote('installOffering', offeringName);
    },

    function install(self) {
    self.node.setAttribute('class', 'installing');
        var d = self.callRemote('install', {});
        d.addCallbacks(function(result) {
            Mantissa.feedback('Installed');
            self.node.setAttribute('class', 'installed');
            self.node.onclick = null;
        }, function(err) {
            self.node.setAttribute('class', 'uninstalled');
            Mantissa.feedback('Failure: ' + err);
        });
    });
