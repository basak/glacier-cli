#!/usr/bin/env python

# Copyright (c) 2013 Robie Basak
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

import sys
import unittest

from mock import Mock

import glacier


class TestCase(unittest.TestCase):
    def init_app(self, args):
        self.connection = Mock()
        self.cache = Mock()
        self.app = glacier.App(
            args=args,
            connection=self.connection,
            cache=self.cache)

    def run_app(self, args):
        self.init_app(args)
        self.app.main()

    def test_stdin_upload(self):
        self.run_app(['archive', 'upload', 'vault_name', '-'])
        self.connection.get_vault.assert_called_once_with('vault_name')
        vault = self.connection.get_vault.return_value
        vault.create_archive_from_file.assert_called_once_with(
            file_obj=sys.stdin, description='<stdin>')
