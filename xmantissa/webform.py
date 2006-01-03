
# Temporary form generation until we get something better.  Do *not*
# put anything elaborate or correct into this module.

from nevow import tags

TEXT_INPUT = 'text'

class ConfigurationError(Exception):
    """
    User-specified configuration for a newly created Item was invalid
    or incomplete.
    """



def Form(fields):
    def _form():
        for parameter in fields:
            i = tags.input(name=parameter.name, type=parameter.type)
            if parameter.default is not None:
                i = i(value=parameter.default)
            t = tags.div[parameter.description, i]
            yield t
    return list(_form())



def coerced(expected, received):
    result = {}
    for parameter in expected:
        try:
            inputValue = received[parameter.name][0]
        except KeyError:
            raise ConfigurationError("Missing value for input: " + parameter.name)
        else:
            result[parameter.name] = parameter.coercer(inputValue)
    return result
