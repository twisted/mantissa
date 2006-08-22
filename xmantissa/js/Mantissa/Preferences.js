// import Mantissa.LiveForm

Mantissa.Preferences.PrefCollectionLiveForm = Mantissa.LiveForm.FormWidget.subclass(
                                                'Mantissa.Preferences.PrefCollectionLiveForm');

/**
 * L{Mantissa.LiveForm.FormWidget} subclass which replaces its
 * node with the string received during form submission, which
 * is expected to be a new, flattened liveform
 */
Mantissa.Preferences.PrefCollectionLiveForm.methods(
    function submitSuccess(self, result) {
        Divmod.Runtime.theRuntime.setNodeContent(
            self.node,
            '<div xmlns="http://www.w3.org/1999/xhtml">' + result + '</div>');
    });
