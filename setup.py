# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import os.path
import re


import setuptools


def get_long_description():
    with open("README.md", "r") as fh:
        return fh.read()


def get_version():
    with open(os.path.join("stack", "version.py"), "r") as fh:
        pkg = fh.read()

    LIBAPI = int(re.search(r"""(?m)^LIBAPI\s*=\s*(\d+)""", pkg).group(1))
    LIBPATCH = int(re.search(r"""(?m)^LIBPATCH\s*=\s*(\d+)""", pkg).group(1))
    return f"{LIBAPI}.{LIBPATCH}"


install_requires = ["pyyaml", "click", "tabulate"]

setuptools.setup(
    name="stack",
    version=get_version(),
    author="David García",
    author_email="david.garcia@canonical.com",
    maintainer="Canonical",
    description="stack: tool to deploy stacks in Juju",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/davigar15/juju-stack",
    packages=["stack", "stack.cli"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
    ],
    keywords="juju charm osm",
    project_urls={
        "Juju": "https://juju.is/",
    },
    python_requires=">=3.6",
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "juju-stack = stack.cli.juju:main",
            "charmcraft-stack = stack.cli.charmcraft:main",
        ],
    },
)
