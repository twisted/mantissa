from nevow import rend, livepage
from xmantissa.webtheme import getAllThemes

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

    def render_title(self, ctx, data):
        return ""

    def render_topPanel(self, ctx, data):
        return ""

    def render_navigation(self, ctx, data):
        return ""

    def render_content(self, ctx, data):
        return ctx.tag[self.fragment]

    def render_head(self, ctx, data):
        content = []
        for theme in getAllThemes():
            extra = theme.head()
            if extra is not None:
                content.append(extra)
                break

        return ctx.tag[content]

class PublicPage(rend.Page, PublicPageMixin):
    def __init__(self, original, fragment):
        rend.Page.__init__(self, original, docFactory=getLoader("shell"))
        self.fragment = fragment

class PublicLivePage(livepage.LivePage, PublicPageMixin):
    def __init__(self, original, fragment):
        livepage.LivePage.__init__(self, original, docFactory=getLoader("shell"))
        self.fragment = fragment

    def render_head(self, ctx, data):
        tag = PublicPageMixin.render_head(self, ctx, data)
        return tag[livepage.glue]
