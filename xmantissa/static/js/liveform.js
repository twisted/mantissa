
// import Mantissa
// import Mantissa.Forms
// import Nevow.Athena

if (Mantissa.LiveForm == undefined) {
    Mantissa.LiveForm = {};
}

Mantissa.LiveForm.FormWidget = Nevow.Athena.Widget.subclass();

Mantissa.LiveForm.FormWidget.prototype._accumulateInputs = function () {
    return Mantissa.Forms.accumulateInputs(this.node);
};

Mantissa.LiveForm.FormWidget.prototype.submit = function () {
    return this.callRemote('invoke', this._accumulateInputs());
};
