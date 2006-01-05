
from twisted.python import filepath
from twisted.trial import unittest
from twisted.application import internet, service

from nevow import appserver, loaders, tags, url, rend, static, athena

from xmantissa import liveform

DOCTYPE_XHTML = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'

class TestSuite(athena.LiveFragment):
    jsClass = u'Mantissa.Test.TestSuite'

    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveFragment'))[
            tags.form(action='#', onsubmit='Mantissa.Test.TestSuite.get(this).run(); return false;')[
                tags.input(type='submit', value='Run Tests')],
            tags.div['Tests Passed: ', tags.span(_class='test-success-count')[0]],
            tags.div['Tests Failed: ', tags.span(_class='test-failure-count')[0]],
            tags.invisible(render=tags.directive('testFragments'))])

    def __init__(self, page, testFragments):
        super(TestSuite, self).__init__()
        self.page = page
        self.testFragments = testFragments


    def render_testFragments(self, ctx, data):
        for f in self.testFragments:
            f.page = self.page
            yield f



class TestFramework(athena.LivePage):
    addSlash = True
    docFactory = loaders.stan([
        tags.xml(DOCTYPE_XHTML),
        tags.html[
            tags.head(render=tags.directive('liveglue'))[
                tags.link(rel='stylesheet', href='static/livetest.css')],
            tags.body(render=tags.directive('testSuite'))[
                tags.div(id='nevow-log')]]])

    def __init__(self, testFragments):
        super(TestFramework, self).__init__(None, None, jsModuleRoot=url.here.child('jsmodule'))
        self.testFragments = testFragments

        here = filepath.FilePath(__file__).parent()
        m = here.parent().child('static').child('js')
        n = filepath.FilePath(athena.__file__).parent().child('athena.js')
        self.jsModules.mapping.update({
            'Mantissa.Test': here.child('livetest.js').path,
            })


    def render_testSuite(self, ctx, data):
        return TestSuite(self, self.testFragments)


    def childFactory(self, ctx, name):
        try:
            n = int(name)
        except ValueError:
            pass
        else:
            try:
                f = self.testFragments[n]
            except IndexError:
                pass
            else:
                return static.Data(f.script, 'text/javascript')
        return super(TestFramework, self).childFactory(ctx, name)


    def child_static(self, ctx):
        return static.File(filepath.FilePath(__file__).parent().child('livetest-static').path)



class TestFrameworkRoot(rend.Page):
    def child_app(self, ctx):
        return TestFramework(self.original)
    child_ = url.URL.fromString('/app')



class Forms(athena.LiveFragment, unittest.TestCase):
    jsClass = u'Mantissa.Test.Forms'

    docFactory = loaders.stan(
        tags.div(_class='test-unrun',
                 render=tags.directive('liveFragment'))[
            tags.invisible(render=tags.directive('hello_form'))])

    def submit(self, argument):
        self.assertEquals(argument, u'hello world')

    def render_hello_form(self, ctx, data):
        f = liveform.LiveForm(
            self.submit,
            [liveform.Parameter('argument',
                                liveform.TEXT_INPUT,
                                unicode,
                                'A text input field: ',
                                u'hello world')])
        f.page = self.page
        return ctx.tag[f]

SPECIAL = object() # guaranteed to fuck up JSON if it ever gets there by
                   # accident.

class Traverse(athena.LiveFragment, unittest.TestCase):
    jsClass = u'Mantissa.Test.Traverse'

    docFactory = loaders.stan(
        tags.div(_class='test-unrun',
                 render=tags.directive('liveFragment'))[
            tags.invisible(render=tags.directive('hello_form'))])

    def submit(self, argument, group):
        self.assertEquals(argument, u'hello world')
        self.assertEquals(group, SPECIAL)

    def paramfilter(self, param1):
        self.assertEquals(param1, u'goodbye world')
        return SPECIAL

    def render_hello_form(self, ctx, data):
        f = liveform.LiveForm(
            self.submit,
            [liveform.Parameter('argument',
                                liveform.TEXT_INPUT,
                                unicode,
                                'A text input field: ',
                                u'hello world'),
             liveform.Parameter('group',
                                liveform.FORM_INPUT,
                                liveform.LiveForm(self.paramfilter,
                                                  [liveform.Parameter
                                                   ('param1',
                                                    liveform.TEXT_INPUT,
                                                    unicode,
                                                    'Another input field: ',
                                                    u'goodbye world')]),
                                'A form input group: ',
                                )])
        f.page = self.page
        return ctx.tag[f]


def makeService():
    site = appserver.NevowSite(TestFrameworkRoot([Forms(),
                                                  Traverse()]))
    return internet.TCPServer(8080, site)

application = service.Application('Forms LiveTest')
makeService().setServiceParent(application)
