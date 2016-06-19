# -*- coding: utf-8 -*-

#    OpenDKIM genkeys tool, CloudFlare API
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
# dnsapi_data[0]        : Global API key
# dnsapi_data[1]        : Email address
# dnsapi_domain_data[0] : Zone ID
# dnsapi_domain_data[1] : TTL in seconds, automatic if not specified
# key_data['plain']     : TXT record value in plain unquoted format

# POST URL: https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records

# Parameters:
# type    : 'TXT'
# name    : selector + '._domainkey.' + domain_suffix
# content : key_data['plain']
# ttl     : dnsapi_domain_data[1]

import logging
import requests

def update( dnsapi_data, dnsapi_domain_data, key_data, debugging = False ):
    if len(dnsapi_data) < 2:
        logging.error( "DNS API cloudflare: API credentials not configured" )
        return False;
    api_key = dnsapi_data[0]
    email = dnsapi_data[1]
    if len(dnsapi_domain_data) < 1:
        logging.error( "DNS API cloudflare: domain data does not contain zone ID" )
        return False
    zone_id = dnsapi_domain_data[0]
    if len(dnsapi_domain_data) > 1:
        try:
            ttl = int( dnsapi_domain_data[1] )
            if ttl < 1:
                ttl = 1
        except Exception:
            ttl = 1
    else:
        ttl = 1
    try:
        selector = key_data['selector']
        data = key_data['plain']
        domain_suffix = key_data['domain']
    except KeyError as e:
        logging.error( "DNS API cloudflare: required information not present: %s", str(e) )
        return False
    if debugging:
        return True

    result = False
    endpoint = "https://api.cloudflare.com/client/v4/zones/{0}/dns_records".format( zone_id )
    headers = { 'Content-Type': 'application/json',
                'X-Auth-Key': api_key,
                'X-Auth-Email': email }
    data = { 'type': 'TXT',
             'name': selector + '._domainkey.' + domain_suffix,
             'content': data,
             'ttl', ttl }
    resp = requests.post( endpoint, data = data, headers = headers )
    logging.info( "HTTP status: %d", resp.status_code )

    if resp.status_code == requests.codes.ok:
        success = resp.json()['success']
        if success:
            result = True
        else:
            result = False
            logging.error( "DNS API cloudflare: failure:\n%s", resp.text )
    else:
        result = False
        logging.error( "DNS API cloudflare: HTTP error %d", resp.status_code )
        logging.debug( "DNS API cloudflare: error response body:\n%s", resp.text )

    return result
