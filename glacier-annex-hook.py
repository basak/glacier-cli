#!/usr/bin/env python

# Copyright (c) 2012 Peter Todd
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

import sys
import os

def print_usage():
    sys.exit(\
"""\
Usage: %s <path-to-glacier-cli> <vault-name> <hook-type> <hook-args>)

See glacier-cli README for more information.""")

try:
    (glacier_cli_path, vault_name, action) = sys.argv[1:4]
except ValueError:
    print_usage()

if action in ('store','retrieve'):
    try:
        (annex_key, annex_file) = sys.argv[4:]
    except ValueError:
        print_usage()
elif action in ('remove','checkpresent'):
    try:
        (annex_key,) = sys.argv[4:]
    except ValueError:
        print_usage()
else:
    print_usage()


# Determine if the annex key is referring to a zero length file by examining
# the size field.
key_is_empty = None
for field in annex_key.split('-')[1:-1]:
    if field and field[0] == 's':
        assert(key_is_empty is None)
        if int(field[1:]) == 0:
            key_is_empty = True
        else:
            key_is_empty = False

# If the size field couldn't be found it's probably because this is a pre-v2
# annex; assume the key isn't empty.
if key_is_empty is None:
    key_is_empty = False


if action == 'store':
    if key_is_empty:
        sys.exit() # storing an empty key is always a success
    else:
        os.execv(glacier_cli_path, (
            glacier_cli_path, 'archive', 'upload', '--name=%s' % annex_key, vault_name, annex_file))
elif action == 'retrieve':
    if key_is_empty:
        # Create the empty file ourselves
        open(annex_file,'w').close()
        sys.exit()
    else:
        os.execv(glacier_cli_path, (glacier_cli_path, 'archive', 'retrieve', '-o', annex_file, vault_name, annex_key))
elif action == 'remove':
    if key_is_empty:
        sys.exit() # removal "works", although does nothing
    else:
        os.execv(glacier_cli_path, (glacier_cli_path, 'archive', 'delete', vault_name, annex_key))
elif action == 'checkpresent':
    if key_is_empty:
        # The empty key is always present.
        print(annex_key)
        sys.exit()
    else:
        os.execv(glacier_cli_path, (glacier_cli_path, 'archive', 'checkpresent', '--quiet', vault_name, annex_key))
else:
    # Action already checked for every case above; shouldn't be possible to get here.
    assert False
