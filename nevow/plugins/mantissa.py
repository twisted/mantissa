
from twisted.python import filepath

from nevow import athena

import xmantissa

mantissa = athena.JSPackage({
    u'Mantissa.TDB': filepath.FilePath(xmantissa.__file__).parent().child('static').child('js').child('tdb.js').path})
