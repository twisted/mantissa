
Divmod.load('Mantissa');

if (Mantissa.Forms == undefined) {
    Mantissa.Forms = {};
}

Mantissa.Forms.accumulateInputs = function(rootNode, /* optional */ inputPredicate) {
    var inputs = {};
    var nodes = Nevow.Athena._walkDOM(rootNode, function(node) {
        return (node.tagName && (node.tagName.toLowerCase() == 'input') && (inputPredicate == undefined || inputPredicate(node)));
    });

    for (var n in nodes) {
        var theNode = nodes[n];
        if (theNode.type.toLowerCase() == 'checked' && !theNode.checked) {
            continue;
        }
        if (inputs[theNode.name] == undefined) {
            inputs[theNode.name] = [];
        }
        inputs[theNode.name].push(theNode.value);
    }
    return inputs;
};

