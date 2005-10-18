from nevow import rend, livepage
from xmantissa.webtheme import getAllThemes
from xmantissa.ixmantissa import IStaticShellContent

def getLoader(n):
    # TODO: implement PublicApplication (?) in webapp.py, so we can make sure
    # that these go in the right order.  Right now we've only got the one
    # though.
    for t in getAllThemes():
        fact = t.getDocFactory(n, None)
        if fact is not None:
            return fact

    raise RuntimeError("No loader for %r anywhere" % (n,))

class PublicPageMixin(object):
    fragment = None
    title = ''

    def render_navigation(self, ctx, data):
        return ""

    def render_search(self, ctx, data):
        return ""

    def render_title(self, ctx, data):
        return ctx.tag[self.title]

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

    def render_head(self, ctx, data):
        content = []
        for theme in getAllThemes():
            extra = theme.head()
            if extra is not None:
                content.append(extra)

        return ctx.tag[content]

class PublicPage(rend.Page, PublicPageMixin):
    def __init__(self, original, fragment, staticContent):
        super(PublicPage, self).__init__(original, docFactory=getLoader("public-shell"))
        self.fragment = fragment
        self.staticContent = staticContent

class PublicLivePage(livepage.LivePage, PublicPageMixin):
    def __init__(self, original, fragment, staticContent):
        super(PublicLivePage, self).__init__(original, docFactory=getLoader("public-shell"))
        self.fragment = fragment
        self.staticContent = staticContent

    def render_head(self, ctx, data):
        tag = super(PublicLivePage, self).render_head(ctx, data)
        return tag[livepage.glue]
