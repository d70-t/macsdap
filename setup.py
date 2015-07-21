import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "macsdap",
    version = "0.0.1",
    author = "Tobias Koelling",
    author_email = "tobias.koelling@physik.uni-muenchen.de",
    description = ("A pydap wrapper for simplified access to macsServer."),
    license = "BSD",
    keywords = "opendap macs",
    url = "http://www.meteo.physik.uni-muenchen.de",
    packages=['macsdap'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires=[
        "pydap==3.1.1cert"
    ],
    dependency_links=[
        "git+https://github.com/d70-t/pydap@master#egg=pydap-3.1.1cert" #pin to a version with CA_CERTS support
    ]
)
