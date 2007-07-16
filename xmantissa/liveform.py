# -*- test-case-name: xmantissa.test.test_liveform -*-

"""

XXX HYPER TURBO SUPER UNSTABLE DO NOT USE XXX

"""

import warnings

from zope.interface import implements

from twisted.python.components import registerAdapter

from epsilon.structlike import record

from nevow import inevow, tags, page, athena
from nevow.athena import expose
from nevow.page import Element, renderer
from nevow.loaders import stan

from xmantissa import webtheme
from xmantissa.fragmentutils import PatternDictionary, dictFillSlots
from xmantissa.ixmantissa import IParameterView


class InputError(athena.LivePageError):
    """
    Base class for all errors related to rejected input values.
    """
    jsClass = u'Mantissa.LiveForm.InputError'



TEXT_INPUT = 'text'
PASSWORD_INPUT = 'password'
TEXTAREA_INPUT = 'textarea'
FORM_INPUT = 'form'
RADIO_INPUT = 'radio'
CHECKBOX_INPUT = 'checkbox'
class Parameter(record('name type coercer label description default '
                       'viewFactory',
                       label=None,
                       description=None,
                       default=None,
                       viewFactory=IParameterView)):
    """
    @type name: C{unicode}
    @ivar name: A name uniquely identifying this parameter within a particular
        form.

    @ivar type: One of C{TEXT_INPUT}, C{PASSWORD_INPUT}, C{TEXTAREA_INPUT},
        C{FORM_INPUT}, C{RADIO_INPUT}, or C{CHECKBOX_INPUT} indicating the kind
        of input interface which will be presented for this parameter.

    @type description: C{unicode} or C{NoneType}
    @ivar description: An explanation of the meaning or purpose of this
        parameter which will be presented in the view, or C{None} if the user
        is intended to guess.

    @type default: C{unicode} or C{NoneType}
    @ivar default: A value which will be initially presented in the view as the
        value for this parameter, or C{None} if no such value is to be
        presented.

    @ivar viewFactory: A two-argument callable which returns an
        L{IParameterView} provider which will be used as the view for this
        parameter, if one can be provided.  It will be invoked with the
        parameter as the first argument and a default value as the second
        argument.  The default should be returned if no view can be provided
        for the given parameter.
    """
    def compact(self):
        """
        Compact FORM_INPUTs by calling their C{compact} method.  Don't do
        anything for other types of input.
        """
        if self.type == FORM_INPUT:
            self.coercer.compact()


MULTI_TEXT_INPUT = 'multi-text'

class ListParameter(record('name coercer count label description defaults '
                           'viewFactory',
                           label=None,
                           description=None,
                           defaults=None,
                           viewFactory=IParameterView)):

    type = MULTI_TEXT_INPUT
    def compact(self):
        """
        Don't do anything.
        """


CHOICE_INPUT = 'choice'
MULTI_CHOICE_INPUT = 'multi-choice'


class Option(record('description value selected')):
    """
    A single choice for a L{ChoiceParameter}.
    """


class ChoiceParameter(record('name choices label description multiple '
                             'viewFactory',
                             label=None,
                             description="",
                             multiple=False,
                             viewFactory=IParameterView)):
    """
    A choice parameter, represented by a <select> element in HTML.

    @ivar choices: A sequence of L{Option} instances (deprecated: a sequence of
        three-tuples giving the attributes of L{Option} instances).

    @ivar multiple: C{True} if multiple choice selections are allowed

    @ivar viewFactory: A two-argument callable which returns an
        L{IParameterView} provider which will be used as the view for this
        parameter, if one can be provided.  It will be invoked with the
        parameter as the first argument and a default value as the second
        argument.  The default should be returned if no view can be provided
        for the given parameter.
    """
    def __init__(self, *a, **kw):
        ChoiceParameter.__bases__[0].__init__(self, *a, **kw)
        if self.choices and isinstance(self.choices[0], tuple):
            warnings.warn(
                "Pass a list of Option instances to ChoiceParameter, "
                "not a list of tuples.",
                category=DeprecationWarning,
                stacklevel=2)
            self.choices = [Option(*o) for o in self.choices]

    def type(self):
        if self.multiple:
            return MULTI_CHOICE_INPUT
        return CHOICE_INPUT
    type = property(type)

    def coercer(self, value):
        if self.multiple:
            return tuple(self.choices[int(v)].value for v in value)
        return self.choices[int(value)].value

    def compact(self):
        """
        Don't do anything.
        """



class ConfigurationError(Exception):
    """
    User-specified configuration for a newly created Item was invalid or
    incomplete.
    """



class InvalidInput(Exception):
    """
    Data entered did not meet the requirements of the coercer.
    """



def _legacySpecialCases(form, patterns, parameter):
    """
    Create a view object for the given parameter.

    This function implements the remaining view construction logic which has
    not yet been converted to the C{viewFactory}-style expressed in
    L{_LiveFormMixin.form}.

    @type form: L{_LiveFormMixin}
    @param form: The form fragment which contains the given parameter.
    @type patterns: L{PatternDictionary}
    @type parameter: L{Parameter}, L{ChoiceParameter}, or L{ListParameter}.
    """
    p = patterns[parameter.type + '-input-container']

    if parameter.type == FORM_INPUT:
        # SUPER SPECIAL CASE
        subForm = parameter.coercer.asSubForm(parameter.name)
        subForm.setFragmentParent(form)
        p = p.fillSlots('input', subForm)
    elif parameter.type == TEXTAREA_INPUT:
        p = dictFillSlots(p, dict(label=parameter.label,
                                  name=parameter.name,
                                  value=parameter.default or ''))
    elif parameter.type == MULTI_TEXT_INPUT:
        subInputs = list()

        for i in xrange(parameter.count):
            subInputs.append(dictFillSlots(patterns['input'],
                                dict(name=parameter.name + '_' + str(i),
                                     type='text',
                                     value=parameter.defaults[i])))

        p = dictFillSlots(p, dict(label=parameter.label or parameter.name,
                                  inputs=subInputs))

    else:
        if parameter.default is not None:
            value = parameter.default
        else:
            value = ''

        if parameter.type == CHECKBOX_INPUT and parameter.default:
            inputPattern = 'checked-checkbox-input'
        else:
            inputPattern = 'input'

        p = dictFillSlots(
            p, dict(label=parameter.label or parameter.name,
                    input=dictFillSlots(patterns[inputPattern],
                                        dict(name=parameter.name,
                                             type=parameter.type,
                                             value=value))))

    p(**{'class' : 'liveform_'+parameter.name})

    if parameter.description:
        description = patterns['description'].fillSlots(
                           'description', parameter.description)
    else:
        description = ''

    return dictFillSlots(
        patterns['parameter-input'],
        dict(input=p, description=description))



class _LiveFormMixin(record('callable parameters description',
                            description=None)):
    jsClass = u'Mantissa.LiveForm.FormWidget'

    subFormName = None

    fragmentName = 'liveform'
    compactFragmentName = 'liveform-compact'

    def __init__(self, *a, **k):
        super(_LiveFormMixin, self).__init__(*a, **k)
        if self.docFactory is None:
            # Give subclasses a chance to assign their own docFactory.
            self.docFactory = webtheme.getLoader(self.fragmentName)


    def compact(self):
        """
        Switch to the compact variant of the live form template.

        By default, this will simply create a loader for the
        C{self.compactFragmentName} template and compact all of this form's
        parameters.
        """
        self.docFactory = webtheme.getLoader(self.compactFragmentName)
        for param in self.parameters:
            param.compact()


    def getInitialArguments(self):
        if self.subFormName:
            subFormName = self.subFormName.decode('utf-8')
        else:
            subFormName = None
        return (subFormName,)


    def asSubForm(self, name):
        self.subFormName = name
        return self


    def _getDescription(self):
        descr = self.description
        if descr is None:
            descr = self.callable.__name__
        return descr


    def submitbutton(self, request, tag):
        """
        Render an INPUT element of type SUBMIT which will post this form to the
        server.
        """
        return tags.input(type='submit',
                          name='__submit__',
                          value=self._getDescription())
    page.renderer(submitbutton)


    def render_submitbutton(self, ctx, data):
        return self.submitbutton(inevow.IRequest(ctx), ctx.tag)


    def render_liveFragment(self, ctx, data):
        return self.liveElement(inevow.IRequest(ctx), ctx.tag)


    def form(self, request, tag):
        """
        Render the inputs for a form.

        @param tag: A tag with
        """
        patterns = PatternDictionary(self.docFactory)
        inputs = []

        for parameter in self.parameters:
            view = parameter.viewFactory(parameter, None)
            if view is not None:
                view.setDefaultTemplate(
                    tag.onePattern(view.patternName + '-input-container'))
                inputs.append(view)
            else:
                inputs.append(_legacySpecialCases(self, patterns, parameter))

        if self.subFormName is None:
            pattern = tag.onePattern('liveform')
        else:
            pattern = tag.onePattern('subform')

        return dictFillSlots(
            tag,
            dict(form=pattern.fillSlots('inputs', inputs),
                 description=self._getDescription()))
    page.renderer(form)


    def render_form(self, ctx, data):
        return self.form(inevow.IRequest(ctx), ctx.tag)


    def invoke(self, formPostEmulator):
        """
        Invoke my callable with input from the browser.

        @param formPostEmulator: a dict of lists of strings in a format like a
            cgi-module form post.
        """
        return self.callable(**self._coerced(formPostEmulator))
    expose(invoke)


    def _coerced(self, received):
        """
        Convert some random strings received from a browser into structured
        data, using a list of parameters.

        @param received: a dict of lists of strings, i.e. the canonical Python
            form of web form post.

        @return: a dict mapping parameter names to coerced parameter values.
        """
        result = {}
        for parameter in self.parameters:
            if parameter.type == MULTI_TEXT_INPUT:
                values = list()
                for i in xrange(parameter.count):
                    name = parameter.name + '_' + str(i)
                    try:
                        inputValue = received[name][0]
                    except KeyError:
                        raise ConfigurationError("Missing value for field " +
                                                 str(i) + " of " + parameter.name)
                    values.append(parameter.coercer(inputValue))
                result[parameter.name.encode('ascii')] = values
            else:
                try:
                    inputValue = received[parameter.name][0]
                except KeyError:
                    raise ConfigurationError("Missing value for input: " +
                                            parameter.name)
                else:
                    # I want to be super-explicit about this for now, since it's
                    # doing stuff no other case is doing.
                    if parameter.type == FORM_INPUT:
                        coerced = parameter.coercer.invoke(inputValue)
                    else:
                        coerced = parameter.coercer(inputValue)
                    result[parameter.name.encode('ascii')] = coerced
        return result



class LiveFormFragment(_LiveFormMixin, athena.LiveFragment):
    """
    DEPRECATED.

    @see LiveForm
    """



class LiveForm(_LiveFormMixin, athena.LiveElement):
    """
    A live form.

    Create with a callable and a list of L{Parameter}s which describe the form
    of the arguments which the callable will expect.

    @ivar callable: a callable that you can call

    @ivar parameters: a list of L{Parameter} objects describing the arguments
        which should be passed to C{callable}.
    """



class _ParameterViewBase(Element):
    """
    Base class providing common functionality for different parameter views.

    @type parameter: L{Parameter}
    """
    def __init__(self, parameter):
        """
        @type tag: L{nevow.stan.Tag}
        @param tag: The document template to use to render this view.
        """
        self.parameter = parameter


    def setDefaultTemplate(self, tag):
        """
        Use the given default template.
        """
        self.docFactory = stan(tag)


    def __eq__(self, other):
        """
        Define equality such other views which are instances of the same class
        as this view and which wrap the same L{Parameter} are considered equal
        to this one.
        """
        if isinstance(other, self.__class__):
            return self.parameter is other.parameter
        return False


    def __ne__(self, other):
        """
        Define inequality as the negation of equality.
        """
        return not self.__eq__(other)


    def name(self, request, tag):
        """
        Render the name of the wrapped L{Parameter} or L{ChoiceParameter} instance.
        """
        return tag[self.parameter.name]
    renderer(name)


    def label(self, request, tag):
        """
        Render the label of the wrapped L{Parameter} or L{ChoiceParameter} instance.
        """
        if self.parameter.label:
            tag[self.parameter.label]
        return tag
    renderer(label)


    def description(self, request, tag):
        """
        Render the description of the wrapped L{Parameter} instance.
        """
        if self.parameter.description is not None:
            tag[self.parameter.description]
        return tag
    renderer(description)



class _TextLikeParameterView(_ParameterViewBase):
    """
    View definition base class for L{Parameter} instances which are simple text
    inputs.
    """
    def default(self, request, tag):
        """
        Render the initial value of the wrapped L{Parameter} instance.
        """
        if self.parameter.default is not None:
            tag[self.parameter.default]
        return tag
    renderer(default)



class TextParameterView(_TextLikeParameterView):
    """
    View definition for L{Parameter} instances with type of C{TEXT_INPUT}
    """
    implements(IParameterView)
    patternName = 'text'



class PasswordParameterView(_TextLikeParameterView):
    """
    View definition for L{Parameter} instances with type of C{PASSWORD_INPUT}
    """
    implements(IParameterView)
    patternName = 'password'



class OptionView(Element):
    """
    View definition for a single choice of a L{ChoiceParameter}.

    @type option: L{Option}
    """
    def __init__(self, index, option, tag):
        self._index = index
        self.option = option
        self.docFactory = stan(tag)


    def __eq__(self, other):
        """
        Define equality such other L{OptionView} instances which wrap the same
        L{Option} are considered equal to this one.
        """
        if isinstance(other, OptionView):
            return self.option is other.option
        return False


    def __ne__(self, other):
        """
        Define inequality as the negation of equality.
        """
        return not self.__eq__(other)


    def description(self, request, tag):
        """
        Render the description of the wrapped L{Option} instance.
        """
        return tag[self.option.description]
    renderer(description)


    def value(self, request, tag):
        """
        Render the value of the wrapped L{Option} instance.
        """
        return tag[self.option.value]
    renderer(value)


    def index(self, request, tag):
        """
        Render the index specified to C{__init__}.
        """
        return tag[self._index]
    renderer(index)


    def selected(self, request, tag):
        """
        Render a selected attribute on the given tag if the wrapped L{Option}
        instance is selected.
        """
        if self.option.selected:
            tag(selected='selected')
        return tag
    renderer(selected)



def _textParameterToView(parameter):
    """
    Return a L{TextParameterView} adapter for C{TEXT_INPUT} and
    C{PASSWORD_INPUT} L{Parameter} instances.
    """
    if parameter.type == TEXT_INPUT:
        return TextParameterView(parameter)
    if parameter.type == PASSWORD_INPUT:
        return PasswordParameterView(parameter)
    return None

registerAdapter(_textParameterToView, Parameter, IParameterView)



class ChoiceParameterView(_ParameterViewBase):
    """
    View definition for L{Parameter} instances with type of C{CHOICE_INPUT}.
    """
    implements(IParameterView)
    patternName = 'choice'

    def multiple(self, request, tag):
        """
        Render a I{multiple} attribute on the given tag if the wrapped
        L{ChoiceParameter} instance allows multiple selection.
        """
        if self.parameter.multiple:
            tag(multiple='multiple')
        return tag
    renderer(multiple)


    def options(self, request, tag):
        """
        Render each of the options of the wrapped L{ChoiceParameter} instance.
        """
        option = tag.patternGenerator('option')
        return tag[[
                OptionView(index, o, option())
                for (index, o)
                in enumerate(self.parameter.choices)]]
    renderer(options)

registerAdapter(ChoiceParameterView, ChoiceParameter, IParameterView)
