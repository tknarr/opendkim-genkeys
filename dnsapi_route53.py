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

# Uses the 'requests' and 'requests-aws4auth' packages.

# Requires:
# dnsapi_data[0]        : AWS key ID
# dnsapi_data[1]        : AWS secret key
# dnsapi_domain_data[0] : AWS region (always us-east-1)
# dnsapi_domain_data[1] : Hosted domain ID
# dnsapi_domain_data[2] : Time-to-live, default 3600 seconds (1 hour)
# key_data['plain']     : TXT record value in plain unquoted format

# POST URL: https://route53.amazonaws.com/2013-04-01/hostedzone/rrset

# Parameters:
# api_key            : dnsapi_data[0]
# api_action         : "domain.resource.create"
# DomainID           : dnsapi_domain_data[0]
# Type               : "TXT"
# Name               : selector + "._domainkey"
# Target             : key_data['plain']

import datetime
import logging
import xml.dom.minidom

import requests
from requests_aws4auth import AWS4Auth


def add( dnsapi_data, dnsapi_domain_data, key_data, debugging = False ):
    if len( dnsapi_data ) < 2:
        logging.error( "DNS API route53: AWS key not configured" )
        return False,
    aws_key_id = dnsapi_data[0]
    aws_key = dnsapi_data[1]
    if len( dnsapi_domain_data ) < 2:
        logging.error( "DNS API route53: domain data does not contain required data" )
        return False,
    region = dnsapi_domain_data[0]
    zone_id = dnsapi_domain_data[1]
    if len( dnsapi_domain_data ) > 2:
        try:
            ttl = int( dnsapi_domain_data[2] )
            if ttl < 5:
                ttl = 5
        except Exception:
            ttl = 3600
    else:
        ttl = 3600
    try:
        selector = key_data['selector']
        data = key_data['chunked']
        domain_suffix = key_data['domain']
    except KeyError as e:
        logging.error( "DNS API route53: required information not present: %s", str( e ) )
        return False,
    if debugging:
        return True,

    aws4_auth = AWS4Auth( aws_key_id, aws_key, region, 'route53' )

    # Construct Route53 XML for the ChangeResourceRecordSets request
    route53_xml = create_xml( 'CREATE', selector, domain_suffix, ttl, data )

    endpoint = "https://route53.amazonaws.com/2013-04-01/hostedzone/{0}/rrset".format(zone_id)
    headers = {'Content-Type': 'text/xml; charset=utf-8'}
    resp = requests.post(endpoint, data = route53_xml, auth = aws4_auth, headers = headers)
    logging.info("HTTP status: %d", resp.status_code)

    if resp.status_code == requests.codes.ok:
        doc = xml.dom.minidom.parseString(resp.text)
        id = doc.getElementsByTagName('Id')
        if id:
            result = True, key_data['domain'], selector, datetime.datetime.utcnow(), \
                     get_text( id.item( 0 ).childNodes ), data
        else:
            logging.error("DNS API route53: cannot find ID in response")
            result = False,
    else:
        result = False,
        error_text = get_error(resp)
        logging.error("DNS API route53: HTTP error %d : %s", resp.status_code, error_text)
        if error_text == '':
            logging.error("DNS API route53: error response body:\n%s", resp.text)

    return result


def delete(dnsapi_data, dnsapi_domain_data, record_data, debugging = False):
    if len(dnsapi_data) < 2:
        logging.error("DNS API route53: AWS key not configured")
        return False
    aws_key_id = dnsapi_data[0]
    aws_key = dnsapi_data[1]
    if len(dnsapi_domain_data) < 2:
        logging.error("DNS API route53: domain data does not contain required data")
        return False
    region = dnsapi_domain_data[0]
    zone_id = dnsapi_domain_data[1]
    if len(dnsapi_domain_data) > 2:
        try:
            ttl = int(dnsapi_domain_data[2])
            if ttl < 5:
                ttl = 5
        except Exception:
            ttl = 3600
    else:
        ttl = 3600
    if len(record_data) < 5:
        logging.error("DNS API route54: saved record does not contain required data")
        return False
    try:
        domain_suffix = record_data[0]
        selector = record_data[1]
        data = ' '.join( record_data[4:] )
    except KeyError as e:
        logging.error("DNS API route53: required information not present: %s", str(e))
        return False
    if debugging:
        return True

    aws4_auth = AWS4Auth(aws_key_id, aws_key, region, 'route53')

    # Construct Route53 XML for the ChangeResourceRecordSets request
    route53_xml = create_xml( 'DELETE', selector, domain_suffix, ttl, data )

    endpoint = "https://route53.amazonaws.com/2013-04-01/hostedzone/{0}/rrset".format(zone_id)
    headers = {'Content-Type': 'text/xml; charset=utf-8'}
    resp = requests.post(endpoint, data = route53_xml, auth = aws4_auth, headers = headers)
    logging.info("HTTP status: %d", resp.status_code)

    if resp.status_code == requests.codes.ok:
        doc = xml.dom.minidom.parseString(resp.text)
        id = doc.getElementsByTagName('Id')
        if id:
            result = True
        else:
            logging.error("DNS API route53: cannot find ID in response")
            result = False
    else:
        result = False
        error_text = get_error(resp)
        logging.error("DNS API route53: HTTP error %d : %s", resp.status_code, error_text)
        if error_text == '':
            logging.error("DNS API route53: error response body:\n%s", resp.text)

    return result


def create_xml( action_str, selector, domain_suffix, ttl, data ):
    # Construct Route53 XML for the ChangeResourceRecordSets request
    impl = xml.dom.minidom.getDOMImplementation()
    doc = impl.createDocument( 'https://route53.amazonaws.com/doc/2013-04-01/',
                               'ChangeResourceRecordSetsRequest', None )
    root = doc.documentElement
    root.setAttribute('xmlns', 'https://route53.amazonaws.com/doc/2013-04-01/')
    chg_batch = doc.createElement('ChangeBatch')
    root.appendChild(chg_batch)
    changes = doc.createElement('Changes')
    chg_batch.appendChild(changes)
    change = doc.createElement('Change')
    changes.appendChild(change)
    action = doc.createElement('Action')
    action_text = doc.createTextNode(action_str)
    action.appendChild(action_text)
    change.appendChild(action)
    rrset = doc.createElement('ResourceRecordSet')
    change.appendChild(rrset)
    name = doc.createElement('Name')
    name_text = doc.createTextNode(selector + '._domainkey.' + domain_suffix)
    name.appendChild(name_text)
    rrset.appendChild(name)
    rrtype = doc.createElement('Type')
    rrtype_text = doc.createTextNode('TXT')
    rrtype.appendChild(rrtype_text)
    rrset.appendChild(rrtype)
    rrttl = doc.createElement('TTL')
    rrttl_text = doc.createTextNode(str(ttl))
    rrttl.appendChild(rrttl_text)
    rrset.appendChild(rrttl)
    rrs = doc.createElement('ResourceRecords')
    rrset.appendChild(rrs)
    rr = doc.createElement('ResourceRecord')
    rrs.appendChild(rr)
    value = doc.createElement('Value')
    value_text = doc.createTextNode(data)
    value.appendChild(value_text)
    rr.appendChild(value)
    route53_xml = doc.toxml('utf-8')
    doc.unlink()  # Let things we don't need anymore be GC'd
    return route53_xml


def get_error( resp):
    try:
        doc = xml.dom.minidom.parseString(resp.text)
        doc.normalize()
        error_type = doc.getElementsByTagName('Type')
        if error_type and error_type.length > 0:
            error_type_text = get_text(error_type.item(0).childNodes)
        else:
            error_type_text = ''
        code = doc.getElementsByTagName('Code')
        if code and code.length > 0:
            code_text = get_text(code.item(0).childNodes)
        else:
            code_text = ''
        message = doc.getElementsByTagName('Message')
        if message and message.length > 0:
            message_text = get_text(message.item(0).childNodes)
        else:
            message_text = ''
        error_text = error_type_text + ' : ' + code_text + ' : ' + message_text
        doc.unlink()
    except Exception as e:
        logging.error("XML exception: %s", str(e))
        error_text = ''
    return error_text


def get_text(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append( node.data )
    return ''.join( rc )
