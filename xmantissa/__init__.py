# -*- test-case-name: xmantissa.test -*-

from xmantissa._version import __version__
from twisted.python import versions

def asTwistedVersion(packageName, versionString):
    return versions.Version(packageName, *map(int, versionString.split(".")))

version = asTwistedVersion("xmantissa", __version__)
