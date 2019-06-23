# OpenDKIM genkeys tool

[![Latest GitHub release](https://img.shields.io/github/release/tknarr/opendkim-genkeys.png)](https://github.com/tknarr/opendkim-genkeys/releases/latest)

Copyright &copy; 2016 Todd T Knarr &lt;<tknarr@silverglass.org>&gt;
Copyright &copy; 2019 Noel Kuntze &lt;<noel.kuntze+github@thermi.consulting>&gt;

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

## Summary

A tool to help with the generation of DKIM keys for use with OpenDKIM. The standard
`opendkim-genkey` tool is awkward to use, it only generates key data for a single
domain at a time and the file for the public key part that needs populated into the
DNS data, while exactly what's needed for use with BIND, isn't in a format usable by
the web-based interfaces to most DNS hosting providers. It also requires manually
updating the DNS information, a significant task when dealing with the common situation
of multiple domains. This awkwardness occurs repeatedly, since the recommendation for
DKIM is that keys be rotated (new keys generated and old keys retired) every month.

This tool takes a configuration detailing all the domains that need keys and generates
all the keys in a single operation, and for supported DNS hosting provider APIs will
automatically add the new keys to DNS for you. In the process it'll regenerate the two
configuration files OpenDKIM needs that depend on the set of domains and keys involved
and leave you with reasonably clean `.txt` files containing the DNS information for
each domain. File names follow a format that should eliminate overwriting of files
unless you deliberately ask for that.

You will need to be familiar with DKIM and have at least a general familiarity with the
OpenDKIM package before using this tool.

## Usage

    usage: genkeys.py [-h] [-v] [-n] [-s] [--working-dir WORKING_DIR]
                      [--opendkimDir OPENDKIM_DIR] [--key-directory KEY_DIRECTORY]
                      [--config CONFIG] [--no-dns] [--no-cleanup] [--debug]
                      [--use-null] [--no-write-file] [--store-in-new-files]
                      [--version]
                      [selector] ...

    Generate OpenDKIM key data for a set of domains

    positional arguments:
      selector              Selector to use
      domains               List of domains to process

optional arguments:
*  `-h`, `--help`           show this help message and exit
*  `-v`, `--verbose`        Log informational messages in addition to errors
*  `-n`, `--next-month`     Use next month's date for automatically-generated\
                            selectors
*  `-s`, `--selector`       Causes the generated selector to be output
*  `--working-dir`      WORKING_DIR\
                            Set the working directory for DKIM data files
*  `--opendkimDir`      OPENDKIM_DIR\
                            The directory of the opendkim configuration
*  `--key-directory`    KEY_DIRECTORY\
                            The directory of the opendkim keys directory
*  `--config`           CONFIG\
                            The path to the configuration file
*  `--no-dns`               Do not update DNS data
*  `--no-cleanup`           Do not delete old key files
*  `--debug`                Log debugging info
*  `--use-null`             Silently use the null DNS API instead of the real API
*  `--no-write-file`        Disable writing any file changes to the key or signing\
                            table, or any of the yml files.
*  `--store-in-new-files`   Do not overwrite old key and signing table files or\
                            dns_update_data.yml files, but write new ones
*  `--version`              Display the program version


If no `selector` is specified, one will be automatically generated based on the current
month (or the next month if `-n` was used). Standard practice would be to omit the
selector and use automatic date-based selectors (which have the format `YYYYMM`, eg.
`201605` for May of 2016), using `-n` if you're generating the keys for next month
ahead of time and need the selector to reflect the month you're generating for rather
than the current one. If `--no-dns` is used you'll have to manually update the DNS
records with the data in the generated `.txt` files, otherwise the script will try
to automatically update the DNS records for all domains it's got DNS API support and
information for. Normally if the resulting files would be overwritten the operation will
fail. The `-a` option will cause single-uppercase-letter suffixes on the selector to be
tried until filenames that do not exist are found or all 26 letters are exhausted before
failing. The suffix is per target domain, so files for different domains may end up with
different suffixes.

The `-s` option can be used to cause the tool to output the generated selector
on standard output for capture by a script. The `-n` option can be used in conjunction
with `-s`, other options will have no effect when `-s` is specified.
This is to assist with scripts to automatically upload the generated data files to a
server for installation.

The following options are also available for development and debugging. They should
not be used under normal circumstances ("If you don't know what it's going to do, _DO
NOT_ push the button." is a good rule to live by).

*   `--debug` : enable logging of additional debugging information and disable actual actions
    in the DNS API modules (error checking will occur, but no attempt will be made to actually
    actually update the records)
*   `--use-null` : silently use the null DNS API instead of the defined one for all domains

## Configuration files

### `dnsapi.yml`

This file defines the global information needed by all domains hosted somewhere that uses
a given API to allow programmatic updating of DNS records.

The file has to contain a dictionary structure in which each key is the name of a DNS API.
The key has to contain an arbitrary object. Its contents are passed to the DNS API when its
corresponding python module is called.

A valid file could have the following contents:
```
netcup:
- 22222
- myapiuser
- myapipassword
foo:
- bar
- baz
```

A DNS API with a particular name is supported by a module in a file named `dnsapi_X.py`,
where the X is replaced with the name in the first field of the API's line in `dnsapi.yml`.
The names are arbitrary but should be mnemonic, and they aren't hardcoded into the main
script in any way. Additional APIs can be supported merely by creating a `dnsapi_X.py` module
for them and adding an entry to `dnsapi.yml`, the main script will automatically load the
module as needed. Writing these scripts is beyond the scope of this document, you can find
information on the process in the wiki's
[Writing a new DNS API module](https://github.com/tknarr/opendkim-genkeys/wiki/Writing-a-new-DNS-API-module)
page.

### `domains.yml`

This file is the main one that ties domains, key files and DNS APIs together. 
Its contents are structured as follows:
```
arbitrary_domain_name:
  api: api_to_use_for_update
  dns_servers:
  - dns_server_1
  - dns_server_2
  - dns_server_n
another_arbitrary_domain_name:
...
```
A formal description would be:
* The file contains a dictionary of domain names whose DKIM records are to be updated
* Each key in the file maps to a dictionary that contains the API to use to update the DKIM record (api key in the dict) and a list of DNS servers that are to be checked for the existence of newly generated and sent DKIM records before they are used in the key.table file
[DNS APIs page](https://github.com/tknarr/opendkim-genkeys/wiki/DNS-APIs). If no DNS API name is
present, the script won't attempt to automatically update the DNS information and you'll need to
take the information from the generated public key file and update the DNS data manually. If a
DNS API name is present (and the information in `dnsapi.yml` and `domains.yml` is all correct),
the script will use the API to add the new DKIM record automatically (you can suppress this via
the `--no-dns` option).

### `opendkim-genkeys.yml`

This file contains the configuration of opendkim-genkeys in yaml format.
Its default location is `/etc/opendkim-genkeys.yml`. This can also be seen in the help message of the script.

The following keys exist:

* `opendkim_dir`                  Default: "/etc/opendkim"
                                  Description: Sets the directory in which the opendkim files are stored.
                                  It is assumed that the key table and signing table files are stored in that directory.
                                  It is also assumed that the directory "keys" below the opendkim directory contains all private keys.
* `working_dir`                   Default: ""
                                  Description: Sets the working directory into which opendkim-genkeys cd's into after parsing of the arguments
* `update_dns`                    Default: True
                                  Description: Whether to update any DNS records or not
* `domain_file_name`              Default: "domains.yml"
                                  Description: The file name in which the domains are stored for which keys should be generated
* `dns_api_defs_filename`         Default: "dnsapi.yml"
                                  Description: The file in which the DNS APIs are configured
* `dns_api_extra_data_file_name`  Default: "dnsapi_extra.yml"
                                  Description: DNS API modules can store data permanently in this file
* `dns_update_data_file_name`     Default: "dns_update_data.yml"
                                  Description: This file contains data describing the domain, selector and    creation date of any generated keys.
* `key_table`                     Default: "key.table"
                                  Description: The opendkim key table.
* `signing_table`                 Default: "signing.table"
                                  Description: The opendkim signing table.
* `key_directory`                 Default: "/etc/opendkim/keys"
                                  Description: The directory that contains any private keys
* `cleanup_file`"                 Default: True
                                  Description: Whether to remove outdated private keys.
* `day_difference`                Default: 70
                                  Description: The days that private keys stay around after they are not used anymore.
* `store_in_new_files`            Default: False
                                  Description: Whether to store the generated key and signing tables and the dns update data in files ending in the ".new" extension.
* `no_write_file`                 Default: False
                                  Description: Whether to write into any files at all
* `new_key_owner`                 Default: "opendkim"
                                  Description: The owner of any newly generated keys.
* `new_key_group`                 Default: "root"
                                  Description: The group of any newly generated keys.
* `new_key_mode`                  Default: 0o400
                                  Description: The Unix ACL (SRWX bits) for newly generated keys.
* `key_table_owner`               Default: "root"
                                  Description: The owner that the key.table file is supposed to have.
* `key_table_group`               Default: "root",
                                  Description: The group that the key.table file is supposed to have.
* `key_table_mode`                Default: 0o400,
                                  Description: The Unix ACL (SRWX bits) of the key.table file.
* `signing_table_owner`           Default: "root"
                                  Description: The owner that the signing.table file is supposed to have.

* `signing_table_group`           Default: "root",
                                  Description: The group that the signing.table file is supposed to have.

* `signing_table_mode`            Default: 0o400
                                  Description: The Unix ACL (SRWX bits) of the signing.table file.

# Generated files

### `dns_update_data.yml`

This file records information about the records created for each domain where DNS
servers were updated. If it doesn't exist, it will be created (warning messages will
be issued, but they're strictly because a template file should have existed).

An example file is provided purely for informational purposes. It's best to delete
it before using the package, allow `genkeys.py` to create it from scratch during the
first run.

### `dnsapi_extra.yml`

This file contains data that a DNS API module wanted to store permanently.
It contains a dictionary that maps DNS API module names to an arbitrary data structure.
The datat structure is defined and used by the DNS API module.

## Private keys
The script automatically generates new RSA keys for DKIM using openssl rsa. The corresponding
file's public keys are automaticlaly generated from the private keys.
Old private keys are automatically deleted after 70 days (the default).

## Updated `opendkim` daemon configuration files

OpenDKIM uses two configuration files to control what keys are used to sign outgoing
messages: `signing.table` and `key.table`. `signing.table` is the simplest one, the first
field is a pattern matching email addresses (usually `*@domain` to match all addresses
in a given domain) and the second field is a tag used to determine what key entry will
be used to sign messages matching the first field's pattern. The tag is arbitrary, this
script generates one based on the domain name.

`key.table` has one entry per tag mentioned in `signing.table`. The first field is the
tag, the second is a colon-delimited set of information: a domain name, a selector value
and the name of a key file to use for signing. Note that the domain doesn't have to be
the domain of the email sender, it's simply the domain under which DKIM public keys for
signature validation will be looked up. This script configures things so that the DKIM
public keys will be under the domain the email is from. The key files in the final field
will be located in `/etc/opendkim/keys`, the standard location, and follow the pattern of
the key name, a dot, the selector value and the suffix `.key`.

The script completely regenerates these two files based on the information in `domains.yml`
and the selector value (whether auto-generated or supplied), so once the private keys are
uploaded to `/etc/opendkim/keys` you can just upload the new `signing.table` and `key.table`
files to `/etc/opendkim` and restart the OpenDKIM daemon to begin using the new keys for
outgoing mail.

Neither of these files affects checking of incoming mail, that's done based on the domain
and selector information the sender's DKIM software put into the signature header.

# Standard installation and workflow

The recommended setup is to have two directories, a binaries directory where the
`genkeys.py` script and the various `dnsapi_*.py` scripts are installed and a data
directory where your configuration files and data files are located. The binaries
directory doesn't need to be in your path. You can put the binaries directly in the
data directory, but it increases the clutter and the chances that you'll accidentally
delete the script files. A better organization is to have the binaries and data
directories as siblings beneath a parent directory dedicated to this software. Copy
the contents of the `src` and `util` directories of the downloaded package into the
binaries directory, and the contents of the `data` directory into the data directory.
Then `cd` to the data directory and run the `initialize_data_dir.sh` script to set up
the initial data files correctly.

Edit `dnsapi.yml` and `domains.yml` and enter the information for your accounts
and domains at your DNS service providers. If you have domains at DNS service providers
that aren't supported by the program, leave the DNS API information in `domains.yml`
blank for them and keys will be generated so you can set the TXT records manually.
You can delete the `dnsapi.yml` entries for services that you don't use if you wish,
but make sure to retain the `null` API entry because it's used implicitly for domains
hosted on services that don't use a supported API.

Once the two configuration files are set up, you just `cd` to the data directory and
run `genkeys.py` with the `-n` option at the end of the month. That will generate new
private and public key files for every domain listed using the selector value for next
month and automatically add the appropriate public-key TXT records to all domains that
you've set up API information for. For domains that either don't have a DNS API available
or you don't have (or haven't configured) information for, you'll have to update the DNS
data by hand to create the TXT records.

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
`genkeys.py` will use that value as the selector instead of generating one. The `dkim_rotation.sh`
script uses this to allow getting and displaying the selector value and then guaranteeing
that the displayed value will be the one actually used.

## Automation scripts

After editing and testing, the two automation scripts should be installed in crontab as
described in each script's explanation.

### `dkim_rotation.sh`

This script runs on the system where you generate new DKIM keys. It generates new keys
and then uploads them to a staging location on the mail servers. Normally it's run
from crontab as a normal user, either on a day late in the month (to prepare keys for
the next month) or early in the AM on the first of the month. I recommend running the
script towards the end of the month to prepare for the next month, this gives time to
check the results and catch any problems that might crop up. An example crontab entry
would be:

    31 8 25 * * /usr/local/sbin/dkim_rotation.sh

This runs the script at 8:30am on the 25th of the month. That gives you between 3 and
6 days to check the results before they are applied.

To prepare the script for your installation you need to edit a few bits of data to
reflect the users and directories on your systems.

    GENKEY="genkeys.py -n"

Edit this line to include the path to `genkeys.py` if it's not in the PATH of the
user the script. If you will be running the script on the first of the month the keys
are for, rather than near the end of the month before, edit the `-n` switch out of
the quoted string.

    TARGETS="user1@host1:relative/directory user2@host2:/absolute/directory"

`TARGETS` is a space-separated list of `scp` user/host/paths that the DKIM files are
to be uploaded to. The syntax for each entry is the syntax used in the `scp` command
to specify the destination to copy to. Omit the trailing slashes from the directory
paths, the script is coded to add them where needed. You may omit the user portion and
the `@` character if you'll be uploading to the same username as the script runs under
or if your SSH configuration is set up with the desired username for that host. The
entries will work exactly like scp would if you specified the entry as the destination,
use this as a guide to what you can do in each entry.

    cd /key/location

Edit `/key/location` to reflect the directory you want to use to generate the keys on
the local system.

The output of the script will be mailed to the user it runs under by the cron system.
Set up any mail aliases or forwarding needed to get this output to the person responsible
for key rotation so they can see any errors that occurred and get the reminder to check
the mail servers for correct uploads.

### `dkim_update.sh`

This script runs on each mail server that handles outgoing mail. It must be run as
root to allow it to restart the OpenDKIM service. Normally it's run from crontab
early in the AM on the first of the month, after the `dkim_rotation.sh` script has been
run. If `dkim_rotation.sh` is run late in the previous month the exact timing doesn't
matter. An example crontab entry would be:

    2 0 1 * * /usr/local/sbin/dkim_update.sh

This runs the script at 2 minutes past midnight on the 1st of the month.

The script will remove the uploaded copies if installation into the running OpenDKIM
instance succeeds, to prevent later runs from picking up stale files by accident.

To prepare the script for your installation a couple of pieces of data at the start of
the script need to be edited to reflect the directories in use on your system.

    SRC_DIR=/upload/location

Edit this to reflect the directory the files were uploaded to on this host by the
`dkim_rotation.sh` script.

    DKIM_USER=opendkim
    DKIM_GROUP=opendkim

Edit these entries to reflect the user and group names used by the OpenDKIM software
if necessary. The settings here are the standard ones.

    cd /etc/opendkim

Edit this directory if needed to reflect where OpenDKIM's configuration directory
is. The setting here is the standard location.

The output of this script will be mailed to the root user by the cron system, so you
must make sure root's mail is routed to someone to review for errors.
