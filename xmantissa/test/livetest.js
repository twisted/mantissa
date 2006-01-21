
// import Nevow.Athena
// import Mantissa

if (Mantissa.Test == undefined) {
    Mantissa.Test = {};
}

Mantissa.Test.TestCase = Nevow.Athena.Widget.subclass('Mantissa.Test.TestCase');
Mantissa.Test.TestCase.methods(
    function _run(self, reporter) {

        self.node.setAttribute('class', 'test-running');
        try {
            var result = self.run();
        } catch (err) {
            self._failure(err, reporter);
            return;
        }
        if (result.addCallback && result.addErrback) {
            result.addCallback(function(result) { self._success(reporter); });
            result.addErrback(function(err) { self._failure(err, reporter); });
            return result;
        } else {
            self._success(reporter);
        }
    },

    function _failure(self, err, reporter) {
        self.node.setAttribute('class', 'test-failure');
        reporter.reportFailure(err);
    },

    function _success(self, reporter) {
        self.node.setAttribute('class', 'test-success');
        reporter.reportSuccess();
    });

Mantissa.Test.TestSuite = Nevow.Athena.Widget.subclass('Mantissa.Test.TestSuite');
Mantissa.Test.TestSuite.methods(
    function __init__(self, node) {
        Mantissa.Test.TestSuite.upcall(self, '__init__', node);
        self._successNode = self.nodeByAttribute('class', 'test-success-count');
        self._failureNode = self.nodeByAttribute('class', 'test-failure-count');
        self._successCount = 0;
        self._failureCount = 0;
    },

    function run(self) {
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
    },

    function reportSuccess(self) {
        self._successCount += 1;
        self._successNode.innerHTML = self._successCount;
    },

    function reportFailure(self, err) {
        self._failureCount += 1;
        self._failureNode.innerHTML = self._failureCount;
        Divmod.log('test-result', err.message);
    });

Mantissa.Test.Forms = Mantissa.Test.TestCase.subclass('Mantissa.Test.Forms');
Mantissa.Test.Forms.methods(
    function run(self) {
        return self.childWidgets[0].submit();
    });

Mantissa.Test.TextArea = Mantissa.Test.Forms.subclass('Mantissa.Test.TextArea');

Mantissa.Test.Traverse = Mantissa.Test.Forms.subclass('Mantissa.Test.Traverse');

Mantissa.Test.People = Mantissa.Test.Forms.subclass('Mantissa.Test.People');
