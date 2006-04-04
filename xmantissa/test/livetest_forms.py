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


class Select(testcase.TestCase):
    jsClass = u'Mantissa.Test.Select'

    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveTest'))[
            tags.invisible(render=tags.directive('select_form'))])

    def submit(self, argument):
        self.assertEquals(argument, u"apples")

    def render_select_form(self, ctx, data):
        # XXX No support for rendering these yet!
        f = liveform.LiveForm(
            self.submit,
            [liveform.Parameter('argument', None, unicode)])
        f.docFactory = loaders.stan(tags.form(render=tags.directive('liveFragment'))[
            tags.select(name="argument")[
                tags.option(value="apples")["apples"],
                tags.option(value="oranges")["oranges"]],
            tags.input(type='submit', render=tags.directive('submitbutton'))])
        f.setFragmentParent(self)
        return ctx.tag[f]


class Choice(testcase.TestCase):
    jsClass = u'Mantissa.Test.Choice'

    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveTest'))[
            tags.invisible(render=tags.directive('choice_form'))])

    def submit(self, argument):
        self.assertEquals(argument, 2)

    def render_choice_form(self, ctx, data):
        f = liveform.LiveForm(
            self.submit,
            [liveform.ChoiceParameter('argument', int,
                [('One', 1, False),
                 ('Two', 2, True),
                 ('Three', 3, False)])])
        f.setFragmentParent(self)
        return ctx.tag[f]


class ChoiceMultiple(testcase.TestCase):
    jsClass = u'Mantissa.Test.ChoiceMultiple'

    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveTest'))[
            tags.invisible(render=tags.directive('choice_form'))])

    def submit(self, argument):
        self.assertIn(1, argument)
        self.assertIn(3, argument)

    def render_choice_form(self, ctx, data):
        f = liveform.LiveForm(
            self.submit,
            [liveform.ChoiceParameter('argument', int,
                [('One', 1, True),
                 ('Two', 2, False),
                 ('Three', 3, True)],
                "Choosing mulitples from a list.", True)])
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
