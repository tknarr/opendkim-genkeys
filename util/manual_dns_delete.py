#!/usr/bin/python
# -*- coding: utf-8 -*-

#    OpenDKIM genkeys - list zones and zone IDs for CloudFlare account
#    Copyright (C) 2017 Todd Knarr <tknarr@silverglass.org>

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

import argparse
import datetime
import glob
import importlib
import logging
import os
import os.path
import string
import sys

# Internal settings, should not need changed
domain_filename = 'domains.ini'
dns_api_defs_filename = 'dnsapi.ini'


def process_ini_file( filename, critical = True ):
    # Snarf in the contents
    try:
        ini_file = open( filename, 'r' )
        input_lines = ini_file.readlines()
    except IOError as e:
        if critical:
            logging.critical( "Error accessing file %s", filename )
            logging.error( "%s", str( e ) )
        else:
            logging.warning( "Error accessing file %s", filename )
            logging.warning( "%s", str( e ) )
        return None
    ini_data = []
    for line in input_lines:
        fields = line.split()
        if fields != None and len( fields ) > 0 and len( fields[0] ) > 0 and fields[0][0] != '#':
            ini_data.append( fields )
    return ini_data


def fields_to_line( fields ):
    line = ""
    for field in fields:
        if len( line ) > 0:
            line += '\t'
        if isinstance( field, datetime.datetime ):
            line += field.strftime( '%Y-%m-%dT%H:%M:%S' )
        else:
            line += str( field )
    return line


def find_dnsapi_modules( pn ):
    # Go through all possible names (pulled from what's mentioned in the
    # dnsapi.ini file) and for each one X see if we can load a module named
    # dnsapi_X (file will be dnsapi_X.py).
    dnsapis = { }
    possible_names = pn
    # Make sure null is included
    if 'null' not in possible_names:
        possible_names.append( 'null' )
    for api_name in possible_names:
        module_name = "dnsapi_" + api_name
        try:
            module = importlib.import_module( module_name )
        except ImportError as e:
            module = None
            logging.error( "Module %s for DNS API %s not found", module_name, api_name )
            logging.info( "%s", str( e ) )
        if module is not None:
            logging.debug( "DNS API module %s loaded", api_name )
            dnsapis[api_name] = module
    return dnsapis


# Set up command-line argument parser and parse arguments
parser = argparse.ArgumentParser( description = "Generate OpenDKIM key data for a set of domains" )
parser.add_argument( "-v", "--verbose", dest = 'log_info', action = 'store_true',
                     help = "Log informational messages in addition to errors" )
parser.add_argument( "domain", default = None, help = "Domain to delete entry from" )
parser.add_argument( "selector", default = None, help = "Selector to use" )
parser.add_argument( "data", nargs = argparse.REMAINDER, help = "API-specific arguments" )
args = parser.parse_args()

if args.log_info:
    level = logging.INFO
else:
    level = logging.WARN

logging.basicConfig( level = level, format = "%(levelname)s: %(message)s" )

# Check for required arguments
if args.domain is None:
    logging.error( "Insufficient arguments: no domain name given" )
    sys.exit( 1 )
if args.selector is None:
    logging.error( "Insufficient arguments: no selector given" )
    sys.exit( 1 )
if len( args.data ) == 0:
    logging.error( "Insufficient arguments: no record data given" )
    sys.exit( 1 )

# Process dnsapi.ini
dnsapi_info = { }  # Key = DNS API name, Value = remainder of fields
dnsapi_data = process_ini_file( dns_api_defs_filename )
if dnsapi_data is None:
    logging.critical( "No DNS API definitions found in %s", dns_api_defs_filename )
    sys.exit( 1 )
else:
    for item in dnsapi_data:
        dnsapi_info[item[0]] = item[1:len( item )]
# Insure we have the null API
if dnsapi_info['null'] is None:
    dnsapi_info['null'] = []

# Process domains.ini
domain_data = process_ini_file( domain_filename )
if domain_data is None:
    logging.critical( "No domain definitions found in %s", domain_filename )
    sys.exit( 1 )
# Make all domains with no API specified use the null API
for item in domain_data:
    if len( item ) < 3 or item[2] is None:
        item[2] = 'null'
# We'll need a list of all the key names used by domains
key_names = []
for item in domain_data:
    if item[1] not in key_names:
        key_names.append( item[1] )

# Check for our DNS API modules. If we don't have any, there's no sense in
# trying to go further.
dnsapis = find_dnsapi_modules( dnsapi_info.keys() )  # Key = DNS API name, Value = module
if len( dnsapis ) == 0:
    logging.error( "No DNS API modules found" )
    sys.exit( 1 )

dnsapi_domain_data = None
dnsapi_name = 'null'
for item in domain_data:
    if item[0] == args.domain:
        dnsapi_name = item[2]
        dnsapi_domain_data = item[3:len( item )]
        break
if dnsapi_domain_data is None:
    logging.error( "Domain %s data not found", args.domain )
    sys.exit( 1 )

if dnsapi_name not in dnsapis:
    logging.error( "DNS API module %s not found", dnsapi_name )
    sys.exit( 1 )
dnsapi_module = dnsapis[dnsapi_name]
dnsapi_data = dnsapi_info[dnsapi_name]

record = [ args.domain, args.selector, None ]
record.extend( args.data )

result = dnsapi_module.delete( dnsapi_data, dnsapi_domain_data, record, False )
if result is None:
    logging.info( "No support for removing old record for %s:%s via %s API",
                  record[0], record[1], dnsapi_name )
elif result:
    logging.info( "Removing %s:%s", record[0], record[1] )
else:
    logging.error( "Error removing old record for %s:%s via %s API",
                   record[0], record[1], dnsapi_name )

sys.exit( 0 )
