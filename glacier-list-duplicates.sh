#!/bin/sh
set -e

# Usage:
# sh glacier-list-duplicates.sh <vault>
# sh glacier-list-duplicates.sh <vault> | xargs -n1 glacier archive delete <vault>

# This is a helper wrapper around glacier-cli. If your Glacier archive contains
# archives with identical data where an identical archive name indicates
# identical archive data, then this tool will list archive ids suitable for
# deletion, retaining (ie. not listing) one of each identical archive id. This
# is useful to work around this bug:
# http://git-annex.branchable.com/bugs/Glacier_remote_uploads_duplicates/

vault="$1"

all=$(mktemp list-duplicates.XXXXXXXXXX)
keep=$(mktemp list-duplicates.XXXXXXXXXX)

trap "rm -f -- '$all' '$keep'" EXIT

glcr archive list --force-ids "$vault"|sort -k2|uniq -f1 -D > "$all"
uniq -f1 < "$all" | cut -f1 | sort > "$keep"
cut -f1 < "$all" | sort | comm -23 - "$keep"
