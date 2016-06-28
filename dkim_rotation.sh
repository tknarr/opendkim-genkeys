#!/bin/sh

#    OpenDKIM genkeys tool
#    Copyright (C) 2016 Todd Knarr <tknarr@silverglass.org>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# This script gets run from the crontab of the user responsible for generating new
# OpenDKIM keys.

# Edit this to point to the genkeys.py script, including it's path if it's not
# in the PATH. Remove the -n switch if you are running this script at the start
# of the month the keys are for.
GENKEY="genkeys.py -n"

# Edit this space-separated list of the usernames, hosts and directories to upload
# OpenDKIM keys to after generating them. Do not use trailing slashes.
TARGETS="user1@host1:relative/directory user2@host2:/absolute/directory"

# Edit to reflect the location you generate keys in
cd /key/location

# Record the selector for use during the upload
selector=`${GENKEY} --selector`

# Generate the keys and tables
${GENKEY} || exit 1
# Set permissions correctly
for x in *.${selector}.key
do
    if [ -f $x ]
    then
        chmod u=rw,go= $x
    fi
done
echo "DKIM ${selector} key generation completed successfully."

# Do each upload, including the uploaded marker only if the upload succeeded
for x in $TARGETS
do
    h=`echo $x | cut -d: -f1`
    d=`echo $x | cut -d: -f2-`
    scp *.${selector}.key key.table signing.table ${h}:${d}/ && \
        ssh -x ${h} touch ${d}/.uploaded && \
        echo "DKIM key upload to $x completed successfully."
done

echo "DKIM key rotation completed successfully."

exit 0
