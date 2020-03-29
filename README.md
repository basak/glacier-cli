glacier-cli
===========

This tool provides a sysadmin-friendly command line interface to [Amazon
Glacier][glacier], turning Glacier into an easy-to-use storage backend. It
automates tasks which would otherwise require a number of separate steps (job
submission, polling for job completion and retrieving the results of jobs).
It provides integration with [git-annex][git-annex], making Glacier even more
useful.

[glacier]: http://aws.amazon.com/glacier/
[git-annex]: http://git-annex.branchable.com/

glacier-cli uses Amazon Glacier's archive description field to keep friendly
archive names, although you can also address archives directly by using their
IDs. It keeps a local cache of archive IDs and their corresponding names, as
well as housekeeping data to keep the cache up-to-date. This will save you time
because you won't have to wait spend hours retrieving inventories all the time,
and will save you mental effort because you won't have to keep track of the
obtuse archive IDs yourself.

glacier-cli is fully interoperable with other applications using the same
Glacier vaults. It can deal gracefully with vaults changing from other machines
and/or other applications, and introduces no new special formats from the point
of view of a vault.

Example with git-annex
----------------------

    $ echo 42 > example-content
    $ git annex add example-content
    add example-content (checksum...) ok
    (Recording state in git...)
    $ git commit -m'Add example-content'
    [master cc632d1] Add example-content
     1 file changed, 1 insertion(+)
     create mode 120000 example/example-content
_(the local annex now stores example-content)_

    $ git annex copy --to glacier example-content
    copy example-content (gpg) (checking glacier...) (to glacier...) 
    ok
_(copying content to Amazon Glacier is straightforward)_

    $ git annex drop example-content
    drop example-content (gpg) (checking glacier...) ok
_(now the only copy of the data is in Amazon Glacier)_

    $ git annex get --from glacier example-content
    get example-content (from glacier...) (gpg) 
    glacier: queued retrieval job for archive 'GPGHMACSHA1--2945f64be96ccbb9feb4d8ff44ac9692fdbe654e'

      retrieve hook exited nonzero!
    failed
    git-annex: get: 1 failed
_(this fails on the first attempt since the data isn't immediately available;
but it does submit a job to Amazon Glacier requesting the data, so a later
retry will work)_

_(...four hours later...)_

    $ git annex get --from glacier example-content
    get example-content (from glacier...) (gpg) 
    ok
    $ cat example-content
    42
_(content successfully retrieved from Glacier)_

Example without git-annex
-------------------------

    $ glacier vault list
_(empty result with zero exit status)_

    $ glacier vault create example-vault
_(silently successful: like other Unix commands, only errors are noisy)_

    $ glacier vault list
    example-vault
_(this list is retrieved from Glacier; a relatively quick operation)_

    $ glacier archive list example-vault
_(empty result with zero exit status; nothing is in our vault yet)_

    $ echo 42 > example-content
    $ glacier archive upload example-vault example-content
_(Glacier has now stored example-content in an archive with description
example-content and in a vault called example-vault)_

    $ glacier archive list example-vault
    example-content
_(this happens instantly, since glacier-cli maintains a cached inventory)_

    $ rm example-content
_(now the only place the content is stored is in Glacier)_

    $ glacier archive retrieve example-vault example-content
    glacier: queued retrieval job for archive 'example-content'
    $ glacier archive retrieve example-vault example-content
    glacier: job still pending for archive 'example-content'
    $ glacier job list
    a/p 2012-09-19T21:41:35.238Z example-vault example-content
    $ glacier archive retrieve --wait example-vault example-content
_(...hours pass while Amazon retrieves the content...)_

    $ cat example-content
    42
_(content successfully retrieved from Glacier)_

Costs
-----

Before you use Amazon Glacier, you should make yourself familiar with [how much
it costs](http://aws.amazon.com/glacier/pricing/). Note that archive retrieval
costs are complicated and [may be a lot more than you
expect](http://www.daemonology.net/blog/2012-09-04-thoughts-on-glacier-pricing.html).
Files are uploaded in chunks, so uploading an archive can cause many
requests.  The default size of the parts is determined by the boto library;
check `DefaultPartSize` in
[the documentation](http://boto.readthedocs.org/en/latest/ref/glacier.html#module-boto.glacier.vault).  [Changes have been proposed to this tool in order to allow the user
to specify the chunk size, but they have not been merged
yet.](https://github.com/basak/glacier-cli/pull/24)

Installation
------------

glacier-cli and its dependencies are pure Python packages
and it should be straightforward to install them on a system with
standard Python tools.
It was originally developed for Python 2, but it is possible to
get it working with Python 3 too.


### Installation with `pip`

It is recommended (but not required) to install glacier-cli
in a virtual environment (e.g. using something like
[`virtualenv`](https://virtualenv.pypa.io/en/latest/),
[`venv`](https://docs.python.org/3/library/venv.html),
[`conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html),
...).
This allows managing glacier-cli and its dependencies
in isolation and avoids conflicts with other packages and tools.

These virtual environment systems come with `pip`
(the standard Python package manger) out of the box,
which is the easiest way to install glacier-cli including
its dependencies.
If you don't use a virtual environment, it is still recommended
to at least use `pip`.

Install glacier-cli using `pip` (preferably in a virtual environment)
with one of these methods:

- Installation from source: make a local clone of this repository and install it:

        git clone git://github.com/basak/glacier-cli.git
        cd glacier-cli
        pip install .

- Installation directly from GitHub repo:

        pip install git+https://github.com/basak/glacier-cli.git


### Symlinks

The installation through pip will also create
a command line tool `glacier-cli` in the `bin` folder
of the virtual environment.
However, you probably want to be able to use it without first
activating the virtual environment.
Also, if you want to use it with `git-annex` (see lower), it should be
available under the name `glacier` in your `PATH`.

Create appropriate symlinks to achieve this.
The details of this largely depend on your setup or workflow,
but here are some examples as inspiration
(to be executed from within the virtual environment):

- if `~/bin` is in your `PATH`:

        ln -s $(which glacier-cli) ~/bin/glacier

- to make it available globally to all users:

        sudo ln -s $(which glacier-cli) /usr/local/bin/glacier




Integration with git-annex
--------------------------

Using glacier-cli via [git-annex][git-annex] is the easiest way to use Amazon
Glacier from the CLI.

git-annex now has native glacier-cli integration.  See the [git-annex Glacier
documentation](http://git-annex.branchable.com/special_remotes/glacier/) and
[tutorial](http://git-annex.branchable.com/tips/using_Amazon_Glacier/)
for details.

You probably want to set git-annex to only use glacier as a last resort in
order to control your costs:

    git config remote.glacier.annex-cost 1000

Copying to the remote works as normal. Retrieving from the remote initially
fails after a job is queued. If you try again after the job is complete
(usually around four hours), then retrieval should work successfully. You can
monitor the status of the jobs using `glacier job list`; when the job status
changes from `p` (pending) to `d` (done), a retrieval should work. Note that
jobs expire from Amazon Glacier after around 24 hours or so.

`glacier checkpresent` cannot always check for certain that an archive
definitely exists within Glacier. Vault inventories take hours to retrieve,
and even when retrieved do not necessarily represent an up-to-date state. For
this reason and as a compromise, `glacier checkpresent` will confirm to
git-annex that an archive exists if it is known to have existed less than 60
hours ago. You may override this permitted lag interval with the `--max-age`
option to `glacier checkpresent`.

Commands
--------

* <code>glacier vault list</code>
* <code>glacier vault create <em>vault-name</em></code>
* <code>glacier vault sync [--wait] [--fix] [--max-age <em>hours</em>] <em>vault-name</em></code>
* <code>glacier archive list <em>vault-name</em></code>
* <code>glacier archive upload [--name <em>archive-name</em>] <em>vault-name</em> <em>filename</em></code>
* <code>glacier archive retrieve [--wait] [-o <em>filename</em>] [--multipart-size <em>bytes</em>] <em>vault-name</em> <em>archive-name</em></code>
* <code>glacier archive retrieve [--wait] [--multipart-size <em>bytes</em>] <em>vault-name</em> <em>archive-name</em> [<em>archive-name</em>...]</code>
* <code>glacier archive delete <em>vault-name</em> <em>archive-name</em></code>
* <code>glacier job list</code>

Delayed Completion
------------------
If you request an archive retrieval, then this requires a job which will take
some number of hours to complete. You have one of two options:

1. If the command fails with a temporary failure&mdash;printed to `stderr` and
   with an exit status of `EX_TEMPFAIL` (75)&mdash;then a job is pending, and
   you must retry the command until it succeeds.
2. If you prefer to just wait, then use `--wait` (or retry with `--wait` if you
   didn't use it the first time). This will just do everything and exit when it
   is done. Amazon Glacier jobs typically take around four hours to complete.

Without `--wait`, glacier-cli will follow this logic:

1. Look for a suitable existing archive retrieval job.
2. If such a job exists and it is pending, then exit with a temporary failure.
3. If such a job exists and it has finished, then retrieve the data and exit
   with success.
4. Otherwise, submit a new job to retrieve the archive and exit with a
   temporary failure. Subsequent calls requesting the same archive will find
   this job and follow these same four steps with it, resulting in a downloaded
   archive when the job is complete.

Cache Reconstruction
--------------------

glacier-cli follows the [XDG Base Directory
Specification](http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html)
and keeps its cache in `${XDG_CACHE_HOME:-$HOME/.cache}/glacier-cli/db`.

After a disaster, or if you have modified a vault from another machine, you can
reconstruct your cache by running:

    $ glacier vault sync example-vault

This will set off an inventory job if required. This command is subject to
delayed completion semantics as above but will also respond to `--wait` as
needed.

By default, existing inventory jobs that completed more than 24 hours ago are
ignored, since they may be out of date. You can override this with
<code>--max-age=<em>hours</em></code>. Specify `--max-age=0` to force a new
inventory job request.

Note that there is a lag between creation or deletion of an archive and the
archive's corresponding appearance or disappearance in a subsequent inventory,
since Amazon only periodically regenerates vault inventories. glacier-cli will
show you newer information if it knows about it, but if you perform vault
operations that do not update the cache (eg. on another machine, as another
user, or from another program), then updates may take a while to show up here.
You will need to run a `vault sync` operation after Amazon have updated your
vault's inventory, which could be a good day or two after the operation took
place.

If something doesn't go as expected (eg. an archive that glacier-cli knows it
created fails to appear in the inventory after a couple of days, or an archive
disappears from the inventory after it showed up there), then `vault sync` will
warn you about it. You can use `--fix` to accept the correction and update the
cache to match the official inventory.

Addressing Archives
-------------------

Normally, you can just address an archive by its name (which, from Amazon's
perspective, is the Glacier archive description).

However, you may end up with multiple archives with the same name, or archives
with no name, since Amazon allows this. In this case, you can refer to an
archive by ID instead by prefixing your reference with `id:`.

To avoid ambiguity, prefixing a reference with `name:` works as you would
expect. If you end up with archive names or IDs that start with `name:` or
`id:`, then you must use a prefix to disambiguate.

Using Pipes
-----------

Use `glacier archive upload <vault> --name=<name> - ` to upload data from
standard input. In this case you must use `--name` to name your archive
correctly.

Use `glacier archive retrieve <vault> <name> -o-` to download data to standard
output. glacier-cli will not output any data to standard output apart from the
archive data in order to prevent corrupting the output data stream.

Future Directions
-----------------

* Add resume functionality for uploads and downloads

Contact
-------

* For bugs or feature requests please create a [glacier-cli github
  issue](https://github.com/basak/glacier-cli/issues).
