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

import logging

def update( dnsapi_data, dnsapi_domain_data, key_data, debugging = False ):
    try:
        selector = key_data['selector']
        domain = key_data['domain']
        data = key_data['plain']
    except KeyError as e:
        logging.error( "DNS API linode: required information not present: %s", str(e) )
        return False
    if debugging:
        return True
    logging.error( "dnsapi_linode.update() not implemented" )
    return False
