# -*- coding: utf-8 -*-

#    OpenDKIM genkeys tool, dummy API module for testing
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

# Requires:
# Nothing

# To use this module, add a 'fail' entry to dnsapi.ini. You can list the methods that
# should fail ('add', 'delete') as keywords after the 'fail'. By default all methods
# will fail.

import datetime
import logging


def add( dnsapi_data, dnsapi_domain_data, key_data, debugging = False ):
    if debugging:
        try:
            logging.debug( "    DNS API %s", key_data['dnsapi'] )
            logging.debug( "    selector: %s", key_data['selector'] )
            logging.debug( "    domain  : %s", key_data['domain'] )
        except KeyError as e:
            logging.debug( "    required %s not found", str( e ) )
        logging.debug( "    global data: %s", str( dnsapi_data ) )
        logging.debug( "    domain data: %s", str( dnsapi_domain_data ) )
        logging.debug( "    key data   :" )
        for key, value in key_data.iteritems():
            logging.debug( '        %s: %s', key, value )
    if len( dnsapi_data ) == 0 or 'add' in dnsapi_data:
        return False,
    else:
        return True, key_data['domain'], key_data['selector'], datetime.datetime.utcnow(), '-'


def delete( dnsapi_data, dnsapi_domain_data, record_data, debugging = False ):
    if len( dnsapi_data ) == 0 or 'delete' in dnsapi_data:
        return False
    else:
        return True
