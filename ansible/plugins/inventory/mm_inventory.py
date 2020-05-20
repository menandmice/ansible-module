#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Men&Mice
# GNU General Public License v3.0
# see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt
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
      username:
        description: The user that you plan to use to access inventories on your Men&Mice Suite
        type: string
        env:
          - name: MM_USERNAME
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
username: apiuser
password: apipasswd

# Then you can run the following command.
# If some of the arguments are missing, Ansible will attempt to read them from
# environment variables.

# ansible-inventory -i /path/to/mm_inventory.yml --list

# Example for reading from environment variables:

# Set environment variables:
# export MM_HOST=YOUR_MM_HOST_ADDRESS
# export MM_USERNAME=YOUR_MM_USERNAME
# export MM_PASSWORD=YOUR_MM_PASSWORD

# Read the inventory from the Men&Mice Suite, and list them.
# The inventory path must always be @mm_inventory if you are reading
# all settings from environment variables.
# ansible-inventory -i @mm_inventory --list
'''

import re
import os
import json
from ansible.module_utils import six
from ansible.module_utils.urls import Request, urllib_error, ConnectionError, socket, httplib
from ansible.module_utils._text import to_native
from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin

# Python 2/3 Compatibility
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


class InventoryModule(BaseInventoryPlugin):
    NAME = 'mm_inventory'
    # If the user supplies '@mm_inventory' as path, the plugin will read from environment variables.
    no_config_file_supplied = False

    def make_request(self, request_handler, mm_url):
        """Makes the request to given URL, handles errors, returns JSON
        """
        try:
            response = request_handler.get(mm_url)
        except (ConnectionError, urllib_error.URLError, socket.error, httplib.HTTPException) as err:
            error_msg = 'Connection to remote host failed: {err}'.format(err=err)
            # If the Men&Mice Suite gives a readable error message, display that message to the user.
            if callable(getattr(err, 'read', None)):
                error_msg += ' with message: {err_msg}'.format(err_msg=err.read())
            raise AnsibleParserError(to_native(error_msg))

        # Attempt to parse JSON.
        try:
            return json.loads(response.read())
        except (ValueError, TypeError) as e:
            # If the JSON parse fails, print the ValueError
            raise AnsibleParserError(to_native('Failed to parse json from host: {err}'.format(err=e)))

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
        # Note the environment variables will be handled automatically by InventoryManager.
        mm_host = self.get_option('host')

        if not re.match('(?:http|https)://', mm_host):
            mm_host = 'https://{mm_host}'.format(mm_host=mm_host)

        request_handler = Request(url_username=self.get_option('username'),
                                  url_password=self.get_option('password'),
                                  force_basic_auth=True)

        sys.exit(0)
        inventory_url = '/api/v2/inventories/{inv_id}/script/?hostvars=1&towervars=1&all=1'.format(inv_id=inventory_id)
        inventory_url = urljoin(mm_host, inventory_url)

        inventory = self.make_request(request_handler, inventory_url)
        # To start with, create all the groups.
        for group_name in inventory:
            if group_name != '_meta':
                self.inventory.add_group(group_name)

        # Then, create all hosts and add the host vars.
        all_hosts = inventory['_meta']['hostvars']
        for host_name, host_vars in six.iteritems(all_hosts):
            self.inventory.add_host(host_name)
            for var_name, var_value in six.iteritems(host_vars):
                self.inventory.set_variable(host_name, var_name, var_value)

        # Lastly, create to group-host and group-group relationships, and set group vars.
        for group_name, group_content in six.iteritems(inventory):
            if group_name != 'all' and group_name != '_meta':
                # First add hosts to groups
                for host_name in group_content.get('hosts', []):
                    self.inventory.add_host(host_name, group_name)
                # Then add the parent-children group relationships.
                for child_group_name in group_content.get('children', []):
                    self.inventory.add_child(group_name, child_group_name)
            # Set the group vars. Note we should set group var for 'all', but not '_meta'.
            if group_name != '_meta':
                for var_name, var_value in six.iteritems(group_content.get('vars', {})):
                    self.inventory.set_variable(group_name, var_name, var_value)

        # Clean up the inventory.
        self.inventory.reconcile_inventory()
