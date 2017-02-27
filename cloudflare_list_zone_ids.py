#!/usr/bin/python
# -*- coding: utf-8 -*-

#    OpenDKIM genkeys - list zones and zone IDs for CloudFlare account
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
import argparse
import logging

import CloudFlare

# Set up command-line argument parser and parse arguments
parser = argparse.ArgumentParser(description="List CloudFlare zones and zone IDs")
parser.add_argument("api_key", help="Global API key")
parser.add_argument("email", help="Account email address")
parser.add_argument("domain", nargs='?', default=None, help="Domain to request ID for")
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

api_key = args.api_key
email = args.email
if api_key == None:
    logging.error("API key and email address are required.")
    sys.exit(1)
elif email == None:
    logging.error("Email address is required.")
    sys.exit(1)
domain = args.domain

cf = CloudFlare.CloudFlare(email=email, token=api_key, raw=True)

zones = []
current_page = 0
total_pages = 1

while current_page < total_pages:

    current_page += 1
    logging.info("Retrieving page %d of %d", current_page, total_pages)

    request_params = {'per_page': 50, 'page': current_page, 'order': 'name', 'direction': 'asc'}
    if domain:
        request_params['name'] = domain

    try:
        response = cf.zones.get(params=request_params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        if len(e) > 0:
            for ex in e:
                logging.error('Cloudflare API: [%d] %s', ex, ex)
        else:
            logging.error('Cloudflare API: [%d] %s', e, e)
        sys.exit(1)

    result_info = response['result_info']

    for zone in response['result']:
        zones.append((zone['id'], zone['name']))

    current_page = result_info['page']
    total_pages = result_info['total_pages']

for id, name in zones:
    print("{0}\t{1}".format(id, name))

sys.exit(0)
