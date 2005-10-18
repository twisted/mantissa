function setText(elem, text) {
    if(!elem.childNodes.length) {
        var t = document.createTextNode(text);
        elem.appendChild(t);
    } else
        elem.firstChild.nodeValue = text;
}

function setSearchState(start, stop, total) {
    var rsummary = document.getElementById("results-summary");

    if(parseInt(total) == 0)
        rsummary.style.display = "none";
    else {
        setText(document.getElementById("viewing-start"), start);
        setText(document.getElementById("viewing-stop"), stop);
        setText(document.getElementById("total-matches"), total);
        rsummary.style.display = "block";
    }
}
