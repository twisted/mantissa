from setuptools import setup, find_packages
import re

versionPattern = re.compile(r"""^__version__ = ['"](.*?)['"]$""", re.M)
with open("xmantissa/_version.py", "rt") as f:
    version = versionPattern.search(f.read()).group(1)

setup(
    name="Mantissa",
    version=version,
    maintainer="Tristan Seligmann",
    maintainer_email="mithrandi@mithrandi.net",
    url="https://github.com/twisted/mantissa",
    license="MIT",
    platforms=["any"],
    description="A multiprotocol application deployment platform",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: No Input/Output (Daemon)",
        "Framework :: Twisted",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: JavaScript",
        "Programming Language :: Python",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Terminals",
        ],
    install_requires=[
        "Twisted>=14.0.0",
        "PyOpenSSL>=0.13",
        "Axiom>=0.7.0",
        "Vertex>=0.2.0",
        "PyTZ",
        "Pillow",
        "cssutils>=0.9.5",
        "Nevow>=0.9.5",
        "PyCrypto",
        ],
    packages=find_packages() + ['axiom.plugins', 'nevow.plugins'],
    include_package_data=True,
    )
