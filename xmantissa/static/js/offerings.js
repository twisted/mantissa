
function offeringFeedback(message) {
    /* XXX TODO: make this look good - moe, please? :) */
    log(message);
}

function log(msg) {
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(msg));
    document.getElementById("log").appendChild(d);
}

function offeringClicked(node) {
    var nodeClass = node.getAttribute('class');
    if (nodeClass == 'installed') {
        return false;
    } else if (nodeClass == 'uninstalled') {
        var d = installOffering(node.getAttribute('id'));
        d.addCallback(function(result) {
                          offeringFeedback("Good job.");
                          node.setAttribute('class', 'installed');
                      });
        d.addErrback(function(error) {
                         offeringFeedback("You are the loser.");
                     });
        return false;
    } else {
        offeringFeedback('Server error!  Node class was ' + nodeClass);
        return false;
    }
}

function installOffering(offeringName) {
    return server.callRemote('installOffering', offeringName);
}

function installSignup(form) {

    var vis = document.createTreeWalker(form,
                                        NodeFilter.SHOW_ELEMENT,
                                        function (n) {
                                            if (n.tagName == 'INPUT') {
                                                return NodeFilter.FILTER_ACCEPT;
                                            } else {
                                                return NodeFilter.FILTER_SKIP;
                                            }
                                        },
                                        false);

    var provisionableFactoryNames = [];

    var input;
    while ((input = vis.nextNode()) != null) {
        if (input.type == "checkbox" && input.checked) {
            provisionableFactoryNames.push(input.name);
        }
    };

    if (!provisionableFactoryNames.length) {
        offeringFeedback("You didn't select any provisionable factories.");
    } else {
        var kind = null;
        for(var i = 0; i < form.kind.length; i++) {
            if(form.kind[i].checked) {
                kind = form.kind[i].value;
            }
        }
        var d = server.callRemote('createSignup',
                                  kind,
                                  form.url.value,
                                  provisionableFactoryNames);
        d.addBoth(function (result) {
            offeringFeedback("Done: " + result);
        });
    }

    return false;
}
