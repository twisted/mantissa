
"""
Tests for L{xmantissa.liveform}.
"""

from xml.dom.minidom import parseString

from zope.interface import implements

from twisted.trial.unittest import TestCase

from nevow.page import renderer
from nevow.tags import directive, div, span
from nevow.loaders import stan
from nevow.flat import flatten
from nevow.inevow import IQ

from xmantissa.liveform import (
    FORM_INPUT, TEXT_INPUT, PASSWORD_INPUT, CHOICE_INPUT, Parameter,
    TextParameterView, PasswordParameterView, ChoiceParameter,
    ChoiceParameterView, Option, OptionView, LiveForm,
    ListParameter,)

from xmantissa.webtheme import getLoader
from xmantissa.test.rendertools import TagTestingMixin, renderLiveFragment
from xmantissa.ixmantissa import IParameterView


class StubView(object):
    """
    Behaviorless implementation of L{IParameterView} used where such an object
    is required by tests.
    """
    implements(IParameterView)

    patternName = 'text'

    def setDefaultTemplate(self, tag):
        """
        Ignore the default template tag.
        """



class ParameterTestsMixin:
    """
    Mixin defining various tests common to different parameter view objects.
    """
    def viewFactory(self, parameter):
        """
        Instantiate a view object for the given parameter.
        """
        raise NotImplementedError("%s did not implement viewFactory")


    def test_comparison(self):
        """
        Parameter view objects should compare equal to other view objects of
        the same type which wrap the same underlying parameter object.
        """
        self.assertTrue(self.viewFactory(self.param) == self.viewFactory(self.param))
        self.assertFalse(self.viewFactory(self.param) != self.viewFactory(self.param))
        self.assertFalse(self.viewFactory(self.param) == object())
        self.assertTrue(self.viewFactory(self.param) != object())


    def test_name(self):
        """
        The I{name} renderer of the view object should render the name of the
        L{Parameter} it wraps as a child of the tag it is given.
        """
        tag = div()
        renderedName = renderer.get(self.view, 'name')(None, tag)
        self.assertTag(tag, 'div', {}, [self.name])


    def test_label(self):
        """
        L{TextParameterView.label} should render the label of the L{Parameter}
        it wraps as a child of the tag it is given.
        """
        tag = div()
        renderedLabel = renderer.get(self.view, 'label')(None, tag)
        self.assertTag(tag, 'div', {}, [self.label])


    def test_withoutLabel(self):
        """
        L{ChoiceParameterView.label} should do nothing if the wrapped
        L{ChoiceParameter} has no label.
        """
        tag = div()
        self.param.label = None
        renderedOptions = renderer.get(self.view, 'label')(None, tag)
        self.assertTag(renderedOptions, 'div', {}, [])


    def _defaultRenderTest(self, fragmentName):
        loader = getLoader(fragmentName)
        document = loader.load()
        patternName = self.view.patternName + '-input-container'
        pattern = IQ(document).onePattern(patternName)
        self.view.setDefaultTemplate(pattern)
        html = flatten(self.view)

        # If it parses, well, that's the best we can do, given an arbitrary
        # template.
        document = parseString(html)


    def test_renderWithDefault(self):
        """
        The parameter view should be renderable using the default template.
        """
        return self._defaultRenderTest('liveform')


    def test_renderWithCompact(self):
        """
        The parameter view should be renderable using the compact template.
        """
        return self._defaultRenderTest('liveform-compact')



class TextLikeParameterViewTestsMixin:
    """
    Mixin defining tests for parameter views which are simple text fields.
    """
    def type():
        def get(self):
            raise AttributeError("%s did not define the type attribute")
        return get,
    type = property(*type())

    name = u'param name'
    label = u'param label'
    coercer = lambda value: value
    description = u'param desc'
    default = u'param default value'


    def setUp(self):
        """
        Create a L{Parameter} and a L{TextParameterView} wrapped around it.
        """
        self.param = Parameter(
            self.name, self.type, self.coercer, self.label, self.description,
            self.default)
        self.view = self.viewFactory(self.param)


    def test_default(self):
        """
        L{TextParameterView.value} should render the default value of the
        L{Parameter} it wraps as a child of the tag it is given.
        """
        tag = div()
        renderedDefault = renderer.get(self.view, 'default')(None, tag)
        self.assertTag(tag, 'div', {}, [self.default])


    def test_withoutDefault(self):
        """
        L{TextParameterView.value} should leave the tag it is given unchanged
        if the L{Parameter} it wraps has a C{None} default.
        """
        tag = div()
        self.param.default = None
        renderedDefault = renderer.get(self.view, 'default')(None, tag)
        self.assertTag(tag, 'div', {}, [])


    def test_description(self):
        """
        L{TextParameterView.description} should render the description of the
        L{Parameter} it wraps as a child of the tag it is given.
        """
        tag = div()
        renderedDescription = renderer.get(self.view, 'description')(None, tag)
        self.assertTag(tag, 'div', {}, [self.description])


    def test_withoutDescription(self):
        """
        L{TextParameterView.description} should leave the tag it is given
        unchanged if the L{Parameter} it wraps has no description.
        """
        tag = div()
        self.param.description = None
        renderedDescription = renderer.get(self.view, 'description')(None, tag)
        self.assertTag(tag, 'div', {}, [])


    def test_renderCompletely(self):
        """
        L{TextParameterView} should be renderable in the usual Nevow manner.
        """
        self.view.docFactory = stan(div[
                div(render=directive('name')),
                div(render=directive('label')),
                div(render=directive('default')),
                div(render=directive('description'))])
        html = flatten(self.view)
        self.assertEqual(
            html,
            '<div><div>param name</div><div>param label</div>'
            '<div>param default value</div><div>param desc</div></div>')



class TextParameterViewTests(TextLikeParameterViewTestsMixin,
                             TestCase, ParameterTestsMixin,
                             TagTestingMixin):
    """
    Tests for the view generation code for C{TEXT_INPUT} L{Parameter}
    instances.
    """
    type = TEXT_INPUT
    viewFactory = TextParameterView



class PasswordParameterViewTests(TextLikeParameterViewTestsMixin,
                                 TestCase, ParameterTestsMixin,
                                 TagTestingMixin):
    """
    Tests for the view generation code for C{PASSWORD_INPUT} L{Parameter}
    instances.
    """
    type = PASSWORD_INPUT
    viewFactory = PasswordParameterView



class ChoiceParameterTests(TestCase, ParameterTestsMixin, TagTestingMixin):
    """
    Tests for the view generation code for C{CHOICE_INPUT} L{Parameter}
    instances.
    """
    viewFactory = ChoiceParameterView

    def setUp(self):
        """
        Create a L{Parameter} and a L{ChoiceParameterView} wrapped around it.
        """
        self.type = CHOICE_INPUT
        self.name = u'choice name'
        self.choices = [
            Option(u'description one', u'value one', False),
            Option(u'description two', u'value two', False)]
        self.label = u'choice label'
        self.description = u'choice description'
        self.multiple = False
        self.param = ChoiceParameter(
            self.name, self.choices, self.label, self.description,
            self.multiple)
        self.view = self.viewFactory(self.param)


    def test_multiple(self):
        """
        L{ChoiceParameterView.multiple} should render the multiple attribute on
        the tag it is passed if the wrapped L{ChoiceParameter} is a
        L{MULTI_CHOICE_INPUT}.
        """
        tag = div()
        self.param.multiple = True
        renderedSelect = renderer.get(self.view, 'multiple')(None, tag)
        self.assertTag(tag, 'div', {'multiple': 'multiple'}, [])


    def test_single(self):
        """
        L{ChoiceParameterView.multiple} should not render the multiple
        attribute on the tag it is passed if the wrapped L{ChoiceParameter} is
        a L{CHOICE_INPUT}.
        """
        tag = div()
        renderedSelect = renderer.get(self.view, 'multiple')(None, tag)
        self.assertTag(tag, 'div', {}, [])


    def test_options(self):
        """
        L{ChoiceParameterView.options} should load the I{option} pattern from
        the tag it is passed and add copies of it as children to the tag for
        all of the options passed to L{ChoiceParameterView.__init__}.
        """
        option = span(pattern='option')
        tag = div[option]
        renderedOptions = renderer.get(self.view, 'options')(None, tag)
        self.assertEqual(
            renderedOptions.children[1:],
            [OptionView(index, c, None)
             for (index, c)
             in enumerate(self.choices)])


    def test_description(self):
        """
        L{ChoiceParameterView.description} should add the description of the
        wrapped L{ChoiceParameter} to the tag it is passed.
        """
        tag = div()
        renderedOptions = renderer.get(self.view, 'description')(None, tag)
        self.assertTag(renderedOptions, 'div', {}, [self.description])


    def test_withoutDescription(self):
        """
        L{ChoiceParameterView.description} should do nothing if the wrapped
        L{ChoiceParameter} has no description.
        """
        tag = div()
        self.param.description = None
        renderedOptions = renderer.get(self.view, 'description')(None, tag)
        self.assertTag(renderedOptions, 'div', {}, [])



class OptionTests(TestCase, TagTestingMixin):
    """
    Tests for the view generation code for a single choice, L{OptionView}.
    """
    simpleOptionTag = stan(div[
            div(render=directive('description')),
            div(render=directive('value')),
            div(render=directive('index')),
            div(render=directive('selected'))])

    def setUp(self):
        """
        Create an L{Option} and an L{OptionView} wrapped around it.
        """
        self.description = u'option description'
        self.value = u'option value'
        self.selected = True
        self.option = Option(self.description, self.value, self.selected)
        self.index = 3
        self.view = OptionView(self.index, self.option, self.simpleOptionTag)


    def test_description(self):
        """
        L{OptionView.description} should add the description of the option it
        wraps as a child to the tag it is passed.
        """
        tag = div()
        renderedDescription = renderer.get(self.view, 'description')(None, tag)
        self.assertTag(renderedDescription, 'div', {}, [self.description])


    def test_value(self):
        """
        L{OptionView.value} should add the value of the option it wraps as a
        child to the tag it is passed.
        """
        tag = div()
        renderedValue = renderer.get(self.view, 'value')(None, tag)
        self.assertTag(renderedValue, 'div', {}, [self.value])


    def test_index(self):
        """
        L{OptionView.index} should add the index passed to
        L{OptionView.__init__} to the tag it is passed.
        """
        tag = div()
        renderedIndex = renderer.get(self.view, 'index')(None, tag)
        self.assertTag(renderedIndex, 'div', {}, [self.index])


    def test_selected(self):
        """
        L{OptionView.selected} should add a I{selected} attribute to the tag it
        is passed if the option it wraps is selected.
        """
        tag = div()
        renderedValue = renderer.get(self.view, 'selected')(None, tag)
        self.assertTag(renderedValue, 'div', {'selected': 'selected'}, [])


    def test_notSelected(self):
        """
        L{OptionView.selected} should not add a I{selected} attribute to the
        tag it is passed if the option it wraps is not selected.
        """
        self.option.selected = False
        tag = div()
        renderedValue = renderer.get(self.view, 'selected')(None, tag)
        self.assertTag(renderedValue, 'div', {}, [])


    def test_renderCompletely(self):
        """
        L{ChoiceParameterView} should be renderable in the usual Nevow manner.
        """
        html = flatten(self.view)
        self.assertEqual(
            html,
            '<div><div>option description</div><div>option value</div>'
            '<div>3</div><div selected="selected"></div></div>')



class LiveFormTests(TestCase, TagTestingMixin):
    """
    Tests for the form generation code in L{LiveForm}.
    """
    # Minimal tag which can be used with the form renderer.  Classes are only
    # used to tell nodes apart in the tests.
    simpleLiveFormTag = div[
        span(pattern='text-input-container'),
        span(pattern='password-input-container'),
        span(pattern='liveform', _class='liveform-container'),
        span(pattern='subform', _class='subform-container')]


    def test_compact(self):
        """
        L{LiveForm.compact} should replace the existing C{docFactory} with one
        for the I{compact} version of the live form template.
        """
        form = LiveForm(None, [])
        form.compact()
        self.assertTrue(form.docFactory.template.endswith('/liveform-compact.html'))


    def test_recursiveCompact(self):
        """
        L{LiveForm.compact} should also call C{compact} on all of its subforms.
        """
        class StubChild(object):
            compacted = False
            def compact(self):
                self.compacted = True
        child = StubChild()
        form = LiveForm(None, [Parameter('foo', FORM_INPUT, child),
                               Parameter('bar', TEXT_INPUT, int),
                               ListParameter('baz', None, 3),
                               ChoiceParameter('quux', [])])
        form.compact()
        self.assertTrue(child.compacted)


    def test_descriptionSlot(self):
        """
        L{LiveForm.form} should fill the I{description} slot on the tag it is
        passed with the description of the form.
        """
        description = u"the form description"
        formFragment = LiveForm(None, [], description)
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(formTag.slotData['description'], description)


    def test_formSlotOuter(self):
        """
        When it is not nested inside another form, L{LiveForm.form} should fill
        the I{form} slot on the tag with the tag's I{liveform} pattern.
        """
        def submit(**kw):
            pass
        formFragment = LiveForm(submit, [])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertTag(
            formTag.slotData['form'], 'span', {'class': 'liveform-container'},
            [])


    def test_formSlotInner(self):
        """
        When it has a sub-form name, L{LiveForm.form} should fill the I{form}
        slot on the tag with the tag's I{subform} pattern.
        """
        def submit(**kw):
            pass
        formFragment = LiveForm(submit, [])
        formFragment.subFormName = 'test-subform'
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertTag(
            formTag.slotData['form'], 'span', {'class': 'subform-container'},
            [])


    def test_noParameters(self):
        """
        When there are no parameters, L{LiveForm.form} should fill the
        I{inputs} slot on the tag it uses to fill the I{form} slot with an
        empty list.
        """
        def submit(**kw):
            pass
        formFragment = LiveForm(submit, [])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(formTag.slotData['form'].slotData['inputs'], [])


    def test_parameterViewOverride(self):
        """
        L{LiveForm.form} should use the C{view} attribute of parameter objects,
        if it is not C{None}, to fill the I{inputs} slot on the tag it uses to
        fill the I{form} slot.
        """
        def submit(**kw):
            pass

        name = u'param name'
        label = u'param label'
        type = TEXT_INPUT
        coercer = lambda value: value
        description = u'param desc'
        default = u'param default value'

        view = StubView()
        views = {}
        viewFactory = views.get
        param = Parameter(
            name, type, coercer, label, description, default, viewFactory)
        views[param] = view

        formFragment = LiveForm(submit, [param])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(
            formTag.slotData['form'].slotData['inputs'],
            [view])


    def test_individualTextParameter(self):
        """
        L{LiveForm.form} should fill the I{inputs} slot on the tag it uses to
        fill the I{form} slot with a list consisting of one
        L{TextParameterView} when the L{LiveForm} is created with one
        C{TEXT_INPUT} L{Parameter}.
        """
        def submit(**kw):
            pass

        name = u'param name'
        label = u'param label'
        type = TEXT_INPUT
        coercer = lambda value: value
        description = u'param desc'
        default = u'param default value'
        param = Parameter(
            name, type, coercer, label, description, default)

        formFragment = LiveForm(submit, [param])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(
            formTag.slotData['form'].slotData['inputs'],
            [TextParameterView(param)])


    def test_individualPasswordParameter(self):
        """
        L{LiveForm.form} should fill the I{inputs} slot of the tag it uses to
        fill the I{form} slot with a list consisting of one
        L{TextParameterView} when the L{LiveForm} is created with one
        C{PASSWORD_INPUT} L{Parameter}.
        """
        def submit(**kw):
            pass

        name = u'param name'
        label = u'param label'
        type = PASSWORD_INPUT
        coercer = lambda value: value
        description = u'param desc'
        default = u'param default value'
        param = Parameter(
            name, type, coercer, label, description, default)

        formFragment = LiveForm(submit, [param])
        formTag = formFragment.form(None, self.simpleLiveFormTag)
        self.assertEqual(
            formTag.slotData['form'].slotData['inputs'],
            [PasswordParameterView(param)])


    def test_liveformTemplateStructuredCorrectly(self):
        """
        When a L{LiveForm} is rendered using the default template, the form
        contents should end up inside the I{form} tag.

        As I understand it, this is a necessary condition for the resulting
        html form to operate properly.  However, due to the complex behavior of
        the HTML (or even XHTML) DOM and the inscrutability of the various
        specific implementations of it, it is not entirely unlikely that my
        understanding is, in some way, flawed.  If you know better, and believe
        this test to be in error, supplying a superior test or simply deleting
        this one may not be out of the question. -exarkun
        """
        def submit(**kw):
            pass

        name = u'param name'
        label = u'param label'
        type = PASSWORD_INPUT
        coercer = lambda value: value
        description = u'param desc'
        default = u'param default value'
        param = Parameter(
            name, type, coercer, label, description, default)

        formFragment = LiveForm(submit, [param])
        html = renderLiveFragment(formFragment)
        document = parseString(html)
        forms = document.getElementsByTagName('form')
        self.assertEqual(len(forms), 1)
        inputs = forms[0].getElementsByTagName('input')
        self.assertTrue(len(inputs) >= 1)
