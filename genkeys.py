#!/usr/bin/python
# -*- coding: utf-8 -*-

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

import sys
import os
import os.path
import glob
import datetime
import logging
import argparse
import importlib


# Settings, edit as appropriate for your environment

# Directory that OpenDKIM key files will be placed in on the mail server
opendkim_dir = '/etc/opendkim/keys'

# Set this to True if you never want to have the script update DNS records for you
never_update_dns = False

# End of normal configuration settings
# ======================================================================

# Internal settings, should not need changed
domain_filename = 'domains.ini'
dns_api_defs_filename = 'dnsapi.ini'


VERSION = '1.4'

# Creates the private-key file, and the public-key txt-record file in chunked (BIND) form.
# Returns a public key record dict, or None in the event of an error:
#   selector: real selector value used if asked to avoid overwrites instead of failing
#   plain:    unquoted unchunked data
#   chunked:  BIND-format quoted chunked data
def gen_key( target_name, selector, find_unused_selector = False ):
    # Check for existence of resulting files and handle it
    suffix_list = [ '' ]
    if find_unused_selector:
        suffix_list += list( string.ascii_uppercase )
    real_selector = None
    for suffix in suffix_list:
        rs = selector + suffix
        private_key_filename = target_name +  "." + rs + ".key"
        public_key_filename = target_name + "." + rs + ".txt"
        if ( not os.path.exists( private_key_filename ) ) and ( not os.path.exists( public_key_filename ) ):
            real_selector = rs
            break
    if real_selector == None:
        logging.critical( "Files for %s selector %s already exist", target_name, selector )
        return None
    if real_selector != selector:
        logging.warning( "Avoided overwriting keys for %s by using selector %s", target_name, real_selector )

    # Use the OpenDKIM tool to generate the key data files
    try:
        wait_status = os.system( "opendkim-genkey -b 2048 -r -s " + selector + " -d " + target_name )
    except OSError as e:
        logging.critical( "Error running opendkim-genkey" )
        logging.error( "%s", str( e ) )
        return None
    status = ( wait_status & 0xFF00 ) >> 8
    if status != 0:
        logging.critical( "Error status %d returned by opendkim-genkey", status )
        return None

    # The private key always ends up as target_name.selector.key
    try:
        os.rename( selector + ".private", private_key_filename )
    except OSError as e:
        logging.critical( "Cannot rename the private key file %s.private", selector )
        logging.error( "%s", str( e ) )
        return None

    # Read opendkim-genkey's file and reformat the public key

    # Snarf in the public key file for processing
    try:
        pubkey_file = open( selector + ".txt", 'r' )
    except IOError as e:
        logging.critical( "Error accessing the public key file %s.txt", selector )
        logging.error( "%s", str( e ) )
        return None
    input_text = pubkey_file.read()
    pubkey_file.close()
    if len( input_text ) <= 0:
        logging.critical( "No input found" )
        return None

    # Find the first double-quote, and the double-quote after it. If we can't
    # find the first one, we're either done (if we processed at least one chunk
    # of data) or we have a syntax problem. If we can't find the second one, we
    # definitely have a syntax problem. If we found both, extract the chunk of
    # data between them and add it to the accumulated key data value (with or
    # without the enclosing quotes and spacing depending on the format). Repeat
    # until we can't find an opening double-quote.
    value = ''
    chunked_value = ''
    start = 0
    while start >= 0:
        first_quote = input_text.find( '"', start )
        if first_quote >= start:
            second_quote = input_text.find( '"', first_quote + 1 )
        else:
            if len( value ) == 0:
                # Error, we couldn't find the start
                logging.critical( "Cannot find start of DNS record value" )
                return None
            else:
                # We're done when we can't find the start of the next chunk
                break
        if second_quote >= 0:
            # Unchunked form
            value += input_text[first_quote+1:second_quote]
            # Chunked form
            if len( chunked_value ) > 0:
                chunked_value += ' '
            chunked_value += input_text[first_quote:second_quote+1]
            start = second_quote + 1
        else:
            logging.error( "Syntax error in record data: no closing quote found" )
            break

    # We should've found at least one chunk of key data
    if len( value ) == 0:
        logging.critical( "No DNS record value found" )
        return None

    output_file = open( public_key_filename, 'w' )
    output_file.write( chunked_value + '\n' )
    output_file.close()

    # Clean up the file opendkim-genkey created, we don't need it anymore
    try:
        os.remove( selector + ".txt" )
    except OSError as e:
        logging.error( "Could not delete origin file %s.txt", selector )
        logging.error( "%s", str( e ) )
        return None

    return { 'selector': real_selector, 'plain': value, 'chunked': chunked_value }


def split_ini_line( linetext ):
    l = linetext.split()
    if len(l) == 0 or len(l[0]) == 0 or l[0][0] == '#':
        return None
    return l


def split_ini_file( filetext ):
    lines = filetext.splitlines()
    l = []
    for line in lines:
        if len(line) > 0:
            fields = split_ini_line( line )
            if fields != None:
                l.append( fields )
    if len(l) == 0:
        return None
    return l


def process_ini_file( filename ):
    # Snarf in the contents
    try:
        ini_file = open( filename, 'r' )
    except IOError as e:
        logging.critical( "Error accessing file %s", filename )
        logging.error( "%s", str( e ) )
        return None
    input_text = ini_file.read()
    ini_file.close()

    ini_data = split_ini_file( input_text )
    if len( ini_data ) == 0:
        return None
    return ini_data


def find_dnsapi_modules( pn ):
    # Go through all possible names (pulled from what's mentioned in the
    # dnsapi.ini file) and for each one X see if we can load a module named
    # dnsapi_X (file will be dnsapi_X.py).
    dnsapis = {}
    possible_names = pn
    for api_name in possible_names:
        module_name = "dnsapi_" + api_name
        try:
            module = importlib.import_module( module_name )
        except ImportError as e:
            module = None
            logging.error( "Module %s for DNS API %s not found", module_name, api_name )
        if module != None:
            logging.debug( "DNS API module %s loaded", api_name )
            dnsapis[ api_name ] = module
    return dnsapis



# Set up command-line argument parser and parse arguments
parser = argparse.ArgumentParser( description = "Generate OpenDKIM key data for a set of domains" )
parser.add_argument( "-v", "--verbose", dest = 'log_info', action = 'store_true',
                     help = "Log informational messages in addition to errors" )
parser.add_argument( "-n", "--next-month", dest = 'next_month', action = 'store_true',
                     help = "Use next month's date for automatically-generated selectors" )
parser.add_argument( "-a", "--avoid-overwrite", dest = 'avoid_collisions', action = 'store_true',
                     help = "Add a suffix to the selector if needed to avoid overwriting existing files" )
parser.add_argument( "-s", "--selector", dest='output_selector', action = 'store_true',
                     help = "Causes the generated selector to be output" )
parser.add_argument( "--no-dns", dest = 'update_dns', action = 'store_false',
                     help = "Do not update DNS data" )
parser.add_argument( "--debug", dest = 'log_debug', action = 'store_true',
                     help = "Log debugging info and do not update DNS" )
parser.add_argument( "--use-null", dest = 'use_null_dnsapi', action = 'store_true',
                     help = "Silently use the null DNS API instead of the real API" )
parser.add_argument( "--version", dest='display_version', action = 'store_true',
                     help = "Display the program version" )
parser.add_argument( "selector", nargs = '?', default = None, help = "Selector to use" )
args = parser.parse_args()

if args.display_version:
    print "OpenDKIM genkeys.py v{0}".format( VERSION )
    sys.exit( 0 )

if args.log_info:
    level = logging.INFO
else:
    level = logging.WARN
if args.log_debug:
    level = logging.DEBUG

should_update_dns = args.update_dns
if never_update_dns:
    should_update_dns = False

should_output_selector = args.output_selector
if should_output_selector:
    should_update_dns = False
    level = logging.ERROR

avoid_collisions = args.avoid_collisions

logging.basicConfig( level = level, format = "%(levelname)s: %(message)s" )

# If we weren't given an explicit selector, the default is YYYYMM based on
# either this month or next month.
selector = args.selector
if selector == None:
    selector_date = datetime.date.today().replace( day = 1 )
    if args.next_month:
        y = selector_date.year
        m = selector_date.month
        m += 1
        if m > 12:
            m = 1
            y += 1
        selector_date = selector_date.replace( year = y, month = m )
    selector = selector_date.strftime( "%Y%m" )
logging.info( "Selector: %s", selector )
if should_output_selector:
    print selector
    sys.exit( 0 )

# Process dnsapi.ini
# If we're supposed to update DNS records but don't have any definitions for
# the DNS APIs, we record an error but we can continue to generate the keys
# and public key files anyway. The admin will just have to update the DNS
# records manually.
dnsapi_info = {} # Key = DNS API name, Value = remainder of fields
dnsapi_data = process_ini_file( dns_api_defs_filename )
if dnsapi_data == None and should_update_dns:
    logging.error( "No DNS API definitions found in %s", dns_api_defs_filename )
    should_update_dns = False
else:
    for item in dnsapi_data:
        dnsapi_info[ item[0] ] = item[1:len(item)]

# Process domains.ini
domain_data = process_ini_file( domain_filename )
if domain_data == None:
    logging.critical( "No domain definitions found in %s", domain_filename )
    sys.exit( 1 )
# We'll need a list of all the key names used by domains
key_names = []
for item in domain_data:
    if item[1] not in key_names:
        key_names.append( item[1] )

# Generate our keys, one per key name
keys = {} # Key = key name (field 1) from domain_data[n], Value = key data dict
for target in key_names:
    logging.info( "Generating key %s", target )
    key_data = gen_key( target, selector, avoid_collisions )
    if key_data == None:
        logging.critical( "    Error generating key %s", target )
        sys.exit( 1 )
    keys[target] = key_data
# That also gives us the private key and public key txt files needed

# Generate the key.table and signing.table files
try:
    key_table_file = open( "key.table", 'w' )
    signing_table_file = open( "signing.table", 'w' )
except IOError as e:
    logging.critical( "Error creating key or signing table file" )
    logging.error( "%s", str( e ) )
    sys.exit( 1 )
for item in domain_data:
    code = item[0].replace( '.', '-' )
    try:
        key_table_file.write( "%s\t%s:%s:%s/%s.%s.key\n" % \
                              ( code, item[0], selector, opendkim_dir, item[1], selector ) )
        signing_table_file.write( "*@%s\t%s\n" % ( item[0], code ) )
    except IOError as e:
        logging.critical( "Error creating key or signing table file" )
        logging.error( "%s", str( e ) )
        sys.exit( 1 )
key_table_file.close()
signing_table_file.close()

# Check for our DNS API modules. If we don't have any, there's no sense in
# trying to do automatic updating even if we're supposed to.
if should_update_dns:
    dnsapis = find_dnsapi_modules( dnsapi_info.keys() ) # Key = DNS API name, Value = module
    if len(dnsapis) == 0:
        logging.warning( "No DNS API modules found at %s", os.path.dirname( __file__ ) )
        should_update_dns = False

if should_update_dns:
    logging.info( "Updating DNS records" )
    for item in domain_data:
        if len(item) > 2:
            dnsapi_name = item[2]
            dnsapi_domain_data = item[3:len(item)]
            try:
                if args.use_null_dnsapi:
                    dnsapi_module = dnsapis[ 'null' ]
                else:
                    dnsapi_module = dnsapis[ dnsapi_name ]
                dnsapi_data = dnsapi_info[ dnsapi_name ]
                key_data = keys[ item[1] ].copy()
            except KeyError:
                dnsapi_module = None
                dnsapi_data = None
                key_data = None
            if dnsapi_module == None:
                logging.error( "No DNS API %s found for %s", dnsapi_name, item[0] )
            if dnsapi_module != None and dnsapi_data != None and key_data != None:
                logging.info( "Updating selector %s for %s with key %s", key_data[ 'selector' ], item[0], item[1] )
                key_data['domain'] = item[0]
                key_data['dnsapi'] = dnsapi_name
                sts = dnsapi_module.update( dnsapi_data, dnsapi_domain_data, key_data, args.log_debug )
                if not sts:
                    logging.error( "Error updating record for %s with key %s via %s API",
                                    item[0], item[1], dnsapi_name )

sys.exit( 0 )
