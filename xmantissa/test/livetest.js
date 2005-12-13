Divmod.load('Mantissa');

if (Mantissa.Test == undefined) {
    Mantissa.Test = {};
}

Mantissa.Test.TestCase = Nevow.Athena.Widget.subclass();
Mantissa.Test.TestCase.prototype._run = function(reporter) {
    var self = this;

    self.node.setAttribute('class', 'test-running');
    try {
        var result = self.run()
    } catch (err) {
        self._failure(err, reporter)
        return;
    }
    if (result.addCallback && result.addErrback) {
        result.addCallback(function(result) { self._success(reporter); });
        result.addErrback(function(err) { self._failure(err, reporter); });
        return result;
    } else {
        self._success(reporter);
    }
};

Mantissa.Test.TestCase.prototype._failure = function(err, reporter) {
    this.node.setAttribute('class', 'test-failure');
    reporter.reportFailure(err);
};

Mantissa.Test.TestCase.prototype._success = function(reporter) {
    this.node.setAttribute('class', 'test-success');
    reporter.reportSuccess();
};

Mantissa.Test.TestSuite = Nevow.Athena.Widget.subclass();
Mantissa.Test.TestSuite.prototype.__init__ = function(node) {
    Mantissa.Test.TestSuite.upcall(this, '__init__', node);
    this._successNode = this.nodeByAttribute('class', 'test-success-count');
    this._failureNode = this.nodeByAttribute('class', 'test-failure-count');
    this._successCount = 0;
    this._failureCount = 0;
};

Mantissa.Test.TestSuite.prototype.run = function() {
    var self = this;

    /* For each child invoke the _run method
     */
    var visitTestCase = function(node) {
        var athenaID = Nevow.Athena.athenaIDFromNode(node);
        if (athenaID != null) {
            var athenaWidget = Nevow.Athena.Widget.fromAthenaID(athenaID);
            if (athenaWidget._run) {
                athenaWidget._run(self);
            }
        }
    };
    this.visitNodes(visitTestCase);
};

Mantissa.Test.TestSuite.prototype.reportSuccess = function() {
    this._successCount += 1;
    this._successNode.innerHTML = this._successCount;
};

Mantissa.Test.TestSuite.prototype.reportFailure = function(err) {
    this._failureCount += 1;
    this._failureNode.innerHTML = this._failureCount;
    Divmod.log('test-result', err.message);
};
