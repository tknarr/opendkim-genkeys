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

# This script gets run from the OpenDKIM user's crontab at a time after new
# key files are uploaded.

# Replace with the location DKIM files are uploaded to
SRC_DIR=/upload/location

# Edit if needed for the actual location of OpenDKIM's configuration directory
cd /etc/opendkim

# Check for a successful upload, so we don't accidentally process leftovers from
# a previous upload.
if [ ! -f ${SRC_DIR}/.uploaded ]
then
   echo "Uploaded marker not present, aborting."
   exit 1
fi

# Copy the .key files to the key directory.
for x in ${SRC_DIR}/*.key
do
    if [ -f $x ]
    then
        cp $x keys/ || exit 1
        chmod u=rw,go= $x || exit 1
    fi
done

# Back up the old .table files
for x in *.table
do
    if [ -f $x ]
    then
        cp -p $x ${x}.bak || exit 1
    fi
done
# Copy the new .table files
for x in ${SRC_DIR}/*.table
do
    if [ -f $x ]
    then
        cp $x ./ || exit 1
        chmod u=rw,go=r $x || exit 1
    fi
done

# Clear out the old files if everything succeeded
rm -f ${SRC_DIR}/*.key ${SRC_DIR}/*.table ${SRC_DIR}/.uploaded || exit 1

echo "DKIM key update completed successfully."

exit 0
