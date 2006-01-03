
from twisted.python import util

from nevow import athena

import xmantissa

def _f(*sibling):
    return util.sibpath(xmantissa.__file__, '/'.join(sibling))

mantissaPkg = athena.JSPackage({
    'Mantissa': _f('static', 'js', 'mantissa.js'),
    'Mantissa.Forms': _f('static', 'js', 'forms.js'), # deprecated!
    'Mantissa.LiveForm': _f('static', 'js', 'liveform.js'), # use this instead
    'Mantissa.TDB': _f('static', 'js', 'tdb.js'),
    'Mantissa.Offering': _f('static', 'js', 'offerings.js'),
    })
