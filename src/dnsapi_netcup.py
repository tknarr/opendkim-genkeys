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

import logging
from nc_dnsapi import Client, DNSRecord

def _get_parameters(dnsapi_data, data):
    return dnsapi_data[0], dnsapi_data[1], dnsapi_data[2], data["domain"], data["selector"]

def _try_login(customer_id, api_key, api_pw):
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.WARNING)
    i = 0
    api = None
    while i < 5:
        try:
            api = Client(customer_id, api_key, api_pw)
        except Exception as exc:
            logger.error.warn("Failed to login, retrying: %s", exc)
        if api is not None:
            return api
        i += 1
        if i == 5:
            logger.error("Failed to login. Aborting!")
            return None

def _init_module_specific_data(module_specific_data):
    if isinstance(module_specific_data, dict):
        return module_specific_data
    return {}

def _get_api(customer_id, api_key, api_pw, module_specific_data):
    api = module_specific_data.get("api_session")
    if not api:
        api = _try_login(customer_id, api_key, api_pw)
    return api

def add(dnsapi_data, dnsapi_domain_data, key_data, module_specific_data, debugging=False):
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.WARNING)
    logging.basicConfig()
    if len(dnsapi_data) != 3:
        logger.error("Invalid or incomplete dnsapi configuration!")
        return (False,)

    # try logging in
    customer_id, api_key, api_pw, domain, selector = _get_parameters(dnsapi_data, key_data)
    module_specific_data = _init_module_specific_data(module_specific_data)
    api = _get_api(customer_id, api_key, api_pw, module_specific_data)
    if not api:
        return (False,)

    ret = None
    try:
        ret = api.add_dns_record(domain, DNSRecord(
            selector + "._domainkey", "TXT", "v=DKIM1; h=sha256; k=rsa; s=email; p=%s" % key_data['plain']))
    except Exception as e:
        print("Failed) to add the record: %s", e)
        try:
            module_specific_data.pop("api_session")
        except:
            pass
        return (False,)

    if not ret:
        print("Failed to add the record: %s", ret)
        return (False,)
    return (True, domain, selector)

def check(dnsapi_data, dnsapi_domain_data, key_data, module_specific_data, debugging=False):
    """Check if the given record exists"""
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.WARNING)
    if len(dnsapi_data) != 3:
        logger.error("Invalid or incomplete dnsapi configuration!")
        return None
     # try logging in
    customer_id, api_key, api_pw, domain, selector = _get_parameters(dnsapi_data, key_data)
    module_specific_data = _init_module_specific_data(module_specific_data)

    api = _get_api(customer_id, api_key, api_pw, module_specific_data)
    if not api:
        return False

    try:
        return api.dns_record_exists(
            domain,
            DNSRecord(selector + "._domainkey", "TXT", "v=DKIM1; h=sha256; k=rsa; s=email; p=%s" % key_data['plain']))
    except:
        return False

def delete_all(dnsapi_data, dnsapi_domain_data, record_data, module_specific_data, debugging=False):
    """Check if the given record exists"""
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.WARNING)
    if len(dnsapi_data) != 3:
        logger.error("Invalid or incomplete dnsapi configuration!")
        return None
     # try logging in
    customer_id, api_key, api_pw, domain, _ = _get_parameters(dnsapi_data, record_data)
    module_specific_data = _init_module_specific_data(module_specific_data)

    api = _get_api(customer_id, api_key, api_pw, module_specific_data)
    if not api:
        return False

    try:
        record_list = []
        for record in api.dns_records(domain):
            record.deleterecord=True
            record_list.append(record)
        api.delete_records(record_list)
    except:
        return False

def delete(dnsapi_data, dnsapi_domain_data, record_data, module_specific_data, debugging=False):
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.WARNING)
    if len(dnsapi_data) != 3:
        logger.error("Invalid or incomplete dnsapi configuration!")
        return (False,)

    # try logging in
    customer_id, api_key, api_pw, domain, selector = _get_parameters(dnsapi_data, record_data)
    module_specific_data = _init_module_specific_data(module_specific_data)

    api = _get_api(customer_id, api_key, api_pw, module_specific_data)
    if not api:
        return (False,)

    # need to get matching records first, so we know the ID, which is required to delete the record
    ret = None
    record = None
    try:
        ret = api.dns_records(domain)
    except Exception as e:
        logger.error("Failed to delete the record: Failed to retrieve the DNS records: %s", e)
        return (False, )
    for record in ret:
        if record.hostname == selector + "._domainkey" and record.type == "TXT":
            record.deleterecord=True
            break
    if not record:
        logger.error("Failed to delete the record: Failed to find the record.")
        return (False, )
    try:
        ret = api.delete_dns_record(domain, record)
    except Exception as e:
        logger.error("Failed to delete the record: %s", e)
        try:
            module_specific_data.pop("api_session")
        except:
            pass
        return (False,)

    if not ret:
        logger.error("Failed to delete the record: %s", ret)
        return (False,)
    return True

def delete_duplicates(dnsapi_data, dnsapi_domain_data, record_data, module_specific_data, debugging=False):
    """
    Remove all duplicates
    """
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.WARNING)
    if len(dnsapi_data) != 3:
        logger.error("Invalid or incomplete dnsapi configuration!")
        return (False,)

    # try logging in
    customer_id, api_key, api_pw, domain, selector = _get_parameters(dnsapi_data, record_data)
    module_specific_data = _init_module_specific_data(module_specific_data)

    api = _get_api(customer_id, api_key, api_pw, module_specific_data)
    if not api:
        return (False,)

    ret = None
    # get all records for the zone
    records1 = []
    records2 = api.dns_records(domain)
    for record in records2:
        if record in records1:
            records2.deleterecord = True
        else:
            records1.append(record)

    return api.update_dns_records(domain, records2)

def init(module_specific_data, debugging=False):
    if isinstance(module_specific_data, dict):
        return module_specific_data
    else:
        return {}

def finish(module_specific_data, debugging=False):
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.WARNING)
    try:
        if isinstance(module_specific_data, dict) and module_specific_data.get("api_session"):
            session = module_specific_data.pop("api_session")
            session.logout()
    except Exception as e:
        logger.error("An exception occured while trying to logout: %s", e)
        return False
    return True
