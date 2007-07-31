
"""
An interactive demonstration of L{xmantissa.liveform.LiveForm} and
L{xmantissa.liveform.RepeatableFormParameter}.

Run this test like this::
    $ twistd -n athena-widget --element=xmantissa.test.acceptance.liveform.testname
    $ firefox http://localhost:8080/
    (where testname is one of "coerce", "inputerrors",
     "repeatableFormParameter", "repeatableFormParameterCompact")

This will display a form which rejects most inputs.
"""

from xmantissa.liveform import TEXT_INPUT, InputError, Parameter, LiveForm, RepeatableFormParameter


def coerce(theText):
    """
    Reject all values of C{theText} except C{'hello, world'}.
    """
    if theText != u'hello, world':
        raise InputError(u"Try entering 'hello, world'")


def inputerrors():
    """
    Create a L{LiveForm} which rejects most inputs in order to demonstrate how
    L{InputError} is handled in the browser.
    """
    form = LiveForm(
        lambda theText: None,
        [Parameter(u'theText', TEXT_INPUT, coerce, 'Some Text')],
        u'LiveForm input errors acceptance test',
        )
    return form



def repeatableFormParameter():
    """
    Create a L{LiveForm} with a L{RepeatableFormParameter}.
    """
    form = LiveForm(
        lambda **k: unicode(k),
        [RepeatableFormParameter(
            u'repeatableFoo',
            [Parameter('foo', TEXT_INPUT, int, 'Enter a number'),
             Parameter('bar', TEXT_INPUT, int, 'And another')])])
    form.jsClass = u'Mantissa.Test.EchoingFormWidget'
    return form



def repeatableFormParameterCompact():
    """
    Create a compact L{LiveForm} with a L{RepeatableFormParameter}.
    """
    form = repeatableFormParameter()
    form.compact()
    return form
