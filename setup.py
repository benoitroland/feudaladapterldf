#! /usr/bin/env python
# MIT License{{{
#
# Copyright (c) 2017 - 2019 Karlsruhe Institute of Technology - Steinbuch Centre for Computing
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.}}}

import setuptools

setuptools.setup(
    setup_requires=['pbr>=1.8'],
    pbr=True,
)

#!/usr/bin/env python3
#
# import setuptools
#
# with open("README.md", "r") as me:
#     long_description = me.read()
#
# setuptools.setup(
#     name="ldf_adapter",
#     version="0.1.2-dev1",
#     author="Joshua Bachmeier",
#     author_email="joshua.bachmeier@student.kit.edu",
#     description="LDF Adapter to connect BWIDM and FEUDAL",
#     long_description=long_description,
#     long_description_content_type="text/markdown",
#     url="https://git.scc.kit.edu/feudal/feudal_adapter_ldf",
#     packages=setuptools.find_packages(),
#     classifiers=[
#         "Programming Language :: Python :: 3",
#         "License :: No License ",
#         "Operating System :: Unix Like",
#     ],
#     install_requires=[
#         "Unidecode",
#         "regex",
#         "requests",
#     ],
#     entry_points={
#         'console_scripts': [
#             "ldf_adapter = ldf_adapter.interface:main"
#         ]
#     },
#     test_suite="tests"
# )
