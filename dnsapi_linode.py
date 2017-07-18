# -*- coding: utf-8 -*-

#    OpenDKIM genkeys tool, Linode DNS Manager API
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
# dnsapi_data[0]        : API key
# dnsapi_domain_data[0] : Domain ID
# key_data['plain']     : TXT record value in plain unquoted format

# POST URL: https://api.linode.com/

# Parameters:
# api_key            : dnsapi_data[0]
# api_action         : "domain.resource.create"
# DomainID           : dnsapi_domain_data[0]
# Type               : "TXT"
# Name               : selector + "._domainkey"
# Target             : key_data['plain']

import datetime
import logging

import requests


def add(dnsapi_data, dnsapi_domain_data, key_data, debugging = False):
    if len(dnsapi_data) < 1:
        logging.error("DNS API linode: API key not configured")
        return False,
    api_key = dnsapi_data[0]
    if len(dnsapi_domain_data) < 1:
        logging.error("DNS API linode: domain data does not contain domain ID")
        return False,
    domain_id = dnsapi_domain_data[0]
    try:
        selector = key_data['selector']
        data = key_data['plain']
    except KeyError as e:
        logging.error("DNS API linode: required information not present: %s", str(e))
        return False,
    if debugging:
        return True,

    resp = requests.post("https://api.linode.com/",
                         data = {'api_key':    api_key,
                                 'api_action': 'domain.resource.create',
                                 'DomainID':   domain_id,
                                 'Type':       'TXT',
                                 'Name':       selector + "._domainkey",
                                 'Target':     data
                                 })
    logging.info("HTTP status: %d", resp.status_code)

    if resp.status_code == requests.codes.ok:
        error_array = resp.json()['ERRORARRAY']
        if len(error_array) > 0:
            result = False,
            for error in error_array:
                logging.error("DNS API linode: error %d: %s", error['ERRORCODE'], error['ERRORMESSAGE'])
        else:
            data = resp.json()['DATA']
            if data:
                result = True, key_data['domain'], selector, datetime.datetime.utcnow(), data['ResourceID']
            else:
                logging.error("DNS API linode: could not locate data in response")
                result = False,
    else:
        result = False,
        logging.error("DNS API linode: HTTP error %d", resp.status_code)
        logging.error("DNS API linode: error response body:\n%s", resp.text)

    return result


def delete(dnsapi_data, dnsapi_domain_data, record_data, debugging = False):
    if len(dnsapi_data) < 1:
        logging.error("DNS API linode: API key not configured")
        return False
    api_key = dnsapi_data[0]
    if len(dnsapi_domain_data) < 1:
        logging.error("DNS API linode: domain data does not contain domain ID")
        return False
    domain_id = dnsapi_domain_data[0]
    try:
        resource_id = record_data[3]
    except KeyError as e:
        logging.error("DNS API linode: required information not present: %s", str(e))
        return False
    if debugging:
        return True

    resp = requests.post("https://api.linode.com/",
                         data = {'api_key':    api_key,
                                 'api_action': 'domain.resource.delete',
                                 'DomainID':   domain_id,
                                 'ResourceID': resource_id,
                         })
    logging.info("HTTP status: %d", resp.status_code)

    if resp.status_code == requests.codes.ok:
        error_array = resp.json()['ERRORARRAY']
        if len(error_array) > 0:
            result = False
            for error in error_array:
                logging.error("DNS API linode: error %d: %s", error['ERRORCODE'], error['ERRORMESSAGE'])
        else:
            data = resp.json()['DATA']
            if data:
                result = True
            else:
                logging.error("DNS API linode: could not locate data in response")
                result = False
    else:
        result = False
        logging.error("DNS API linode: HTTP error %d", resp.status_code)
        logging.error("DNS API linode: error response body:\n%s", resp.text)

    return result
