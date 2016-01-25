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

* `-h` : display help
* `-n` : use next month instead of this month when automatically generating a selector
* `-v` : log additional informational messages while processing
* `--no-dns` : do not attempt to automatically update DNS records

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
not be used under normal circumstances ("Do _not_ push the button when you don't know
exactly what it does").

* `--debug` : enable logging of additional debugging information and disable actual actions
    in the DNS API modules (error checking will occur, but no attempt will be made to actually
    actually update the records)
* `--use-null` : silently use the null DNS API instead of the defined one for all domains

## Configuration files

### `dnsapi.ini`

_TODO_

### `domains.ini`

_TODO_

## Generated files

_TODO_

### Private and public key files

_TODO_

### Updated `opendkim` daemon configuration files

_TODO_

## Standard workflow

_TODO_

## Writing a new DNS API modules

_TODO_
