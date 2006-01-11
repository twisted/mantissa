
from zope.interface import implements

from nevow import inevow, url, rend

from xmantissa import ixmantissa
from xmantissa import sharing
from xmantissa import publicresource

class UserIndexPage(object):
    implements(inevow.IResource)

    def __init__(self, loginSystem):
        self.loginSystem = loginSystem

    def locateChild(self, ctx, segments):
        user = segments[0]
        host = inevow.IRequest(ctx).getHeader('host')
        parts = unicode(user).split(u'@')
        if len(parts) == 1:
            parts.append(host.decode('ascii'))
        result = self.loginSystem.accountByAddress(*parts)
        if result is not None:
            return SharingIndex(result.avatars.open()), segments[1:]
        return rend.NotFound

    def renderHTTP(self, ctx):
        return 'Keep trying.  You are almost there.'



class SharingIndex(object):
    implements(inevow.IResource, ixmantissa.ICustomizable)

    def __init__(self, userStore, avatarName=None):
        self.userStore = userStore
        self.avatarName = avatarName

    def customizeFor(self, avatarName):
        return SharingIndex(self.userStore, avatarName)

    def renderHTTP(self, ctx):
        return url.URL.fromContext(ctx).child('')

    def locateChild(self, ctx, segments):
        shareID = segments[0].decode('ascii')

        role = sharing.getPrimaryRole(self.userStore, self.avatarName)

        try:
            #### import pdb; pdb.Pdb().set_trace()
            sharedItem = sharing.getShare(self.userStore, role, shareID)
        except sharing.NoSuchShare:
            return rend.NotFound
        fragment = ixmantissa.INavigableFragment(sharedItem)
        # If you're shared, you MUST implement customizeFor (maybe this should
        # be a different interface? ugh.
        fragment = fragment.customizeFor(self.avatarName)
        if fragment.fragmentName is not None:
            fragDocFactory = ixmantissa.IWebTranslator(
                self.userStore).getDocFactory(fragment.fragmentName, None)
            if fragDocFactory is not None:
                fragment.docFactory = fragDocFactory
        result = publicresource.PublicAthenaLivePage(fragment,
                                                     forUser=self.avatarName)
        return result, segments[1:]
