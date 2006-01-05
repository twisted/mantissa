
// import Mantissa
// import Mantissa.LiveForm

if (typeof Mantissa.Offering == 'undefined') {
    Mantissa.Offering = {};
}

Mantissa.Offering.UninstalledOffering = Nevow.Athena.Widget.subclass();
Mantissa.Offering.UninstalledOffering.prototype.installOffering = function(offeringName) {
    return this.callRemote('installOffering', offeringName);
};

Mantissa.Offering.UninstalledOffering.prototype.install = function() {
    var self = this;
    this.node.setAttribute('class', 'installing');
    var d = this.callRemote('install', {});
    d.addCallbacks(function(result) {
        Mantissa.feedback('Installed');
        self.node.setAttribute('class', 'installed');
        self.node.onclick = null;
    }, function(err) {
        self.node.setAttribute('class', 'uninstalled');
        Mantissa.feedback('Failure: ' + err);
    });
};
