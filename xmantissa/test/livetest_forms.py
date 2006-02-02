import textwrap

from nevow import loaders, tags
from nevow.livetrial import testcase

from xmantissa import liveform

class TextInput(testcase.TestCase):
    jsClass = u'Mantissa.Test.Forms'

    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveTest'))[
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
        f.setFragmentParent(self)
        return ctx.tag[f]


class MultiTextInput(testcase.TestCase):
    jsClass = u'Mantissa.Test.Forms'

    docFactory = loaders.stan(
            tags.div(render=tags.directive('liveTest'))[
                tags.invisible(render=tags.directive('multiForm'))])

    def submit(self, sequence):
        self.assertEquals(sequence, [1, 2, 3, 4])

    def render_multiForm(self, ctx, data):
        f = liveform.LiveForm(
                self.submit,
                (liveform.ListParameter('sequence',
                                        int,
                                        4,
                                        'A bunch of text inputs: ',
                                        (1, 2, 3, 4)),))
        f.setFragmentParent(self)
        return ctx.tag[f]

class TextArea(testcase.TestCase):
    jsClass = u'Mantissa.Test.TextArea'

    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveTest'))[
            tags.invisible(render=tags.directive('textarea_form'))])


    defaultText = textwrap.dedent(u"""
    Come hither, sir.
    Though it be honest, it is never good
    To bring bad news. Give to a gracious message
    An host of tongues; but let ill tidings tell
    Themselves when they be felt.
    """).strip()

    def submit(self, argument):
        self.assertEquals(
            argument,
            self.defaultText)


    def render_textarea_form(self, ctx, data):
        f = liveform.LiveForm(
            self.submit,
            [liveform.Parameter('argument',
                                liveform.TEXTAREA_INPUT,
                                unicode,
                                'A text area: ',
                                self.defaultText)])
        f.setFragmentParent(self)
        return ctx.tag[f]



SPECIAL = object() # guaranteed to fuck up JSON if it ever gets there by
                   # accident.

class Traverse(testcase.TestCase):
    jsClass = u'Mantissa.Test.Traverse'

    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveTest'))[
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
