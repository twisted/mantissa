import os
import shutil
import tarfile

from axiom.store import Store

from xmantissa.signup import FreeTicketSignup

def createDatabase(s):
    FreeTicketSignup(store=s,
                     prefixURL=u'/a/b',
                     booth=s,
                     benefactor=s)

# Below here should eventually be framework code, and is in fact identical to
# the existing test in axiom.test.historic.  Refactor after this branch is
# merged.

def determineFile(f):
    return os.path.join(
        os.path.dirname(f),
        os.path.basename(f).split("stub_")[1].split('.py')[0]+'.axiom')

if __name__ == '__main__':
    dbfn = determineFile(__file__)
    s = Store(dbfn)
    s.transact(createDatabase, s)
    s.close()
    tarball = tarfile.open(dbfn+'.tbz2', 'w:bz2')
    tarball.add(os.path.basename(dbfn))
    tarball.close()
    shutil.rmtree(dbfn)
