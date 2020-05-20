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

DOCUMENTATION = '''
    name: mm_inventory
    plugin_type: inventory
    author: Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
    short_description: Ansible dynamic inventory plugin for the Men&Mice Suite.
    version_added: "2.7"
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
'''

EXAMPLES = '''
# Before you execute the following commands, you should make sure this file is
# in your plugin path, and you enabled this plugin.

# Example for using mm_inventory.yml file

plugin: mm_inventory
host: http://mmsuite.example.net
user: apiuser
password: apipasswd

# Then you can run the following command.
# If some of the arguments are missing, Ansible will attempt to read them from
# environment variables.

# ansible-inventory -i /path/to/mm_inventory.yml --list

# Example for reading from environment variables:

# Set environment variables:
# export MM_HOST=YOUR_MM_HOST_ADDRESS
# export MM_USER=YOUR_MM_USER
# export MM_PASSWORD=YOUR_MM_PASSWORD

# Read the inventory from the Men&Mice Suite, and list them.
# The inventory path must always be @mm_inventory if you are reading
# all settings from environment variables.
# ansible-inventory -i @mm_inventory --list
'''

import sys
import re
import os
import json
from ansible.module_utils import six
from ansible.module_utils.urls import Request, urllib_error, ConnectionError, socket, httplib
from ansible.module_utils._text import to_native
from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.module_utils.urls import open_url, SSLValidationError

# Python 2/3 Compatibility
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


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


class InventoryModule(BaseInventoryPlugin,  Constructable, Cacheable):
    NAME = 'mm_inventory'
    # If the user supplies '@mm_inventory' as path, the plugin will read from environment variables.
    no_config_file_supplied = False

    def verify_file(self, path):
        if path.endswith('@mm_inventory'):
            self.no_config_file_supplied = True
            return True
        elif super(InventoryModule, self).verify_file(path):
            return path.endswith(('mm_inventory.yml', 'mm_inventory.yaml',
                                  'mmsuite.yml', 'mandm.yml', 'mandmsuite.yml',
                                  'mmsuite.yaml', 'mandm.yaml', 'mandmsuite.yaml'))
        else:
            return False

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path)
        if not self.no_config_file_supplied and os.path.isfile(path):
            self._read_config_data(path)

        # Read inventory from Men&Mice Suite server.
        provider = {
            'mmurl': self.get_option('host'),
            'user': self.get_option('user'),
            'password': self.get_option('password'),
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
                    children.append({'ref': child['ref'], 'name': child['name']})

        # Now that we have all child-ranges, find all active IP's in these
        # ranges
        http_method = "GET"
        url = "command/GetIPAMRecords"
        for child in children:
            databody = {'filter': 'state=Assigned', 'rangeRef': child['name']}
            result = doapi(url, http_method, provider, databody)

            # All IPAM records in the range retrieved. Split the out
            for ipam in result['message']['result']['ipamRecords']:
                # Ansible only needs one combo, so only take the first one
                # from the returned result
                address = ipam['address']
                hostname = ipam['dnsHosts'][0]['dnsRecord']['name']

                self.inventory.add_host(hostname)
                self.inventory.set_variable(hostname, 'ansible_host', address)

        # Clean up the inventory.
        self.inventory.reconcile_inventory()
