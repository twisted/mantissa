from epsilon import setuphelper

from xmantissa import version

setuphelper.autosetup(
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
        "Topic :: Internet"])
