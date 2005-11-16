
function min(x, y) {
    if (x < y) {
        return x;
    } else {
        return y;
    }
}

function max(x, y) {
    if (x > y) {
        return x;
    } else {
        return y;
    }
}

function abs(n) {
    if (n < 0) {
        return -n;
    } else{
        return n;
    }
}

function SmoothScroller_scrollTo(x, y) {
    this.x = x;
    this.y = y;

    if (!this.scrolling) {
        this.scrolling = true;
        this._reallyScroll();
    }

}

function SmoothScroller__reallyScroll() {
    var x = this.x;
    var y = this.y;

    beforeX = window.scrollX
    beforeY = window.scrollY

    xScroll = (x - beforeX) / 50.0;
    yScroll = (y - beforeY) / 50.0;

    window.scrollTo(beforeX + xScroll, beforeY + yScroll);

    if (beforeX == window.scrollX) {
        xScroll = 0;
    }
    if (beforeY == window.scrollY) {
        yScroll = 0;
    }

    if (xScroll || yScroll) {
        function scrollLater() {
            theScroller._reallyScroll();
        }
        setTimeout(scrollLater, 20);
    } else {
        this.scrolling = false;
    }
}

function SmoothScroller() {
    this.x = null;
    this.y = null;
    this.scrolling = false;

    this.scrollTo = SmoothScroller_scrollTo;
    this._reallyScroll = SmoothScroller__reallyScroll;
}

theScroller = new SmoothScroller();

function submitInput(sourceNode) {
    var outputNode = document.getElementById('output');
    var inputTextNode = document.createTextNode(sourceNode.value);

    server.handle('input', sourceNode.value);
    outputNode.appendChild(inputTextNode);
    sourceNode.value = '';
    return false;
}

function appendManholeOutput(outputLines) {
    var outputNode = document.getElementById('output');
    var inputNode = document.getElementById('source');

    var outputLine = null;
    var outputDiv = null;

    for (var n = 0; n < outputLines.length; n++) {
        outputDiv = document.createElement('div');
        outputLine = document.createTextNode(outputLines[n]);
        outputDiv.appendChild(outputLine);
        outputNode.appendChild(outputDiv);
    }

    theScroller.scrollTo(0, document.height);
}
