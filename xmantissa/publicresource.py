from nevow import rend, livepage, athena, tags, inevow

from xmantissa.webtheme import getLoader, getAllThemes

class PublicPageMixin(object):
    fragment = None
    title = ''
    username = None

    def render_navigation(self, ctx, data):
        return ""

    def render_search(self, ctx, data):
        return ""

    def render_title(self, ctx, data):
        return ctx.tag[self.title]

    def render_username(self, ctx, data):
        from xmantissa.signup import FreeTicketSignup

        if self.username is not None:
            return ctx.tag.fillSlots('username', self.username)

        IQ = inevow.IQ(self.docFactory)
        signupPattern = IQ.patternGenerator('signup')
        loginLinks = IQ.onePattern('login-links')

        signups = []
        for signup in self.store.query(FreeTicketSignup):
            signups.append(signupPattern.fillSlots(
                                'prompt', signup.prompt).fillSlots(
                                'url', '/' + signup.prefixURL))

        return ctx.tag.clear()[loginLinks.fillSlots('signups', signups)]

    def render_header(self, ctx, data):
        if self.staticContent is None:
            return ctx.tag

        header = self.staticContent.getHeader()
        if header is not None:
            return ctx.tag[header]
        else:
            return ctx.tag

    def render_footer(self, ctx, data):
        if self.staticContent is None:
            return ctx.tag

        header = self.staticContent.getFooter()
        if header is not None:
            return ctx.tag[header]
        else:
            return ctx.tag

    def render_content(self, ctx, data):
        return ctx.tag[self.fragment]

    def head(self):
        return None

    def render_head(self, ctx, data):
        content = list(t.head() for t in getAllThemes())
        content.append(self.head())
        return ctx.tag[filter(None, content)]

class PublicPage(PublicPageMixin, rend.Page):
    def __init__(self, original, store, fragment, staticContent, forUser):
        super(PublicPage, self).__init__(original, docFactory=getLoader("public-shell"))
        self.store = store
        self.fragment = fragment
        self.staticContent = staticContent
        if forUser is not None:
            assert isinstance(forUser, unicode), forUser
        self.username = forUser

class PublicLivePage(PublicPageMixin, livepage.LivePage):
    def __init__(self, original, store, fragment, staticContent, forUser):
        super(PublicLivePage, self).__init__(original, docFactory=getLoader("public-shell"))
        self.store = store
        self.fragment = fragment
        self.staticContent = staticContent
        if forUser is not None:
            assert isinstance(forUser, unicode), forUser
        self.username = forUser

    def render_head(self, ctx, data):
        tag = super(PublicLivePage, self).render_head(ctx, data)
        return tag[livepage.glue]

class PublicAthenaLivePage(PublicPageMixin, athena.LivePage):
    fragment = None
    def __init__(self, store, fragment, staticContent=None, forUser=None, *a, **k):
        self.store = store
        super(PublicAthenaLivePage, self).__init__(
            docFactory=getLoader("public-shell"),
            *a, **k)
        if fragment is not None:
            self.fragment = fragment
            # everybody who calls this has a different idea of what 'fragment'
            # means - let's just be super-lenient for now
            if getattr(fragment, 'setFragmentParent', False):
                fragment.setFragmentParent(self)
            else:
                fragment.page = self
        self.staticContent = staticContent
        if forUser is not None:
            assert isinstance(forUser, unicode), forUser
        self.username = forUser

    def render_head(self, ctx, data):
        ctx.tag[tags.invisible(render=tags.directive('liveglue'))]
        return PublicPageMixin.render_head(self, ctx, data)
