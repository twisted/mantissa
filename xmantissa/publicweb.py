
"""
Support for the public-facing portion of web applications.
"""

from zope.interface import implements

from axiom import item, attributes

from xmantissa import ixmantissa, website

class PublicWeb(item.Item, website.PrefixURLMixin):
    """
    Fixture for site-wide public-facing content.

    @ivar application: An Item which implements L{ixmantissa.IPublicPage}.
    """
    implements(ixmantissa.ISiteRootPlugin)

    typeName = 'mantissa_public_web'
    schemaVersion = 1

    prefixURL = attributes.text(allowNone=False)
    application = attributes.reference(allowNone=False)

    installedOn = attributes.reference()

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install PublicWeb on more than one thing"
        super(PublicWeb, self).installOn(other)
        self.installedOn = other

    def createResource(self):
        return ixmantissa.IPublicPage(self.application).createResource()
