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

import mock
from mock import Mock, patch, sentinel
import nose.tools

import glacier


EX_TEMPFAIL = 75


class TestCase(unittest.TestCase):
    def init_app(self, args, memory_cache=False):
        self.connection = Mock()
        if memory_cache:
            self.cache = glacier.Cache(0, db_path=':memory:')
        else:
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

    def test_archive_list_force_ids(self):
        self.init_app(
            ['archive', 'list', '--force-ids', 'vault_name'],
            memory_cache=True,
        )
        self.cache.add_archive('vault_name', 'archive_name_1', 'id_1')
        self.cache.add_archive('vault_name', 'archive_name_1', 'id_2')
        self.cache.add_archive('vault_name', 'archive_name_3', 'id_3')
        print_mock = Mock()
        with patch('__builtin__.print', print_mock):
            self.app.main()

        # print should have been called with a list of the items in some
        # arbitrary order. Testing this correctly involves being agnostic with
        # the order of args in *args. Does mock provide any other way of doing
        # this other than by introspecting mock_calls like this?
        nose.tools.assert_equals(print_mock.call_count, 1)
        nose.tools.assert_equals(
            sorted(print_mock.mock_calls[0][1]),
            sorted([
                u'id:id_1\tarchive_name_1',
                u'id:id_2\tarchive_name_1',
                u'id:id_3\tarchive_name_3',
            ]),
        )
        nose.tools.assert_equals(
            print_mock.mock_calls[0][2],
            {'sep': "\n"}
        )

    def test_archive_upload(self):
        file_obj = Mock()
        file_obj.name = 'filename'
        open_mock = Mock(return_value=file_obj)
        with patch('__builtin__.open', open_mock):
            self.run_app(['archive', 'upload', 'vault_name', 'filename'])
        self.connection.get_vault.assert_called_with('vault_name')
        mock_vault = self.connection.get_vault.return_value
        mock_vault.create_archive_from_file.assert_called_once_with(
            file_obj=file_obj, description='filename')

    def test_archive_stdin_upload(self):
        self.run_app(['archive', 'upload', 'vault_name', '-'])
        self.connection.get_vault.assert_called_once_with('vault_name')
        vault = self.connection.get_vault.return_value
        vault.create_archive_from_file.assert_called_once_with(
            file_obj=sys.stdin, description='<stdin>')

    def test_archive_retrieve_no_job(self):
        self.init_app(['archive', 'retrieve', 'vault_name', 'archive_name'])
        mock_vault = Mock()
        mock_vault.list_jobs.return_value = []
        self.connection.get_vault.return_value = mock_vault
        mock_exit = Mock()
        mock_print = Mock()
        with patch('sys.exit', mock_exit):
            with patch('__builtin__.print', mock_print):
                self.app.main()
        mock_exit.assert_called_once_with(EX_TEMPFAIL)
        mock_print.assert_called_once_with(
            u"glacier: queued retrieval job for archive 'archive_name'",
            file=sys.stderr)
        self.connection.get_vault.assert_called_once_with('vault_name')
        mock_vault.retrieve_archive.assert_called_once_with(
            self.cache.get_archive_id.return_value)

    def test_archive_retrieve_with_job(self):
        self.init_app(['archive', 'retrieve', 'vault_name', 'archive_name'])
        self.cache.get_archive_id.return_value = sentinel.archive_id
        mock_job = Mock(
            archive_id=sentinel.archive_id,
            completed=True,
            completion_date='1970-01-01T00:00:00Z',
            archive_size=1)
        mock_vault = Mock()
        mock_vault.list_jobs.return_value = [mock_job]
        self.connection.get_vault.return_value = mock_vault
        mock_open = mock.mock_open()
        with patch('__builtin__.open', mock_open):
            self.app.main()
        self.cache.get_archive_id.assert_called_once_with(
            'vault_name', 'archive_name')
        mock_job.get_output.assert_called_once_with()
        mock_job.get_output.return_value.read.assert_called_once_with()
        mock_open.assert_called_once_with('archive_name', u'wb')
        mock_open.return_value.write.assert_called_once_with(
            mock_job.get_output.return_value.read.return_value)

    def test_archive_delete(self):
        self.run_app(['archive', 'delete', 'vault_name', 'archive_name'])
        self.cache.get_archive_id.assert_called_once_with(
            'vault_name', 'archive_name')
        self.connection.get_vault.assert_called_with('vault_name')
        mock_vault = self.connection.get_vault.return_value
        mock_vault.delete_archive.assert_called_once_with(
            self.cache.get_archive_id.return_value)
