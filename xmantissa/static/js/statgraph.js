
// import MochiKit
// import GraphKit
// import Mantissa

Mantissa.StatGraph = {};

Mantissa.StatGraph.GraphData = Divmod.Class.subclass();

Mantissa.StatGraph.GraphData.methods(
    function __init__(self, xs, ys, canvas) {
        self.graph = new CanvasGraph(canvas);
        self.xs = xs;
        self.ys = ys;
    },

    function draw(self) {
        self.graph.setDataset("data", map(null, range(self.xs.length), self.ys));
        self.graph.xlabels = self.xs;
        self.graph.clear();
        var h8 = {};
        h8["data"] = Color.blueColor();
        self.graph.drawLinePlot(h8);
    });

Mantissa.StatGraph.StatGraph = Nevow.Athena.Widget.subclass("Mantissa.StatGraph.StatGraph");
Mantissa.StatGraph.StatGraph.methods(
    function __init__(self, node) {
        Mantissa.StatGraph.StatGraph.upcall(self, '__init__', node);
        self.graphs = {};
        self.callRemote('buildGraphs').addCallback(function (data) {
            for (var i = 0; i < data.length; i++) {
                var g = new Mantissa.StatGraph.GraphData(data[i][0], data[i][1], self._newCanvas(data[i][3]));
                self.graphs[data[i][2]] = g;
                g.draw();
            }
        });
    },

    function _newCanvas(self, title) {
        var container = document.createElement('div');
        var t = document.createElement('div');
        var container2 = document.createElement('div');
        var canvas = document.createElement("canvas");
        t.appendChild(document.createTextNode(title));
        container.appendChild(t)
        container.appendChild(container2);
        container2.appendChild(canvas);
        t.style.textAlign = "center";
        t.style.width = "500px";
        canvas.width = 500;
        canvas.height = 200;
        self.node.appendChild(container);
        return canvas;
    },

    function update(self, name, xdata, ydata, /* optional */ xs, ys, title) {
        var g = self.graphs[name];
        if (g == undefined) {
            if (xs == undefined || ys == undefined) {
                throw new Error("Undefined pre-existing data arrays, cannot create new graph.");
            }
            g = new Mantissa.StatGraph.GraphData(xs, ys, self._newCanvas(title));
            self.graphs[name] = g;
        }
        g.ys.push(ydata);
        if (g.ys.length > 60) {
            g.ys.shift();
        }
        g.xs.push(xdata);
        if (g.xs.length > 60) {
            g.xs.shift();
        }
        g.draw();
    });
