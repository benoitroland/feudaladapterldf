#!/usr/bin/env python3

import setuptools

with open("README.md", "r") as me:
    long_description = me.read()

setuptools.setup(
    name="ldf_adapter",
    version="0.1.2-dev1",
    author="Joshua Bachmeier",
    author_email="joshua.bachmeier@student.kit.edu",
    description="LDF Adapter to connect BWIDM and FEUDAL",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://git.scc.kit.edu/feudal/feudal_adapter_ldf",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: No License ",
        "Operating System :: Unix Like",
    ],
    install_requires=[
        "Unidecode",
        "regex",
        "requests",
    ],
    entry_points={
        'console_scripts': [
            "ldf_adapter = ldf_adapter.interface:main"
        ]
    },
)
