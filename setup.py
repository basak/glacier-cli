#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright (c) 2015 Markus Hubig
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import os
import re
import codecs

from setuptools import setup

def read(*parts):
    path = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(path, encoding='utf-8') as fobj:
        return fobj.read()

def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

def read_requirements(*file_paths):
    return read(*file_paths).split()


install_requires = read_requirements("requirements.txt")
tests_require = read_requirements("requirements-tests.txt")

setup(
    name='glacier-cli',
    version=find_version('glacier.py'),
    description='A sysadmin-friendly command line interface to Amazon Glacier.',
    long_description=read('README.md'),
    url='https://github.com/basak/glacier-cli',
    author='https://github.com/basak',
    license='MIT License',
    install_requires=install_requires,
    tests_require=tests_require,
    test_suite = 'nose.collector',
    py_modules=['glacier'],
    entry_points={'console_scripts': ['glacier-cli=glacier:main']}
)
