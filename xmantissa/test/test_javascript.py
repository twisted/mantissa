# Copyright (c) 2006 Divmod.
# See LICENSE for details.

"""
Runs mantissa javascript tests as part of the mantissa python tests
"""

from twisted.python.filepath import FilePath
from nevow.testutil import JavaScriptTestSuite, setJavascriptInterpreterOrSkip

class MantissaJavaScriptTestSuite(JavaScriptTestSuite):
    """
    Run all the mantissa javascript test
    """
    path = FilePath(__file__).parent()

    def testJSPlaceholders(self):
        return self.onetest('test_placeholders.js')

setJavascriptInterpreterOrSkip(MantissaJavaScriptTestSuite)
