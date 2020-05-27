#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Men&Mice
# GNU General Public License v3.0
# see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt
#
# https://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html
#
# python 3 headers, required if submitting to Ansible
"""Ansible inventory plugin.

Inventory plugin for finding all hosts in an Men&Mice Suite
As this could a lot, use the 'filter' option to tune it down.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys
import re
import os
import json
import time
from ansible import constants as C
from ansible.errors import AnsibleError
from ansible.module_utils import six
from ansible.module_utils.urls import Request, urllib_error, ConnectionError, socket, httplib
from ansible.module_utils._text import to_native
from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.module_utils.urls import open_url, SSLValidationError
from ansible.plugins.loader import inventory_loader

# Python 2/3 Compatibility
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

# Debugging stuff
from ansible.utils.display import Display
display = Display()

DOCUMENTATION = '''
    name: mm_inventory
    plugin_type: inventory
    author: Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
    short_description: Ansible dynamic inventory plugin for the Men&Mice Suite.
    version_added: "2.7"
    extends_documentation_fragment:
      - inventory_cache
    description:
      - Reads inventories from Men&Mice Suite.
      - Supports reading configuration from both YAML config file and environment variables.
      - If reading from the YAML file, the file name must end with mm_inv.(yml|yaml) or mm_inventory.(yml|yaml),
        the path in the command would be /path/to/mm_inventory.(yml|yaml). If some arguments in the config file
        are missing, this plugin will try to fill in missing arguments by reading from environment variables.
      - If reading configurations from environment variables, the path in the command must be @mm_inventory.
    options:
      plugin:
        description: the name of this plugin, it should always be set to 'mm_inventory'
                     for this plugin to recognize it as it's own.
        env:
          - name: ANSIBLE_INVENTORY_ENABLED
        required: True
        choices: ['mm_inventory']
      host:
        description: The network address of the Men&Mice Suite host
        type: string
        env:
          - name: MM_HOST
        required: True
      user:
        description: The user that you plan to use to access inventories on your Men&Mice Suite
        type: string
        env:
          - name: MM_USER
        required: True
      password:
        description: The password for your your Men&Mice Suite user.
        type: string
        env:
          - name: MM_PASSWORD
        required: True
      ranges:
        description: Ranges to get the inventory from (e.g. 172.16.17.0/24)
        type: list
        env:
          - name: MM_RANGES
        required: False
      filters:
        description:
          - A list of filter value pairs.
          - This a combination of a custom property and the value
          - To avoid parsing errors, the custom-key and custom-value
            are both sanitized, so both are converted to lowercase and
            all special characters are translated to "_"
        type: list
        env:
          - name: MM_FILTERS
        required: False
'''

EXAMPLES = '''
# Before you execute the following commands, you should make sure this file is
# in your plugin path, and you enabled this plugin.

# Examples using mm_inventory.yml file

plugin: mm_inventory
host: "http://mmsuite.example.net"
user: apiuser
password: apipasswd
filters:
  - location: London


plugin: mm_inventory
host: "http://mmsuite.example.net"
user: apiuser
password: apipasswd
ranges:
  - 172.16.17.0/24


The "filters" are an "and" function, a host is only available in the inventory
when all filter-conditions are met.

The "ranges" are an "or" function, a host is available in the inventory
when either ranges-conditions are met.


# With in the ansible.cfg
[inventory]
enable_plugins = mm_inventory, host_list, auto
cache = yes
cache_plugin = pickle
cache_prefix = mm_inv
cache_timeout = 3600
cache_connection = /tmp/inv_cache

# Then you can run the following command.
# If some of the arguments are missing, Ansible will attempt to read them from
# environment variables.

# ansible-inventory -i /path/to/mm_inventory.yml --list
# or "inventory = mm_inventory.yml" in the ansible.cfg file

# Example for reading from environment variables:

# Set environment variables:
#
# export MM_HOST=YOUR_MM_HOST_ADDRESS
# export MM_USER=YOUR_MM_USER
# export MM_PASSWORD=YOUR_MM_PASSWORD
# export MM_FILTERS=YOUR_MM_FILTERS
# export MM_RANGES=YOUR_MM_RANGES

# Read the inventory from the Men&Mice Suite, and list them.
# The inventory path must always be @mm_inventory if you are reading
# all settings from environment variables.
# ansible-inventory -i @mm_inventory --list
'''


def doapi(url, method, provider, databody):
    """Run an API call.

    Parameters:
        - url          -> Relative URL for the API entry point
        - method       -> The API method (GET, POST, DELETE,...)
        - provider     -> Needed credentials for the API provider
        - databody     -> Data needed for the API to perform the task

    Returns:
        - The response from the API call
        - The Ansible result dict

    When connection errors arise, there will be a multiple of tries,
    each a couple of seconds apart, this to handle high-availability
    """
    headers = {'Content-Type': 'application/json'}
    apiurl = "%s/mmws/api/%s" % (provider['mmurl'], url)
    result = {}

    # Maximum and current number of tries to connect to the Men&Mice API
    MAXTRIES = 5
    tries = 0

    while tries <= 4:
        tries += 1
        try:
            resp = open_url(apiurl,
                            method=method,
                            url_username=provider['user'],
                            url_password=provider['password'],
                            data=json.dumps(databody),
                            validate_certs=False,
                            headers=headers)

            # Response codes of the API are:
            #  - 200 => All OK, data returned in the body
            #  - 204 => All OK, no data returned in the body
            #  - *   => Something is wrong, error data in the body
            # But sometimes there is a situation where the response code
            # was 201 and with data in the body, so that is picked up as well

            # Get all API data and format return message
            response = resp.read()
            if resp.code == 200:
                # 200 => Data in the body
                result['message'] = json.loads(response)
            elif resp.code == 201:
                # 201 => Sometimes data in the body??
                try:
                    result['message'] = json.loads(response)
                except ValueError:
                    result['message'] = ""
            else:
                # No response from API (204 => No data)
                try:
                    result['message'] = resp.reason
                except AttributeError:
                    result['message'] = ""
            result['changed'] = True
        except HTTPError as err:
            errbody = json.loads(err.read().decode())
            result['changed'] = False
            result['warnings'] = "%s: %s (%s)" % (err.msg,
                                                  errbody['error']['message'],
                                                  errbody['error']['code']
                                                  )
        except URLError as err:
            raise AnsibleError("Failed lookup url for %s : %s" % (apiurl, to_native(err)))
        except SSLValidationError as err:
            raise AnsibleError("Error validating the server's certificate for %s: %s" % (apiurl, to_native(err)))
        except ConnectionError as err:
            if tries == MAXTRIES:
                raise AnsibleError("Error connecting to %s: %s" % (apiurl, to_native(err)))
            else:
                # There was a connection error, wait a little and retry
                time.sleep(0.25)

        if result.get('message', "") == "No Content":
            result['message'] = ""
        return result


def _sanitize(data):
    """Clean and sanitize a string."""
    data = data.lower()
    data = re.sub(r'[ -\/\\&*^%$#@!+=`~:;<>?,\."\'()\[\]\{\}]', '_', data)

    return data


class InventoryModule(BaseInventoryPlugin, Cacheable):
    # used internally by Ansible, it should match the file name
    # Is not required
    NAME = 'mm_inventory'

    # If the user supplies '@mm_inventory' as the inventory path, the plugin
    # will read all settings from environment variables.
    no_config_file_supplied = False

    def verify_file(self, path):
        """Verify if the configuration file is valid."""
        valid_names = ['mm_inventory', 'mmsuite', 'mandm', 'menandmice',
                       'mandmsuite', 'mm_suite', 'mandm_suite']

        valid = False
        if path.endswith('@mm_inventory'):
            self.no_config_file_supplied = True
            valid = True
        elif super(InventoryModule, self).verify_file(path):
            fname, ext = os.path.splitext(os.path.basename(path))
            if fname in valid_names and ext in C.YAML_FILENAME_EXTENSIONS:
                valid = True

        return valid

    def get_inventory(self):
        """Create a inventory dictionairy with all host and group information.

           Return a dictionary that contains:
                invent = {
                    'hosts': [{'name': hostname, 'address': ipaddress}, ...],
                    'groups': {
                        "all": [hostname1, hostname2, ...],
                        "mm_hosts": [hostname1, hostname2, ...],
                        "custgrp1":  [hostname1, hostname5, ...],
                        "custgrp3":  [hostname4, hostname7, ...],
                        .
                        .
                        .
                    }
                }

             This is the dictionairy that will cached, if requested (2.8+)
        """
        # Read inventory from Men&Mice Suite server

        # Get the needed connection information
        mmurl = self.get_option('host')
        user = self.get_option('user')
        password = self.get_option('password')

        # If provider information is not present, quit
        if not (mmurl and user and password):
            raise AnsibleParserError(
                "Missing connection provider (mmurl, ",
                "username, password) in configuration file")

        # Construct connection provider
        provider = {
            'mmurl': mmurl,
            'user': user,
            'password': password
        }

        # Check if filters are supplied
        try:
            filters = self.get_option('filters')
        except KeyError as err:
            filters = []

        # Check if ranges are supplied
        try:
            ranges = self.get_option('ranges')
        except KeyError as err:
            ranges = []

        # Start with an (almost) empty inventory
        invent = {
            'hosts': [],
            'groups': {
                "all": [],
                "mm_hosts": []
            }
        }

        # Get all IP ranges
        http_method = 'GET'
        url = 'Ranges'
        databody = {}
        result = doapi(url, http_method, provider, databody)

        # Find all child ranges, to prevent checking everything
        children = []
        for res in result['message']['result']['ranges']:
            if res['childRanges']:
                for child in res['childRanges']:
                    # Check if it's a wanted range
                    if ranges:
                        if child['name'] in ranges:
                            children.append({'ref': child['ref'], 'name': child['name']})
                    else:
                        children.append({'ref': child['ref'], 'name': child['name']})

        # Now that we have all child-ranges, find all active IP's in these
        # ranges
        http_method = "GET"
        url = "command/GetIPAMRecords"
        for child in children:
            # Construct the JSON databody
            databody = {'filter': 'state=Assigned', 'rangeRef': child['name']}
            result = doapi(url, http_method, provider, databody)

            # All IPAM records in the range are retrieved. Split it out
            for ipam in result['message']['result']['ipamRecords']:
                # Ansible only needs one combo, so only take the first one
                # from the returned result
                address = ipam['address']
                hostname = ipam['dnsHosts'][0]['dnsRecord']['name']

                # Create all custom property groups. These groups are all
                # called mm_<cp_name>_<cp_value> and to prevent case mixup
                # the names are converted to lowercase and sanitized
                add_host = True
                for custprop in ipam['customProperties']:
                    custval = ipam['customProperties'][custprop]

                    # Create and clean custom property group
                    custgroup = "mm_%s_%s" % (custprop, custval)
                    custgroup = _sanitize(custgroup)

                    # Clean custom properties
                    custprop = _sanitize(custprop)
                    custval = _sanitize(custval)

                    # Also create a group per range
                    rangegrp = 'range_' + _sanitize(child['name'])

                    # Apply filters, if requested. No filter means filters == None
                    if filters:
                        for f in filters:
                            # Is the property in the filter and a wanted value
                            add_host = f.get(custprop, None) == custval

                    # If filter wants this host, add the custom group
                    if add_host:
                        invent['hosts'].append({'name': hostname, 'address': address})
                        if custgroup not in invent['groups']:
                            invent['groups'][custgroup] = []
                        invent['groups'][custgroup].append(hostname)

                        if rangegrp not in invent['groups']:
                            invent['groups'][rangegrp] = []
                        invent['groups'][rangegrp].append(hostname)

                # If filter wants this host, add the host
                if add_host:
                    invent['groups']['all'].append(hostname)
                    invent['groups']['mm_hosts'].append(hostname)

        # Return collected results
        return invent

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        if not self.no_config_file_supplied and os.path.isfile(path):
            self._read_config_data(path)

        # Load cache plugin (Ansible 2.8+)
        # Ansible 2.7- uses a slightly different approach, so that is
        # taken into account.
        try:
            self.load_cache_plugin()
            old_cache = False
        except AttributeError as err:
            old_cache = True

        # Update if caching is enabled and the cache needs refreshing
        use_cache = self.get_option('cache') and cache
        update_cache = False
        if use_cache:
            try:
                # Get the unique cache key
                cache_key = self.get_cache_key(path)
            except KeyError:
                # This occurs if the cache_key is not in the cache or if
                # the cache_key expired, so the cache needs to be updated
                update_cache = True

        # If cache_key was read
        if use_cache:
            try:
                # Read the current inventory from the cache.
                # If this fails, that is either because of a non-existing
                # or an expired cache
                invent = self._cache[cache_key]
            except KeyError:
                # This occurs if the cache_key is not in the cache or if
                # the cache_key expired, so the cache needs to be updated
                update_cache = True

        # Update cache if needed. If user did not define cache, always run
        if update_cache or not use_cache:
            invent = self.get_inventory()

        # Inventory blob is in. Create a complete inventory
        for host in invent['hosts']:
            # Host is a dict with hostname and IP
            self.inventory.add_host(host['name'])
            self.inventory.set_variable(host['name'], 'ansible_host', host['address'])
        for grp in invent['groups']:
            self.inventory.add_group(grp)
            for host in invent['groups'][grp]:
                self.inventory.add_host(host, group=grp)

        # Update cache if needed and requested
        if use_cache:
            if not old_cache:
                self.update_cache_if_changed()

            # When the cache needs updating
            if update_cache:
                if not old_cache:
                    self._cache[cache_key] = invent
                else:
                    # This feature will be removed in version 2.12, but
                    # is needed for the older style cache handling.
                    self.cache.set(cache_key, invent)

        # Clean up the inventory before returning
        self.inventory.reconcile_inventory()
