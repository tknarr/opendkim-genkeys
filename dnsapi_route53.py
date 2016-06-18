# -*- coding: utf-8 -*-

#    OpenDKIM genkeys tool, AWS Route 53 API
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

# Uses the 'requests' package.

# Requires:
# dnsapi_data[0]        : API key ID
# dnsapi_data[1]        : API secret key
# dnsapi_domain_data[0] : Hosted domain name
# key_data['plain']     : TXT record value in plain unquoted format

# POST URL: https://route53.amazonaws.com/2013-04-01/{hostedzone}

# Parameters: TODO
# api_key            : dnsapi_data[0]
# api_action         : "domain.resource.create"
# DomainID           : dnsapi_domain_data[0]
# Type               : "TXT"
# Name               : selector + "._domainkey"
# Target             : key_data['plain']

import logging
import requests

def update( dnsapi_data, dnsapi_domain_data, key_data, debugging = False ):
    if len(dnsapi_data) < 2:
        logging.error( "DNS API route53: API key not configured" )
        return False;
    api_key_id = dnsapi_data[0]
    api_key = dnsapi_data[1]
    if len(dnsapi_domain_data) < 1:
        logging.error( "DNS API route53: domain data does not contain hosted zone name" )
        return False
    zone_name = dnsapi_domain_data[0]
    try:
        selector = key_data['selector']
        data = key_data['plain']
    except KeyError as e:
        logging.error( "DNS API route53: required information not present: %s", str(e) )
        return False
    if debugging:
        return True

    result = False
    resp = requests.post( "https://api.linode.com/",
                          data = { 'api_key': api_key,
                                   'api_action': 'domain.resource.create',
                                   'DomainID': domain_id,
                                   'Type': 'TXT',
                                   'Name': selector + "._domainkey",
                                   'Target': data
                                   } )
    logging.info( "HTTP status: %d", resp.status_code )

    if resp.status_code == requests.codes.ok:
        error_array = resp.json()['ERRORARRAY']
        if len(error_array) > 0:
            result = False
            for error in error_array:
                logging.error( "DNS API linode: error %d: %s", error['ERRORCODE'], error['ERRORMESSAGE'] )
        else:
            result = True
    else:
        result = False
        logging.error( "DNS API linode: HTTP error %d", resp.status_code )
        logging.debug( "DNS API linode: error response body:\n%s", resp.text )

    return result
