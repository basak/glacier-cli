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

from __future__ import print_function

import sys
import unittest

from mock import Mock, patch, sentinel

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

    def test_vault_list(self):
        self.init_app(['vault', 'list'])
        mock_vault = Mock()
        mock_vault.name = sentinel.vault_name
        self.connection.list_vaults.return_value = [mock_vault]
        print_mock = Mock()
        with patch('__builtin__.print', print_mock):
            self.app.main()
        print_mock.assert_called_once_with(sentinel.vault_name, sep=u'\n')

    def test_vault_create(self):
        self.run_app(['vault', 'create', 'vault_name'])
        self.connection.create_vault.assert_called_once_with('vault_name')

    def test_archive_list(self):
        self.init_app(['archive', 'list', 'vault_name'])
        archive_list = [sentinel.archive_one, sentinel.archive_two]
        self.cache.get_archive_list.return_value = archive_list
        print_mock = Mock()
        with patch('__builtin__.print', print_mock):
            self.app.main()
        print_mock.assert_called_once_with(*archive_list, sep="\n")

    def test_stdin_upload(self):
        self.run_app(['archive', 'upload', 'vault_name', '-'])
        self.connection.get_vault.assert_called_once_with('vault_name')
        vault = self.connection.get_vault.return_value
        vault.create_archive_from_file.assert_called_once_with(
            file_obj=sys.stdin, description='<stdin>')
