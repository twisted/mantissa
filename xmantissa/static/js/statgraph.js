
// import MochiKit
// import PlotKit.Base
// import PlotKit.Layout
// import PlotKit.Canvas
// import PlotKit.SweetCanvas
// import Mantissa
function printfire()
    {
        if (document.createEvent)
        {
            printfire.args = arguments;
            var ev = document.createEvent("Events");
            ev.initEvent("printfire", false, true);
            dispatchEvent(ev);
        }
    }
Mantissa.StatGraph = {};

Mantissa.StatGraph.Pie = Divmod.Class.subclass();

Mantissa.StatGraph.Pie.methods(
    function __init__(self, slices, canvas) {
        self.slices = slices;
        self.canvas = canvas;
        canvas.height = 900;
        canvas.width = 900;
        var allXTicks = MochiKit.Base.map(function(L, val) { return {"label": L.substring(13), v: val};}, slices[0],
                                          MochiKit.Iter.range(slices[0].length));
        self.layout = new PlotKit.Layout("pie",  {"xTicks": allXTicks});
        self.layout.addDataset("data", MochiKit.Base.zip(MochiKit.Iter.range(self.slices[1].length), self.slices[1]));
        self.layout.evaluate();
        
        self.graph = new PlotKit.SweetCanvasRenderer(self.canvas, self.layout, {'axisLabelWidth':100});
        self.graph.clear();
        self.graph.render();
    },

    function draw(self) {
    }
    );

Mantissa.StatGraph.GraphData = Divmod.Class.subclass();

Mantissa.StatGraph.GraphData.methods(
    function __init__(self, xs, ys, canvas) {
        self.xs = xs;
        self.ys = ys;
        self.canvas = canvas;
        var xticks = [];
        self.layout = new PlotKit.Layout("line", {xTicks: xticks});
        self.graph = new PlotKit.SweetCanvasRenderer(self.canvas, self.layout, {});
    },

    function updateXTicks(self) {
        var allXTicks = MochiKit.Base.map(function(L, val) { return {"label": L, v: val};}, self.xs, 
                                          MochiKit.Iter.range(self.xs.length));
        // XXX find a better way to do this maybe?
        var len = allXTicks.length;
        self.layout.options.xTicks.length = 0;
        if (len > 5) {
            for (var i = 0; i < len; i += Math.floor(len/4)) {
                self.layout.options.xTicks.push(allXTicks[i]);
            }
        } else {
            self.layout.options.xTicks = allXTicks;
        }
        printfire("Done. " + self.layout.xticks.toSource());
    },

    function draw(self) {
        self.layout.addDataset("data", MochiKit.Base.map(null, MochiKit.Iter.range(self.xs.length), self.ys));
        self.updateXTicks();
        self.layout.evaluate();
        self.graph.clear();
        self.graph.render();
        //var h8 = {};
        //h8["data"] = Color.blueColor();
    });

Mantissa.StatGraph.StatGraph = Nevow.Athena.Widget.subclass("Mantissa.StatGraph.StatGraph");
Mantissa.StatGraph.StatGraph.methods(
    function __init__(self, node) {
        Mantissa.StatGraph.StatGraph.upcall(self, '__init__', node);
        self.graphs = {};
        self.callRemote('buildPie').addCallback(function (slices) {
            var g = new Mantissa.StatGraph.Pie(slices, self._newCanvas("Pie!"));
                self.pie = g;
                g.draw();
        }).addCallback(function (_) {
        self.callRemote('buildGraphs').addCallback(function (data) {
            for (var i = 0; i < data.length; i++) {
                var g = new Mantissa.StatGraph.GraphData(data[i][0], data[i][1], self._newCanvas(data[i][3]));
                self.graphs[data[i][2]] = g;
                g.draw();
            }
        })});
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
