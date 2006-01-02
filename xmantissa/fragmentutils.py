from zope.interface import implements

from nevow import inevow, rend
from nevow.taglibrary import tabbedPane

from xmantissa import ixmantissa

class PatternDictionary(object):
    def __init__(self, docFactory):
        self.docFactory = inevow.IQ(docFactory)
        self.patterns = dict()

    def __getitem__(self, i):
        if i not in self.patterns:
            self.patterns[i] = self.docFactory.patternGenerator(i)
        return self.patterns[i]

def dictFillSlots(tag, slotmap):
    for (k, v) in slotmap.iteritems():
        tag = tag.fillSlots(k, v)
    return tag

class FragmentCollector(rend.Fragment):
    implements(ixmantissa.INavigableFragment)

    fragmentName = None
    live = True
    title = None

    collect = ()

    def __init__(self, original, docFactory=None):
        rend.Fragment.__init__(self, original, docFactory)

        translator = ixmantissa.IWebTranslator(original.installedOn)

        tabs = []
        for item in self.collect:
            item = original.installedOn.findFirst(item)
            frag = ixmantissa.INavigableFragment(item)
            frag.docFactory = translator.getDocFactory(frag.fragmentName, None)
            tabs.append((frag.title, frag))
        self.tabs = tabs

    def head(self):
        for (tabTitle, fragment) in self.tabs:
            content = fragment.head()
            if content is not None:
                yield content

        yield tabbedPane.tabbedPaneGlue.inlineGlue

    def locateHandler(self, ctx, path, name):
        for (tabTitle, fragment) in self.tabs:
            handler = getattr(fragment, 'handle_'+name, None)
            if handler is not None:
                return handler
        raise AttributeError, 'no handler for %r' % name

    def data_tabbedPane(self, ctx, data):
        return tabbedPane.tabbedPane(ctx, dict(pages=self.tabs))

