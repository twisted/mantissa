
# Temporary form generation until we get something better.  Do *not*
# put anything elaborate or correct into this module.

from nevow import tags

TEXT_INPUT = 'text'
def Form(fields):
    def _form():
        for (name, type, _, description, default) in fields:
            i = tags.input(name=name, type=type)
            if default is not None:
                i = i(value=default)
            t = tags.div[description, i]
            yield t
    return list(_form())
