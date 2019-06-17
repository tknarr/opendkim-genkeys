# -*- coding: utf-8 -*-

#    OpenDKIM genkeys tool, netcup.de API
#    Copyright (C) 2018 Noel Kuntze <noel.kuntze+github@thermi.consulting>

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

# Uses the nc_dnsapi package


# Requires:
# dnsapi_data[0]        : Customer ID
# dnsapi_data[1]        : API key
# dnsapi_data[2]        : API password
# dnsapi_domain_data[0] : domain name
# key_data['plain']   : TXT record value

import datetime
import logging
from nc_dnsapi import Client, DNSRecord


def add(dnsapi_data, dnsapi_domain_data, key_data, debugging=False):
    if len(dnsapi_data) != 3:
        logging.error("Invalid or incomplete dnsapi configuration!")
        return False,

    customer_id = dnsapi_data[0]
    api_key = dnsapi_data[1]
    api_pw = dnsapi_data[2]
    domain = key_data['domain']
    selector = key_data['selector']
    # try logging in
    api = Client(customer_id, api_key, api_pw)
    print(key_data)
    if api:
        try:
            api.add_dns_record(domain, DNSRecord(selector + "._domainkey", "TXT", key_data['plain']))
        except Exception as e:
            logging.error("Failed to add the record: %s", e)
            return False,
        api.logout()
    else:
        logging.error("Failed to login!")
        return False,
    return True, domain, selector

def delete(dnsapi_data, dnsapi_domain_data, record_data, debugging=False):
    if len(dnsapi_data) != 3:
        logging.error("Invalid or incomplete dnsapi configuration!")
        return False

    customer_id = dnsapi_data[0]
    api_key = dnsapi_data[1]
    api_pw = dnsapi_data[2]
    domain = record_data[0]
    selector = record_data[1]
    # try logging in
    api = Client(customer_id, api_key, api_pw)
    if api:
        try:
            api.delete_dns_record(domain, DNSRecord(selector + "._domainkey", "TXT", None))
        except Exception as e:
            logging.error("Failed to delete the record: {}".format(e))
            return False
        api.logout()
    else:
        logging.error("Failed to login!")
        return False
    return True
