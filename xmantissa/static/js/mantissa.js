if (typeof Mantissa == 'undefined') {
    Mantissa = {};
}

Mantissa.log = function(msg) {
    /* XXX TODO: make this look good - moe, please? :) */
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(msg));
    document.getElementById("log").appendChild(d);
};

Mantissa.feedback = function(message) {
    this.log(message);
};
