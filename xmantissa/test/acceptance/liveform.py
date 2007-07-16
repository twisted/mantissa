
"""
An interactive demonstration of L{xmantissa.livetest.LiveForm}.

Run this test like this::
    $ twistd -n athena-widget --element=xmantissa.test.acceptance.liveform.inputerrors
    $ firefox http://localhost:8080/

This will display a form which rejects most inputs.
"""

from xmantissa.liveform import TEXT_INPUT, InputError, Parameter, LiveForm


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
