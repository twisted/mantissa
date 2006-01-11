# -*- test-case-name: xmantissa.test.test_sharing -*-

# XXX TODO: 'Q2Q Verified' status of connection, or status, or role, or
# ... something, to distinguish between casual (i.e. spam-prevention) and real
# (i.e. accounting-database-access) security

import os

from zope.interface import directlyProvides, providedBy
from zope.interface.advice import addClassAdvisor

from axiom import userbase
from axiom.item import Item
from axiom.attributes import reference, text, AND, inmemory


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

def allow(*attributes):
    """
    Provide the sharing system with a list of allowed attributes, by decorating
    a class as with implements().  For example::

        class FirearmHelper:
            def shoot(self):
                ...

        class Shotgun(Item, Container):
            ...
            bullets = integer()
            def reload(self):
                ...
            allow(bullets,
                  reload,
                  'shoot')

    @param attributes: a list of function objects, C{SQLAttribute}s, and strings,
    naming the attributes to be shared.
    """
    attributeNames = []
    for attribute in attributes:
        if not isinstance(attribute, str):
            for attrAttr in ['func_name', 'attrname']:
                if hasattr(attribute, attrAttr):
                    attribute = getattr(attribute, attrAttr)
                    break
            else:
                raise TypeError('Attempted to allow insufficiently descriptive attribute type: ' + repr(attribute))
        assert isinstance(attribute, str)
        attributeNames.append(attribute)
    def addSharedAttributes(cls):
        cls.sharedAttributes = tuple(getattr(cls, 'sharedAttributes', ())) + tuple(attributeNames)
        return cls
    addClassAdvisor(addSharedAttributes)


def _getSharedItemAndAttributes(sharedProxy):
    # __providedBy__ is included so that adaptation will work as ... expected.
    # Maybe XXX TODO: add the ability to explicitly set a list of interfaces
    # provided by proxies?
    sharedAttributes = super(SharedProxy, sharedProxy).__getattribute__('_sharedAttributes')
    sharedAttributes = sharedAttributes + ('__providedBy__',)
    sharedItem = super(SharedProxy, sharedProxy).__getattribute__('_sharedItem')
    return sharedAttributes, sharedItem


class SharedProxy(object):

    def __init__(self, sharedItem, sharedAttributes):
        super(SharedProxy, self).__setattr__('_sharedItem', sharedItem)
        super(SharedProxy, self).__setattr__('_sharedAttributes', sharedAttributes)
        # Make me look *exactly* like the item I am proxying for, at least for
        # the purposes of adaptation
        # directlyProvides(self, providedBy(sharedItem))


    def __repr__(self):
        return 'SharedProxy(%r, %r)' % tuple(reversed(_getSharedItemAndAttributes(self)))


    def __getattribute__(self, name):
        sharedAttributes, sharedItem = _getSharedItemAndAttributes(self)
        if name == 'sharedAttributes':
            return sharedAttributes
        if name in sharedAttributes:
            return getattr(sharedItem, name)
        raise AttributeError(name)


    def __setattr__(self, name, value):
        sharedAttributes, sharedItem = _getSharedItemAndAttributes(self)
        if name in sharedAttributes:
            setattr(sharedItem, name, value)


    def __delattr__(self, name):
        sharedAttributes, sharedItem = _getSharedItemAndAttributes(self)
        if name in sharedAttributes:
            delattr(sharedItem, name)


ALL_SHARED_ATTRIBUTES_DB = u'*'

ALL_SHARED_ATTRIBUTES = object()


class Share(Item):
    schemaVersion = 1
    typeName = 'sharing_share'

    shareID = text(allowNone=False)
    sharedItem = reference(allowNone=False)
    sharedTo = reference(allowNone=False)

    sharedAttributeNames = text(allowNone=False)
    _sharedAttributes = inmemory()

    def __init__(self, **kw):
        sa = kw.pop('sharedAttributes')
        if sa is ALL_SHARED_ATTRIBUTES:
            san = ALL_SHARED_ATTRIBUTES_DB
        else:
            san = u','.join(sa)
        kw['sharedAttributeNames'] = san
        super(Share, self).__init__(**kw)


    def sharedAttributes():
        def get(self):
            return self._sharedAttributes
        # Maybe one day someone will want this, but it might be incorrect.
        # Think hard about it before uncommenting...

#         def set(self, newValue):
#             self._sharedAttributes = tuple(newValue)
#             self.sharedAttributeNames = u','.join(self.sharedAttributes)
        return get,
    sharedAttributes = property(*sharedAttributes())


    def activate(self):
        if self.sharedAttributeNames == ALL_SHARED_ATTRIBUTES_DB:
            self._sharedAttributes = self.sharedItem.sharedAttributes
        else:
            self._sharedAttributes = tuple(self.sharedAttributeNames.split(u','))

    def getProxy(self):
        return SharedProxy(self.sharedItem, self.sharedAttributes)


def shareAttributesWith():
    pass

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
              attributeNames=ALL_SHARED_ATTRIBUTES):
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
                 sharedAttributes=attributeNames)

def getShare(store, role, shareID):
    for r in role.allRoles():
        share = store.findFirst(Share, AND(Share.shareID == shareID, Share.sharedTo == r))
        if share is not None:
            return share.getProxy()
    raise NoSuchShare()

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

