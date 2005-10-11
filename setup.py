from distutils.core import setup

distobj = setup(
    name="Mantissa",
    version="0.1",
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

              'axiom.plugins'],

    package_data={'xmantissa': ['static/*', 'themes/base/*']})

from epsilon.setuphelper import regeneratePluginCache
regeneratePluginCache(distobj)
