
from twisted.python import filepath
from twisted.trial import unittest
from twisted.application import internet, service

from nevow import appserver, loaders, tags, url, rend, static, athena

from xmantissa import webform

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
            tags.head[tags.directive('liveglue'),
                      tags.link(rel='stylesheet', href='static/livetest.css')],
            tags.body[tags.directive('testSuite'), tags.div(id='nevow-log')]]])

    def __init__(self, testFragments):
        super(TestFramework, self).__init__(None, None)
        self.testFragments = testFragments

        here = filepath.FilePath(__file__).parent()
        m = here.parent().child('static').child('js')
        n = filepath.FilePath(athena.__file__).parent().child('athena.js')
        self.jsModules.mapping.update({
            'Mantissa': m.child('mantissa.js').path,
            'Mantissa.Forms': m.child('forms.js').path,
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
        tags.div(_class='test-unrun', render=tags.directive('liveFragment'))[
            tags.form(action='#',
                      onsubmit='Mantissa.Test.Forms.get(this).run(); return false;')[
                webform.Form([
                    ('argument',
                     webform.TEXT_INPUT,
                     unicode,
                     'A text input field: ',
                     u'hello world')])]])

    allowedMethods = {'submit': True}
    def submit(self, argument):
        self.assertEquals(argument, [u'hello world'])


def makeService():
    site = appserver.NevowSite(TestFrameworkRoot([Forms()]))
    return internet.TCPServer(8080, site)

application = service.Application('Forms LiveTest')
makeService().setServiceParent(application)
