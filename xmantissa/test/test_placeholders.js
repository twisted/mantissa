// Copyright (c) 2006 Divmod.
// See LICENSE for details.

/**
 * Tests for L{Mantissa.ScrollTable.PlaceholderModel}
 */

// import Mantissa.ScrollTable

/**
 * Set up a placeholder model with an initial placeholder which extends as far
 * as C{totalRows}.
 *
 * @type totalRows: integer
 * @rtype: L{Mantissa.ScrollTable.PlaceholderModel}
 */
function setUp(totalRows) {
    if(totalRows == undefined) {
        throw new Error("i need to know a number");
    }
    var model = Mantissa.ScrollTable.PlaceholderModel();
    model.registerInitialPlaceholder(totalRows, null);
    return model;
}

runTests([
    /**
     * Test L{Mantissa.ScrollTable.PlaceholderModel.createPlaceholder}
     */
    function testCreatePlaceholder() {
        var model = setUp(5);
        var p = model.createPlaceholder(0, 1, null);

        assert(p.start == 0, "expected a start of 0");
        assert(p.stop == 1, "expected a stop of 1");
        assert(p.node == null, "expected a null node");

        p = model.createPlaceholder(5, 11, 6);

        assert(p.start == 5, "expected a start of 5");
        assert(p.stop == 11, "expected a stop of 11");
        assert(p.node == 6, "expected a node of 6");
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.registerInitialPlaceholder}
     */
    function testRegisterInitialPlaceholder() {
        var model = setUp(5);

        assert(model.getPlaceholderCount() == 1, "expected one placeholder");

        var p = model.getPlaceholderWithIndex(0);

        assert(p.start == 0, "expected a start of 0");
        assert(p.stop == 5, "expected a stop of 5");
        assert(p.node == null, "expected a null node");
    },

    /**
     * Test L{Mantissa.ScrollTable.PlaceholderModel.replacePlaceholder}
     */
    function testReplacePlaceholder() {
        var model = setUp(5);

        model.replacePlaceholder(
            0, model.createPlaceholder(0, 1, null));

        assert(model.getPlaceholderCount() == 1, "expected one placeholder");

        var p = model.getPlaceholderWithIndex(0);

        assert(p.start == 0, "expected a start of 0");
        assert(p.stop == 1, "expected a stop of 1");
        assert(p.node == null, "expected a null node");
    },

    /**
     * Test L{Mantissa.ScrollTable.PlaceholderModel.dividePlaceholder}
     */
    function testDividePlaceholder(self) {
        var model = setUp(5);

        var above = model.createPlaceholder(0, 1, null);
        var below = model.createPlaceholder(1, 2, null);

        model.dividePlaceholder(0, above, below);

        assert(model.getPlaceholderCount() == 2, "expected two placeholders");

        var p1 = model.getPlaceholderWithIndex(0);

        assert(p1.start == above.start, "start doesn't match");
        assert(p1.stop == above.stop, "stop doesn't match");
        assert(p1.node == above.node, "node doesn't match");

        var p2 = model.getPlaceholderWithIndex(1);

        assert(p2.start == below.start, "start doesn't match");
        assert(p2.stop == below.stop, "stop doesn't match");
        assert(p2.node == below.node, "node doesn't match");
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findPlaceholderIndexForRowIndex}
     * when there is only one placeholder in the model
     */
    function testFindPlaceholderIndexForRowIndexOnePlaceholder(self) {
        var i, model = setUp(5), index, indices = [0, 1, 2, 3, 4];

        for(i = 0; i < indices.length; i++) {
            index = model.findPlaceholderIndexForRowIndex(indices[i]);
            assert(index == 0, "expected index=zero");
        }
        assert(model.findPlaceholderIndexForRowIndex(5) == null, "expected null");
    },

    /**
     * Test
     * L{Mantissa.ScrollTable.PlaceholderModel.findPlaceholderIndexForRowIndex}
     * where there are multiple placeholders in the model
     */
    function testFindPlaceholderIndexForRowMultiplePlaceholders(self) {
        var model = setUp(5);

        var one = model.createPlaceholder(0, 3, null);
        var two = model.createPlaceholder(3, 5, null);
        var three = model.createPlaceholder(5, 10, null);

        model.dividePlaceholder(0, one, two);
        model.dividePlaceholder(1, two, three);

        /* check that the return result of findPlaceholderIndexForRowIndex is
         * C{output} across C{inputs} */
        var checkOutputMany = function(inputs, output) {
            for(i = 0; i < inputs.length; i++) {
                res = model.findPlaceholderIndexForRowIndex(inputs[i]);
                assert(res == output, ("expected " + output + " for "
                                        + inputs[i] + " not " + res));
            }
        }

        checkOutputMany([0, 1, 2], 0);
        checkOutputMany([3, 4], 1);
        checkOutputMany([5, 6, 7, 8, 9], 2);
        checkOutputMany([10, 11], null);
    }]);
