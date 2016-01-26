# OpenDKIM genkeys tool

Copyright 2016 Todd T Knarr &lt;<tknarr@silverglass.org>&gt;

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License (included in
LICENSE.md) for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see [http://www.gnu.org/licenses/](http://www.gnu.org/licenses/)

## Usage

    genkeys.py [-h] [-n] [-v] [--no-dns] [selector]

*   `-h` : display help
*   `-n` : use next month instead of this month when automatically generating a selector
*   `-v` : log additional informational messages while processing
*   `--no-dns` : do not attempt to automatically update DNS records

If no `selector` is specified, one will be automatically generated based on the current
month (or the next month if `-n` was used). Standard practice would be to omit the
selector and use automatic date-based selectors (which have the format `YYYYMM`, eg.
`201605` for May of 2016), using `-n` if you're generating the keys for next month
ahead of time and need the selector to reflect the month you're generating for rather
than the current one. If `--no-dns` is used you'll have to manually update the DNS
records with the data in the generated `.txt` files, otherwise the script will try
to automatically update the DNS records for all domains it's got DNS API support and
information for.

The following options are also available for development and debugging. They should
not be used under normal circumstances ("If you don't know what it's going to do, _DO
NOT_ push the button." is a good rule to live by).

*   `--debug` : enable logging of additional debugging information and disable actual actions
    in the DNS API modules (error checking will occur, but no attempt will be made to actually
    actually update the records)
*   `--use-null` : silently use the null DNS API instead of the defined one for all domains

## Configuration files

### `dnsapi.ini`

_TODO_

### `domains.ini`

_TODO_

# Generated files

## Private and public key files

_TODO_

## Updated `opendkim` daemon configuration files

_TODO_

# Standard installation and workflow

The recommended setup is to have two directories, a binaries directory where the
`genkeys.py` script and the various `dnsapi_*.py` scripts are installed and a data
directory where your configuration files and data files are located. The binaries
directory doesn't need to be in your path, if it isn't you may want an alias or
small wrapper script so you don't have to use the full path to `genkeys.py` every
time. You can put the binaries directly in the data directory, but it increases the
clutter and the changes that you'll accidentally delete the script files.

Once the two configuration files are set up, you just run `genkeys.py` with the `-n`
option at the end of the month. That will generate new private and public key files
for every domain listed using the selector value for next month and automatically
add the appropriate public-key TXT records to all domains that you've set up API
information for. For domains that either don't have a DNS API available or you don't
have (or haven't configured) information for, you'll have to update the DNS data
by hand to create the TXT records. The data for the records is in the `*.YYYYMM.txt`
files created by the script. Use the `opendkim-testkey` command to verify the records
are OK.

To activate use of the new selector and records on the first of the new month, first
upload the `*.YYYYMM.key` files containing the private keys to the server keys directory
(usually `/etc/opendkim/keys`). Then upload the newly-updated `signing.table` and
`key.table` to the server OpenDKIM configuration directory (usually `/etc/opendkim`).
Restart the OpenDKIM daemon and check for errors in the logs. A last check would be
to send an email from one OpenDKIM-enabled domain handled by your servers to another,
verifying that it gets through without any errors, that the signature was checked and
passed and that the DKIM-Signature and Authentication-Results headers are present and
sensible.

After a week or so, delete the now-outdated TXT records for the old selector from the
DNS data. That gives time for any mail stuck in a queue to get cleared out before the
necessary records disappear.

## Alternative workflows

One alternative method is to run `genkeys.py` without any options at the point where you
want to generate new keys, then immediately upload the new `.key` and `.table` files
and restart the OpenDKIM daemon to start using them. You'd use this if you're not following
a rigorous monthly key rotation schedule.

If you want to set your own selector values, say if management dictates or you need to rotate
keys more often than every month, you can pass a selector value as a command-line parameter.
`genkeys.py` will use that value as the selector instead of generating one.
