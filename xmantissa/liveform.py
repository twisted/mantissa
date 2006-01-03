"""

XXX HYPER TURBO SUPER UNSTABLE DO NOT USE XXX

"""

from epsilon.structlike import record

from nevow import tags, athena, loaders

class Parameter(record('name type coercer description default')):
    pass

TEXT_INPUT = 'text'

class ConfigurationError(Exception):
    """
    User-specified configuration for a newly created Item was invalid
    or incomplete.
    """


class LiveForm(record('callable parameters'), athena.LiveFragment):
    """
    A live form.

    Create with a callable and a list of L{Parameter}s which describe the form
    of the arguments which the callable will expect.

    @ivar callable: a callable that you can call
    @ivar parameters: a list of Parameter objects describing
    """
    allowedMethods = dict(invoke = True)
    jsClass = u'Mantissa.LiveForm.FormWidget'

    docFactory = loaders.stan(
        tags.form(render=tags.directive('liveFragment'),
                  action="#",
                  onsubmit='Nevow.Athena.Widget.get(this).submit()')[
            tags.directive("form")])

    def render_form(self, ctx, data):
        for parameter in self.parameters:
            i = tags.input(name=parameter.name,
                           type=parameter.type)
            if parameter.default is not None:
                i = i(value=parameter.default)
            t = tags.div[parameter.description, i]
            yield t


    def invoke(self, formPostEmulator):
        """
        Invoke my callable with input from the browser.

        @param formPostEmulator: a dict of lists of strings in a format like a
        cgi-module form post.
        """
        return self.callable(**self._coerced(formPostEmulator))


    def _coerced(self, received):
        """
        Convert some random strings received from a browser into structured data,
        using a list of parameters.

        @param expected: an iterable of L{Parameter}s

        @param received: a dict of lists of strings, i.e. the canonical Python form
        of web form post.

        @return: a dict mapping parameter names to coerced parameter values.
        """
        result = {}
        for parameter in self.parameters:
            try:
                inputValue = received[parameter.name][0]
            except KeyError:
                raise ConfigurationError("Missing value for input: " +
                                         parameter.name)
            else:
                result[parameter.name] = parameter.coercer(inputValue)
        return result
