
from twisted.python import util

from nevow import athena

import xmantissa

def _f(*sibling):
    return util.sibpath(xmantissa.__file__, '/'.join(sibling))

mantissaPkg = athena.JSPackage({
    'Mantissa': _f('static', 'js', 'mantissa.js'),
    'Mantissa.LiveForm': _f('static', 'js', 'liveform.js'),
    'Mantissa.People': _f('static', 'js', 'people.js'),
    'Mantissa.TDB': _f('static', 'js', 'tdb.js'),
    'Mantissa.Offering': _f('static', 'js', 'offerings.js'),
    'Fadomatic': _f('static', 'js', 'fadomatic.js')
    })
