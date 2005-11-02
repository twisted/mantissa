from distutils.core import setup

from xmantissa import version

distobj = setup(
    name="Mantissa",
    version=version.short(),
    maintainer="Divmod, Inc.",
    maintainer_email="support@divmod.org",
    url="http://divmod.org/trac/wiki/MantissaProject",
    license="MIT",
    platforms=["any"],
    description="A multiprotocol application deployment platform",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Development Status :: 2 - Pre-Alpha",
        "Topic :: Internet"],

    packages=['xmantissa',
              'xmantissa.plugins',
              'xmantissa.test',

              'axiom.plugins'])

from epsilon.setuphelper import regeneratePluginCache
regeneratePluginCache(distobj)
