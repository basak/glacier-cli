#!/usr/bin/env python

# Copyright (c) 2012 Robie Basak
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
from __future__ import unicode_literals

import argparse
import calendar
import errno
import itertools
import os
import os.path
import sys
import time

import boto.glacier
import iso8601
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm


__version__ = '0.1.0'

# There is a lag between an archive being created and the archive
# appearing on an inventory. Even if the inventory has an InventoryDate
# of after the archive was created, it still doesn't necessarily appear.
# So only warn of a missing archive if the archive still hasn't appeared
# on an inventory created INVENTORY_LAG seconds after the archive was
# uploaded successfully.
INVENTORY_LAG = 24 * 60 * 60 * 3

PROGRAM_NAME = 'glacier'

class ConsoleError(RuntimeError):
    def __init__(self, m):
        self.message = m


class RetryConsoleError(ConsoleError): pass


def info(message):
    print(insert_prefix_to_lines('%s: info: ' % PROGRAM_NAME, message),
          file=sys.stderr)


def warn(message):
    print(insert_prefix_to_lines('%s: warning: ' % PROGRAM_NAME, message),
          file=sys.stderr)


def mkdir_p(path):
    """Create path if it doesn't exist already"""
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def insert_prefix_to_lines(prefix, lines):
    return "\n".join([prefix + line for line in lines.split("\n")])


def iso8601_to_unix_timestamp(iso8601_date_str):
    return calendar.timegm(iso8601.parse_date(iso8601_date_str).utctimetuple())


def get_user_cache_dir():
    xdg_cache_home = os.getenv('XDG_CACHE_HOME')
    if xdg_cache_home is not None:
        return xdg_cache_home

    home = os.getenv('HOME')
    if home is None:
        raise RuntimeError('Cannot find user home directory')
    return os.path.join(home, '.cache')


class Cache(object):
    Base = sqlalchemy.ext.declarative.declarative_base()
    class Archive(Base):
        __tablename__ = 'archive'
        id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
        name = sqlalchemy.Column(sqlalchemy.String)
        vault = sqlalchemy.Column(sqlalchemy.String, nullable=False)
        key = sqlalchemy.Column(sqlalchemy.String, nullable=False)
        last_seen_upstream = sqlalchemy.Column(sqlalchemy.Integer)
        created_here = sqlalchemy.Column(sqlalchemy.Integer)
        deleted_here = sqlalchemy.Column(sqlalchemy.Integer)

        def __init__(self, *args, **kwargs):
            self.created_here = time.time()
            super(Cache.Archive, self).__init__(*args, **kwargs)

    Session = sqlalchemy.orm.sessionmaker()

    def __init__(self, key, db_path=None):
        self.key = key
        if db_path is None:
            db_path = os.path.join(get_user_cache_dir(), 'glacier-cli', 'db')
        if db_path != ':memory:':
            mkdir_p(os.path.dirname(db_path))
        self.engine = sqlalchemy.create_engine('sqlite:///%s' % db_path)
        self.Base.metadata.create_all(self.engine)
        self.Session.configure(bind=self.engine)
        self.session = self.Session()

    def add_archive(self, vault, name, id):
        self.session.add(self.Archive(key=self.key,
                                      vault=vault, name=name, id=id))
        self.session.commit()

    def _get_archive_query_by_ref(self, vault, ref):
        if ref.startswith('id:'):
            filter = {'id': ref[3:]}
        elif ref.startswith('name:'):
            filter = {'name': ref[5:]}
        else:
            filter = {'name': ref}
        return self.session.query(self.Archive).filter_by(
                key=self.key, vault=vault, deleted_here=None, **filter)

    def get_archive_id(self, vault, ref):
        try:
            result = self._get_archive_query_by_ref(vault, ref).one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise KeyError(ref)
        return result.id

    def get_archive_name(self, vault, ref):
        try:
            result = self._get_archive_query_by_ref(vault, ref).one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise KeyError(ref)
        return result.name

    def get_archive_last_seen(self, vault, ref):
        try:
            result = self._get_archive_query_by_ref(vault, ref).one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise KeyError(ref)
        return result.last_seen_upstream or result.created_here

    def delete_archive(self, vault, ref):
        try:
            result = self._get_archive_query_by_ref(vault, ref).one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise KeyError(name)
        result.deleted_here = time.time()
        self.session.commit()

    @staticmethod
    def _archive_ref(archive, force_id=False):
        if archive.name and not force_id:
            if (archive.name.startswith('name:') or
                    archive.name.startswith('id:')):
                return "name:%s" % archive.name
            else:
                return archive.name
        else:
            return 'id:' + archive.id

    def _get_archive_list_objects(self, vault):
        for archive in (
                self.session.query(self.Archive).
                             filter_by(key=self.key,
                                       vault=vault,
                                       deleted_here=None).
                             order_by(self.Archive.name)):
            yield archive

    def get_archive_list(self, vault):
        def force_id(archive):
            return "\t".join([
                self._archive_ref(archive, force_id=True),
                "%s" % archive.name
                ])

        for archive_name, archive_iterator in (
                itertools.groupby(
                    self._get_archive_list_objects(vault),
                    lambda archive: archive.name)):
            # Yield self._archive_ref(..., force_id=True) if there is more than
            # one archive with the same name; otherwise use force_id=False.
            first_archive = next(archive_iterator)
            try:
                second_archive = next(archive_iterator)
            except StopIteration:
                yield self._archive_ref(first_archive, force_id=False)
            else:
                yield force_id(first_archive)
                yield force_id(second_archive)
                for subsequent_archive in archive_iterator:
                    yield force_id(subsequent_archive)

    def get_archive_list_with_ids(self, vault):
        for archive in self._get_archive_list_objects(vault):
            yield "\t".join([
                self._archive_ref(archive, force_id=True),
                "%s" % archive.name,
                ])

    def mark_seen_upstream(
            self, vault, id, name, upstream_creation_date,
            upstream_inventory_date, upstream_inventory_job_creation_date,
            fix=False):

        # Inventories don't get recreated unless the vault has changed.
        # See: https://forums.aws.amazon.com/thread.jspa?threadID=106541
        #
        # The cache's last_seen_upstream is supposed to contain a point in time
        # at which we know for sure that an archive existed, but this can fall
        # too far behind if a vault doesn't change. So assume that an archive
        # that appears in an inventory that hasn't been updated recently
        # nevertheless existed at around the time the inventory _could_ have
        # been regenerated, ie. at some point prior to the date that we
        # requested the inventory retrieval job.
        #
        # This is preferred over using the job completion date as an archive
        # could in theory be deleted while an inventory job is in progress and
        # would still appear in that inventory.
        #
        # Making up a date prior to the inventory job's creation could mean
        # that last_seen_upstream ends up claiming that an archive existed even
        # before it was created, but this will not cause a problem. Better that
        # it's too far back in time than too far ahead.
        #
        # With thanks to Wolfgang Nagele.

        last_seen_upstream = max(
            upstream_inventory_date,
            upstream_inventory_job_creation_date - INVENTORY_LAG
            )

        try:
            archive = self.session.query(self.Archive).filter_by(
                key=self.key, vault=vault, id=id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            self.session.add(
                self.Archive(
                    key=self.key, vault=vault, name=name, id=id,
                    last_seen_upstream=last_seen_upstream
                    )
                )
        else:
            if not archive.name:
                archive.name = name
            elif archive.name != name:
                if fix:
                    warn('archive %r appears to have changed name from %r ' %
                         (archive.id, archive.name) + 'to %r (fixed)' % (name))
                    archive.name = name
                else:
                    warn('archive %r appears to have changed name from %r ' %
                         (archive.id, archive.name) + 'to %r' % (name))
            if archive.deleted_here:
                archive_ref = self._archive_ref(archive)
                if archive.deleted_here < upstream_inventory_date:
                    warn('archive %r marked deleted but still present' %
                         archive_ref)
                else:
                    warn('archive %r deletion not yet in inventory' %
                         archive_ref)
            archive.last_seen_upstream = last_seen_upstream

    def mark_only_seen(self, vault, inventory_date, ids, fix=False):
        upstream_ids = set(ids)
        our_ids = set([r[0] for r in
                self.session.query(self.Archive.id)
                            .filter_by(key=self.key, vault=vault).all()])
        missing_ids = our_ids - upstream_ids
        for id in missing_ids:
            archive = (self.session.query(self.Archive)
                                   .filter_by(key=self.key,
                                              vault=vault, id=id)
                                   .one())
            archive_ref = self._archive_ref(archive)
            if archive.deleted_here and archive.deleted_here < inventory_date:
                self.session.delete(archive)
                info('deleted archive %r has left inventory; ' % archive_ref +
                     'removed from cache')
            elif not archive.deleted_here and (
                  archive.last_seen_upstream or
                    (archive.created_here and
                     archive.created_here < inventory_date - INVENTORY_LAG)):
                if fix:
                    self.session.delete(archive)
                    warn('archive disappeared: %r (removed from cache)' %
                         archive_ref)
                else:
                    warn('archive disappeared: %r' % archive_ref)
            else:
                warn('new archive not yet in inventory: %r' % archive_ref)

    def mark_commit(self):
        self.session.commit()


def get_connection_account(connection):
    """Return some account key associated with the connection.

    This is used to key a cache, so that the same cache can serve multiple
    accounts. The only requirement is that multiple namespaces of vaults and/or
    archives can never collide for connections that return the same key with
    this function. The cache will more more efficient if the same Glacier
    namespace sets always result in the same key.
    """
    return connection.layer1.aws_access_key_id


def find_retrieval_jobs(vault, archive_id):
    return [job for job in vault.list_jobs() if job.archive_id == archive_id]


def find_inventory_jobs(vault, max_age_hours=0):
    if max_age_hours:
        def recent_enough(job):
            if not job.completed:
                return True

            completion_date = iso8601_to_unix_timestamp(job.completion_date)
            return completion_date > time.time() - max_age_hours * 60 * 60
    else:
        def recent_enough(job):
            return not job.completed

    return [job for job in vault.list_jobs()
            if job.action == 'InventoryRetrieval' and recent_enough(job)]


def find_complete_job(jobs):
    for job in sorted(filter(lambda job: job.completed, jobs), key=lambda job: iso8601.parse_date(job.completion_date), reverse=True):
        return job


def has_pending_job(jobs):
    return any(filter(lambda job: not job.completed, jobs))


def update_job_list(jobs):
    for i, job in enumerate(jobs):
        jobs[i] = job.vault.get_job(job.id)


def job_oneline(conn, cache, vault, job):
    action_letter = {'ArchiveRetrieval': 'a',
                     'InventoryRetrieval': 'i'}[job.action]
    status_letter = {'InProgress': 'p',
                     'Succeeded': 'd',
                     'Failed': 'e'}[job.status_code]
    date = job.completion_date
    if not date:
        date = job.creation_date
    if job.action == 'ArchiveRetrieval':
        try:
            name = cache.get_archive_name(vault.name, 'id:' + job.archive_id)
        except KeyError:
            name = None
        if name is None:
            name = 'id:' + job.archive_id
    elif job.action == 'InventoryRetrieval':
        name = ''
    return '{action_letter}/{status_letter} {date} {vault.name:10} {name}'.format(
            **locals())


def wait_until_job_completed(jobs, sleep=600, tries=144):
    update_job_list(jobs)
    job = find_complete_job(jobs)
    while not job:
        tries -= 1
        if tries < 0:
            raise RuntimeError('Timed out waiting for job completion')
        time.sleep(sleep)
        update_job_list(jobs)
        job = find_complete_job(jobs)

    return job


class App(object):
    def job_list(self):
        for vault in self.connection.list_vaults():
            job_list = [job_oneline(self.connection,
                                    self.cache,
                                    vault,
                                    job)
                        for job in vault.list_jobs()]
            if job_list:
                print(*job_list, sep="\n")

    def vault_list(self):
        print(*[vault.name for vault in self.connection.list_vaults()],
                sep="\n")

    def vault_create(self):
        self.connection.create_vault(self.args.name)

    def _vault_sync_reconcile(self, vault, job, fix=False):
        response = job.get_output()
        inventory_date = iso8601_to_unix_timestamp(response['InventoryDate'])
        job_creation_date = iso8601_to_unix_timestamp(job.creation_date)
        seen_ids = []
        for archive in response['ArchiveList']:
            id = archive['ArchiveId']
            name = archive['ArchiveDescription']
            creation_date = iso8601_to_unix_timestamp(archive['CreationDate'])
            self.cache.mark_seen_upstream(
                vault=vault.name,
                id=id,
                name=name,
                upstream_creation_date=creation_date,
                upstream_inventory_date=inventory_date,
                upstream_inventory_job_creation_date=job_creation_date,
                fix=fix)
            seen_ids.append(id)
        self.cache.mark_only_seen(vault.name, inventory_date, seen_ids,
                                  fix=fix)
        self.cache.mark_commit()

    def _vault_sync(self, vault_name, max_age_hours, fix, wait):
        vault = self.connection.get_vault(vault_name)
        inventory_jobs = find_inventory_jobs(vault,
                                             max_age_hours=max_age_hours)

        complete_job = find_complete_job(inventory_jobs)
        if complete_job:
            self._vault_sync_reconcile(vault, complete_job, fix=fix)
        elif has_pending_job(inventory_jobs):
            if wait:
                complete_job = wait_until_job_completed(inventory_jobs)
            else:
                raise RetryConsoleError('job still pending for inventory on %r' %
                                        vault.name)
        else:
            job_id = vault.retrieve_inventory()
            job = vault.get_job(job_id)
            if wait:
                wait_until_job_completed([job])
                self._vault_sync_reconcile(vault, job, fix=fix)
            else:
                raise RetryConsoleError('queued inventory job for %r' %
                        vault.name)

    def vault_sync(self):
        return self._vault_sync(vault_name=self.args.name,
                                max_age_hours=self.args.max_age_hours,
                                fix=self.args.fix,
                                wait=self.args.wait)

    def archive_list(self):
        if self.args.force_ids:
            archive_list = list(self.cache.get_archive_list_with_ids(
                self.args.vault))
        else:
            archive_list = list(self.cache.get_archive_list(self.args.vault))

        if archive_list:
            print(*archive_list, sep="\n")

    def archive_upload(self):
        # XXX: "Leading whitespace in archive descriptions is removed."
        # XXX: "The description must be less than or equal to 1024 bytes. The
        #       allowable characters are 7 bit ASCII without control codes,
        #       specifically ASCII values 32-126 decimal or 0x20-0x7E
        #       hexadecimal."
        if self.args.name is not None:
            name = self.args.name
        else:
            try:
                full_name = self.args.file.name
            except:
                raise RuntimeError('Archive name not specified. Use --name')
            name = os.path.basename(full_name)

        vault = self.connection.get_vault(self.args.vault)
        archive_id = vault.create_archive_from_file(
            file_obj=self.args.file, description=name)
        self.cache.add_archive(self.args.vault, name, archive_id)

    @staticmethod
    def _write_archive_retrieval_job(f, job, multipart_size):
        if job.archive_size > multipart_size:
            def fetch(start, end):
                byte_range = start, end-1
                f.write(job.get_output(byte_range).read())

            whole_parts = job.archive_size // multipart_size
            for first_byte in xrange(0, whole_parts * multipart_size,
                                multipart_size):
                fetch(first_byte, first_byte + multipart_size)
            remainder = job.archive_size % multipart_size
            if remainder:
                fetch(job.archive_size - remainder, job.archive_size)
        else:
            f.write(job.get_output().read())

        # Make sure that the file now exactly matches the downloaded archive,
        # even if the file existed before and was longer.
        try:
            f.truncate(job.archive_size)
        except IOError as e:
            # Allow ESPIPE, since the "file" couldn't have existed before in
            # this case.
            if e.errno != errno.ESPIPE:
                raise

    @classmethod
    def _archive_retrieve_completed(cls, args, job, name):
        if args.output_filename == '-':
            cls._write_archive_retrieval_job(
                sys.stdout, job, args.multipart_size)
        else:
            if args.output_filename:
                filename = args.output_filename
            else:
                filename = os.path.basename(name)
            with open(filename, 'wb') as f:
                cls._write_archive_retrieval_job(f, job, args.multipart_size)

    def archive_retrieve_one(self, name):
        try:
            archive_id = self.cache.get_archive_id(self.args.vault, name)
        except KeyError:
            raise ConsoleError('archive %r not found' % name)

        vault = self.connection.get_vault(self.args.vault)
        retrieval_jobs = find_retrieval_jobs(vault, archive_id)

        complete_job = find_complete_job(retrieval_jobs)
        if complete_job:
            self._archive_retrieve_completed(self.args, complete_job, name)
        elif has_pending_job(retrieval_jobs):
            if self.args.wait:
                complete_job = wait_until_job_completed(retrieval_jobs)
                self._archive_retrieve_completed(self.args, complete_job, name)
            else:
                raise RetryConsoleError('job still pending for archive %r' % name)
        else:
            # create an archive retrieval job
            job = vault.retrieve_archive(archive_id)
            if self.args.wait:
                wait_until_job_completed([job])
                self._archive_retrieve_completed(self.args, job, name)
            else:
                raise RetryConsoleError('queued retrieval job for archive %r' % name)

    def archive_retrieve(self):
        if len(self.args.names) > 1 and self.args.output_filename:
            raise ConsoleError('cannot specify output filename with multi-archive retrieval')
        success_list = []
        retry_list = []
        for name in self.args.names:
            try:
                self.archive_retrieve_one(name)
            except RetryConsoleError as e:
                retry_list.append(e.message)
            else:
                success_list.append('retrieved archive %r' % name)
        if retry_list:
            message_list = success_list + retry_list
            raise RetryConsoleError("\n".join(message_list))

    def archive_delete(self):
        try:
            archive_id = self.cache.get_archive_id(
                self.args.vault, self.args.name)
        except KeyError:
            raise ConsoleError('archive %r not found' % self.args.name)
        vault = self.connection.get_vault(self.args.vault)
        vault.delete_archive(archive_id)
        self.cache.delete_archive(self.args.vault, self.args.name)

    def archive_checkpresent(self):
        try:
            last_seen = self.cache.get_archive_last_seen(
                self.args.vault, self.args.name)
        except KeyError:
            if self.args.wait:
                last_seen = None
            else:
                if not self.args.quiet:
                    print(
                        'archive %r not found' % self.args.name,
                        file=sys.stderr)
                return

        def too_old(last_seen):
            return (not last_seen or
                    not self.args.max_age_hours or
                    (last_seen <
                        time.time() - self.args.max_age_hours * 60 * 60))

        if too_old(last_seen):
            # Not recent enough
            try:
                self._vault_sync(vault_name=self.args.vault,
                                 max_age_hours=self.args.max_age_hours,
                                 fix=False,
                                 wait=self.args.wait)
            except RetryConsoleError:
                pass
            else:
                try:
                    last_seen = self.cache.get_archive_last_seen(
                        self.args.vault, self.args.name)
                except KeyError:
                    if not self.args.quiet:
                        print(('archive %r not found, but it may ' +
                                           'not be in the inventory yet')
                                           % self.args.name, file=sys.stderr)
                    return

        if too_old(last_seen):
            if not self.args.quiet:
                print(('archive %r found, but has not been seen ' +
                                   'recently enough to consider it present') %
                                   self.args.name, file=sys.stderr)
            return

        print(self.args.name)


    def parse_args(self, args=None):
        parser = argparse.ArgumentParser()
        parser.add_argument('--region', default='us-east-1')
        subparsers = parser.add_subparsers()
        vault_subparser = subparsers.add_parser('vault').add_subparsers()
        vault_subparser.add_parser('list').set_defaults(func=self.vault_list)
        vault_create_subparser = vault_subparser.add_parser('create')
        vault_create_subparser.set_defaults(func=self.vault_create)
        vault_create_subparser.add_argument('name')
        vault_sync_subparser = vault_subparser.add_parser('sync')
        vault_sync_subparser.set_defaults(func=self.vault_sync)
        vault_sync_subparser.add_argument('name', metavar='vault_name')
        vault_sync_subparser.add_argument('--wait', action='store_true')
        vault_sync_subparser.add_argument('--fix', action='store_true')
        vault_sync_subparser.add_argument('--max-age', type=int, default=24,
                                          dest='max_age_hours')
        archive_subparser = subparsers.add_parser('archive').add_subparsers()
        archive_list_subparser = archive_subparser.add_parser('list')
        archive_list_subparser.set_defaults(func=self.archive_list)
        archive_list_subparser.add_argument('--force-ids', action='store_true')
        archive_list_subparser.add_argument('vault')
        archive_upload_subparser = archive_subparser.add_parser('upload')
        archive_upload_subparser.set_defaults(func=self.archive_upload)
        archive_upload_subparser.add_argument('vault')
        archive_upload_subparser.add_argument('file',
                                              type=argparse.FileType('rb'))
        archive_upload_subparser.add_argument('--name')
        archive_retrieve_subparser = archive_subparser.add_parser('retrieve')
        archive_retrieve_subparser.set_defaults(func=self.archive_retrieve)
        archive_retrieve_subparser.add_argument('vault')
        archive_retrieve_subparser.add_argument('names', nargs='+',
                                                metavar='name')
        archive_retrieve_subparser.add_argument('--multipart-size', type=int,
                default=(8*1024*1024))
        archive_retrieve_subparser.add_argument('-o', dest='output_filename',
                                                metavar='OUTPUT_FILENAME')
        archive_retrieve_subparser.add_argument('--wait', action='store_true')
        archive_delete_subparser = archive_subparser.add_parser('delete')
        archive_delete_subparser.set_defaults(func=self.archive_delete)
        archive_delete_subparser.add_argument('vault')
        archive_delete_subparser.add_argument('name')
        archive_checkpresent_subparser = archive_subparser.add_parser(
                'checkpresent')
        archive_checkpresent_subparser.set_defaults(
                func=self.archive_checkpresent)
        archive_checkpresent_subparser.add_argument('vault')
        archive_checkpresent_subparser.add_argument('name')
        archive_checkpresent_subparser.add_argument('--wait',
                                                    action='store_true')
        archive_checkpresent_subparser.add_argument('--quiet',
                                                    action='store_true')
        archive_checkpresent_subparser.add_argument(
                '--max-age', type=int, default=80, dest='max_age_hours')
        job_subparser = subparsers.add_parser('job').add_subparsers()
        job_subparser.add_parser('list').set_defaults(func=self.job_list)
        return parser.parse_args(args)

    def __init__(self, args=None, connection=None, cache=None):
        args = self.parse_args(args)

        if connection is None:
            connection = boto.glacier.connect_to_region(args.region)

        if cache is None:
            cache = Cache(get_connection_account(connection))

        self.connection = connection
        self.cache = cache
        self.args = args

    def main(self):
        try:
            self.args.func()
        except RetryConsoleError as e:
            message = insert_prefix_to_lines(PROGRAM_NAME + ': ', e.message)
            print(message, file=sys.stderr)
            # From sysexits.h:
            #     "temp failure; user is invited to retry"
            sys.exit(75)  # EX_TEMPFAIL
        except ConsoleError as e:
            message = insert_prefix_to_lines(PROGRAM_NAME + ': ', e.message)
            print(message, file=sys.stderr)
            sys.exit(1)


def main():
    App().main()


if __name__ == '__main__':
    main()
