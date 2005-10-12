# -*- test-case-name: xmantissa.test.test_interval -*-

"""
Calendar model and query implementation.
"""

from axiom import item
from axiom import attributes


def findOverlapping(startAttribute, # A
                    endAttribute,   # B
                    startValue,     # X
                    endValue,       # Y
                    ):
    """

    Return an L{axiom.iaxiom.IComparison} (an object that can be passed as the
    'comparison' argument to Store.query/.sum/.count) which will constrain a
    query against 2 attributes for ranges with overlap with the given
    arguments.

    For a database with Items of class O which represent values in this
    configuration:

            A                   B
            |-------------------|
       X        Y
      (c)      (d)          X        Y
       |--------|          (e)      (f)
                            |--------|

    X   Y
   (g) (h)                            X      Y
    |---|                            (i)    (j)
                                      |------|

    X                                     Y
   (k)                                   (l)
    |-------------------------------------|

    The query:
        myStore.query(
            O,
            findOverlapping(O.X, O.Y,
                            A, B))

    Will return a generator of Items of class O which represent segments c-d,
    e-f, and k-l, but NOT segments g-h or i-j.

    (NOTE: If you want to pass attributes of different classes for
    startAttribute and endAttribute, read the implementation of this method to
    discover the additional join clauses required.  This may be eliminated some
    day so for now, consider this method undefined over multiple classes.)

    In the database where this query is run, for an item N, all values of
    N.startAttribute must be less than N.endAttribute.

    startValue must be less than endValue.

    """
    if startValue == endValue:
        return attributes.AND(
            startValue > startAttribute,
            startValue < 
    assert startValue < endValue

    attributes.OR(
        )
