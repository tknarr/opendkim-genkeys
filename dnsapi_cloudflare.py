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

# Requires:
# dnsapi_data[0]        : Global API key
# dnsapi_data[1]        : Email address
# dnsapi_domain_data[0] : Zone ID
# dnsapi_domain_data[1] : TTL in seconds, automatic if not specified
# key_data['plain']     : TXT record value in plain unquoted format

# Parameters:
# type    : 'TXT'
# name    : selector + '._domainkey.' + domain_suffix
# content : key_data['plain']
# ttl     : dnsapi_domain_data[1]

import datetime
import logging

import CloudFlare


def update(dnsapi_data, dnsapi_domain_data, key_data, debugging=False):
    if len(dnsapi_data) < 2:
        logging.error("DNS API Cloudflare: API credentials not configured")
        return False,
    api_key = dnsapi_data[0]
    email = dnsapi_data[1]
    if len(dnsapi_domain_data) < 1:
        logging.error("DNS API Cloudflare: domain data does not contain zone ID")
        return False,
    zone_id = dnsapi_domain_data[0]
    if len(dnsapi_domain_data) > 1:
        try:
            ttl = int(dnsapi_domain_data[1])
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
        logging.error("DNS API Cloudflare: required information not present: %s", str(e))
        return False,
    if debugging:
        return True, key_data['domain'], selector

    cf = CloudFlare.CloudFlare(email=email, token=api_key, debug=debugging)

    request_params = {
        'type': 'TXT',
        'name': selector + '._domainkey.' + domain_suffix,
        'content': data,
        'ttl': ttl
    }

    try:
        response = cf.zones.dns_records.post(zone_id, data=request_params)
        if response:
            # TODO need resource ID appended to result
            result = True, key_data['domain'], selector, datetime.datetime.utcnow()
        else:
            result = False,
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        result = False
        if len(e) > 0:
            for ex in e:
                logging.error('DNS API Cloudflare: [%d] %s', ex, ex)
        else:
            logging.error('DNS API Cloudflare: [%d] %s', e, e)

    return result


def delete(dnsapi_data, dnsapi_domain_data, record_data, debugging = False):
    # TODO delete record
    return None
