# -*- test-case-name: xmantissa.test -*-
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

from twisted.python import versions

def asTwistedVersion(packageName, versionString):
    return versions.Version(
            packageName, *map(int, versionString.split('+', 1)[0].split(".")))

version = asTwistedVersion("xmantissa", __version__)

__all__ = ['version', '__version__']
