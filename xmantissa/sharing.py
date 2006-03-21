# -*- test-case-name: xmantissa.test.test_sharing -*-

# XXX TODO: 'Q2Q Verified' status of connection, or status, or role, or
# ... something, to distinguish between casual (i.e. spam-prevention) and real
# (i.e. accounting-database-access) security

import os

from zope.interface import implementedBy, directlyProvides

from twisted.python.reflect import qual, namedAny

from axiom import userbase
from axiom.item import Item
from axiom.attributes import reference, text, AND, inmemory
from axiom.upgrade import registerUpgrader

class NoSuchShare(Exception):
    """
    User requested an object that doesn't exist, was not allowed, or somesuch.
    """

class RoleRelationship(Item):
    schemaVersion = 1
    typeName = 'sharing_relationship'

    member = reference()
    group = reference()

class Role(Item):
    schemaVersion = 1
    typeName = 'sharing_role'
    externalID = text(allowNone=False)
    description = text()

    def becomeMemberOf(self, groupRole):
        self.store.findOrCreate(RoleRelationship,
                                group=groupRole,
                                member=self)

    def allRoles(self, memo=None):
        if memo is None:
            memo = set()
        elif self in memo:
            # this is bad, but we have successfully detected and prevented the
            # only really bad symptom, an infinite loop.
            return
        memo.add(self)
        yield self
        for groupRole in self.store.query(Role,
                                          AND(RoleRelationship.member == self,
                                              RoleRelationship.group == Role.storeID)):
            for roleRole in groupRole.allRoles(memo):
                yield roleRole

    def __repr__(self):
        return self.externalID.upper()

def _getSharedItemAndInterfaces(sharedProxy):
    # __providedBy__ is included so that adaptation will work as ... expected.
    # Maybe XXX TODO: add the ability to explicitly set a list of interfaces
    # provided by proxies?
    sharedInterfaces = super(SharedProxy, sharedProxy).__getattribute__('_sharedInterfaces')
    # sharedInterfaces = sharedInterfaces + ('__providedBy__',)
    sharedItem = super(SharedProxy, sharedProxy).__getattribute__('_sharedItem')
    return sharedInterfaces, sharedItem

ALLOWED_ON_PROXY = ['__provides__', '__dict__']

class SharedProxy(object):

    def __init__(self, sharedItem, sharedInterfaces):
        super(SharedProxy, self).__setattr__('_sharedItem', sharedItem)
        super(SharedProxy, self).__setattr__('_sharedInterfaces', sharedInterfaces)
        # Make me look *exactly* like the item I am proxying for, at least for
        # the purposes of adaptation
        # directlyProvides(self, providedBy(sharedItem))
        directlyProvides(self, sharedInterfaces)


    def __repr__(self):
        return 'SharedProxy(%r, %r)' % tuple(reversed(_getSharedItemAndInterfaces(self)))


    def __getattribute__(self, name):
        if name in ALLOWED_ON_PROXY:
            return object.__getattribute__(self,name)
        sharedInterfaces, sharedItem = _getSharedItemAndInterfaces(self)
        if name == 'sharedInterfaces':
            return sharedInterfaces
        for iface in sharedInterfaces:
            if name in iface:
                return getattr(sharedItem, name)
        raise AttributeError(name)


    def __setattr__(self, name, value):
        sharedInterfaces, sharedItem = _getSharedItemAndInterfaces(self)
        if name in sharedInterfaces:
            setattr(sharedItem, name, value)
        elif name in ALLOWED_ON_PROXY:
            self.__dict__[name] = value
        else:
            raise AttributeError("unsettable: "+repr(name))


    def __delattr__(self, name):
        sharedInterfaces, sharedItem = _getSharedItemAndInterfaces(self)
        if name in sharedInterfaces:
            delattr(sharedItem, name)


ALL_IMPLEMENTED_DB = u'*'
ALL_IMPLEMENTED = object()


class Share(Item):
    schemaVersion = 2
    typeName = 'sharing_share'

    shareID = text(allowNone=False)
    sharedItem = reference(allowNone=False)
    sharedTo = reference(allowNone=False)

    sharedInterfaceNames = text(allowNone=False)
    _sharedInterfaces = inmemory()

    def __init__(self, **kw):
        sa = kw.pop('sharedInterfaces')
        if sa is ALL_IMPLEMENTED:
            san = ALL_IMPLEMENTED_DB
        else:
            san = u','.join(map(qual, sa))
        kw['sharedInterfaceNames'] = san
        super(Share, self).__init__(**kw)


    def sharedInterfaces():
        def get(self):
            return self._sharedInterfaces
        # Maybe one day someone will want this, but it might be incorrect.
        # Think hard about it before uncommenting...

#         def set(self, newValue):
#             self._sharedInterfaces = tuple(newValue)
#             self.sharedAttributeNames = u','.join(self.sharedInterfaces)
        return get,
    sharedInterfaces = property(*sharedInterfaces())


    def activate(self):
        if not self.sharedInterfaceNames:
            self._sharedInterfaces = ()
            return
        if self.sharedInterfaceNames == ALL_IMPLEMENTED_DB:
            I = implementedBy(self.sharedItem.__class__)
            L = list(I)
            T = tuple(L)
            self._sharedInterfaces = T
        else:
            self._sharedInterfaces = tuple(map(namedAny, self.sharedInterfaceNames.split(u',')))

    def getProxy(self):
        return SharedProxy(self.sharedItem, self.sharedInterfaces)


def upgradeShare1to2(oldShare):
    sharedInterfaces = []
    attrs = set(oldShare.sharedAttributeNames.split(u','))
    for iface in implementedBy(oldShare.sharedItem.__class__):
        if set(iface) == attrs or attrs == set('*'):
            sharedInterfaces.append(iface)

    newShare = oldShare.upgradeVersion('sharing_share', 1, 2,
                                       shareID=oldShare.shareID,
                                       sharedItem=oldShare.sharedItem,
                                       sharedTo=oldShare.sharedTo,
                                       sharedInterfaces=sharedInterfaces)
    return newShare


registerUpgrader(upgradeShare1to2, 'sharing_share', 1, 2)

def genShareID(store):
    return unicode(os.urandom(16).encode('hex'), 'ascii')

def getEveryoneRole(store):
    """
    Get a base 'Everyone' role for this store, which is the role that every user has no matter what.
    """
    return store.findOrCreate(Role, externalID=u'Everyone')

def getAuthenticatedRole(store):
    """
    Get the base 'Authenticated' role for this store, which is the role that
    every user with a proper username has, no matter what.
    """
    def tx():
        def addToEveryone(newAuthenticatedRole):
            newAuthenticatedRole.becomeMemberOf(getEveryoneRole(store))
            return newAuthenticatedRole
        return store.findOrCreate(Role, addToEveryone, externalID=u'Authenticated')
    return store.transact(tx)

def getPrimaryRole(store, primaryRoleName, createIfNotFound=False):
    """
    Get Role object corresponding to an identifier name.  If the role name
    passed is the empty string, it is assumed that the user is not
    authenticated, and the 'Everybody' role is primary.  If the role name
    passed is non-empty, but has no corresponding role, the 'Authenticated'
    role - which is a member of 'Everybody' - is primary.  Finally, a specific
    role can be primary if one exists for the user's given credentials, that
    will automatically always be a member of 'Authenticated', and by extension,
    of 'Everybody'.
    """
    if not primaryRoleName:
        return getEveryoneRole(store)
    ff = store.findUnique(Role, Role.externalID == primaryRoleName, default=None)
    if ff is not None:
        return ff
    authRole = getAuthenticatedRole(store)
    if createIfNotFound:
        role = Role(store=store,
                    externalID=primaryRoleName)
        role.becomeMemberOf(authRole)
        return role
    return authRole


def getSelfRole(store):
    """
    Retrieve the Role which corresponds to the user to whom the given store
    belongs.
    """
    for (localpart, domain) in userbase.getAccountNames(store):
        return getPrimaryRole(store, u'%s@%s' % (localpart, domain), createIfNotFound=True)
    raise ValueError("Cannot get self-role for unnamed account.")


def shareItem(sharedItem, toRole=None, toName=None, shareID=None,
              interfaces=ALL_IMPLEMENTED):
    assert sharedItem.store is not None
    if shareID is None:
        shareID = genShareID(sharedItem.store)
    if toRole is None:
        if toName is not None:
            toRole = getPrimaryRole(sharedItem.store, toName, True)
        else:
            toRole = getEveryoneRole(sharedItem.store)
    else:
        assert toName is None
    assert sharedItem.store is toRole.store
    return Share(store=sharedItem.store,
                 shareID=shareID,
                 sharedItem=sharedItem,
                 sharedTo=toRole,
                 sharedInterfaces=interfaces)

def getShare(store, role, shareID):
    for r in role.allRoles():
        share = store.findFirst(Share, AND(Share.shareID == shareID, Share.sharedTo == r))
        if share is not None:
            return share.getProxy()
    raise NoSuchShare()

def itemFromProxy(obj):
    return object.__getattribute__(obj, '_sharedItem')

def unShare(sharedItem):
    """
    Remove all instances of this item from public or shared view.
    """
    sharedItem.store.query(Share, Share.sharedItem == sharedItem).deleteFromStore()

def randomEarlyShared(store, role):
    """
    If there are no explicitly-published public index pages to display, find a
    shared item to present to the user as first.
    """
    for r in role.allRoles():
        share = store.findFirst(Share, Share.sharedTo == r,
                                sort=Share.storeID.ascending)
        if share is not None:
            return share.sharedItem
    raise NoSuchShare("Why, that user hasn't shared anything at all!")

