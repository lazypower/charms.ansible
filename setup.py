import os
from setuptools import setup

setup(
    name = "charms.ansible",
    version = "0.0.1",
    author = "Charles Butler",
    author_email = "charles.butler@ubuntu.com",
    url = "http://github.com/juju-solutions/charms.ansible",
    description = ( "Helpers for working with Ansible in JujuCharms" ),
    license = "GPLv3",
    keywords = "ansible juju charm charms",
    packages = ['charms.ansible'],
    long_description = "",
    classifiers = [
        "Development Status :: 3 - Alpha",
    ],
)
