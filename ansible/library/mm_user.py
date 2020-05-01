#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Men&Mice
# GNU General Public License v3.0 (see
# COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible user module.

Part of the Men&Mice Ansible integration

Module to manage users in the Men&Mice Suite.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

# Set the library search path (add .../../lib) to ensure the modules can be
# found
import sys
import os
import json
import urllib
import mm_include as mm
from ansible.errors import AnsibleError
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url
from ansible.utils.display import Display

ANSIBLE_METADATA = {'metadata_version': '0.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
  module: mm_user
  short_description: Manage user accounts and user properties on the Men&Mice Suite
  author:
    - Carsten Strotmann <carsten@menandmice.training>
    - Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
  version_added: "2.7"
  description:
    - Manage user accounts and user attributes on a Men&Mice Suite installation
  options:
    state:
      description:
        - Whether the account should exist or not, taking action if the state is different from what is stated.
      type: str
      required: False
      choices: [ absent, present ]
      default: present
    name:
      description:
        - Name of the user to create, remove or modify.
      type: str
      required: True
      aliases: [ user ]
    password:
      description: Users password (plaintext)
      type: str
      required: True
    descr:
      description: Description of the user
      required: False
      type: str
    email:
      description: The users email address
      required: False
      type: str
    authentication_type:
      description: Authentication type to use. e.g. internal, AD
      required: True
      type: str
    groups:
      description: Make the user a member of these groups
      required: False
      type: list
    roles:
      description: Make the user a member of these roles
      required: False
      type: list
    provider:
      description: Definition of the Men&Mice suite API provider
      type: dict
      required: True
      suboptions:
        mmurl:
          description: Men&Mice API server to connect to
          required: True
          type: str
        user:
          description: userid to login with into the API
          required: True
          type: str
        password:
          description: password to login with into the API
          required: True
          type: str
          no_log: True
'''

EXAMPLES = r'''
- name: Add the user 'johnd' as an admin
  mm_user:
    username: johnd
    password: password
    full_name: John Doe
    state: present
    provider:
      mmurl: http://mmsuite.example.net
      user: apiuser
      password: apipasswd
  delegate_to: localhost
'''

RETURN = r'''
message:
    description: The output message from the Men&Mice Suite
    type: str
    returned: always
'''

# Make display easier
display = Display()


def get_dhcp_zone(provider, ipaddress):
    """Given an IP Address, find the DHCP Zones."""
    url = "Ranges?filter=%s" % ipaddress

    result = mm.doapi(url, 'GET', provider, {})
    print("DHCP ->", resp)


def run_module():
    """Run Ansible module."""
    # Define available arguments/parameters a user can pass to the module
    module_args = dict(
        state=dict(type='str', required=False, default='present', choices=['absent', 'present']),
        username=dict(type='str', required=True, aliases=['user']),
        password=dict(type='str', required=True, no_log=True),
        full_name=dict(type='str', required=False),
        desc=dict(type='str', required=False),
        email=dict(type='str', required=False),
        authentication_type=dict(type='str', required=True),
        groups=dict(type='list', required=False),
        roles=dict(type='list', required=False),
        provider=dict(type='dict', required=True,
            options=dict(
                mmurl=dict(type='str', required=True, no_log=False),
                user=dict(type='str', required=True, no_log=False),
                password=dict(type='str', required=True, no_log=True)
            )
        )
    )

    # Seed the result dict in the object
    # Se primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = {
        'changed': False,
        'message': ''
    }

    # The AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # If the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    # Get all API settings
    provider = module.params['provider']
    display.vvv(provider)

    # Get all users from the Men&Mice server, start with Users url
    state = module.params['state']
    display.vvv("State:", state)

    # Get list of all users in the system
    resp, result = mm.getrefs("Users", provider)
    users = resp['users']
    display.vvv("Users:", users)

    # If groups are requested, get all groups
    if module.params['groups']:
        resp, result = mm.getrefs("Groups", provider)
        groups = resp['groups']
        display.vvv("Groups:", groups)

    # If roles are requested, get all roles
    if module.params['roles']:
        resp, result = mm.getrefs("Roles", provider)
        roles = resp['roles']
        display.vvv("Roles:", roles)

    # Setup loop vars
    user_exists = False
    user_ref = ""
    skip = False

    # Check if the user already exists
    for user in users:
        if user['name'] == module.params['username']:
            user_exists = True
            user_ref = user['ref']
            break

    # If requested state is "present"
    if state == "present":
        # Create a list of wanted groups
        wanted_groups = []
        if module.params['groups']:
            for group in groups:
                if group['name'] in module.params['groups']:
                    # This group is wanted
                    wanted_groups.append({"ref": group['ref'],
                                          "objType": "Groups",
                                          "name": group['name']})

        wanted_roles = []
        # Create a list of wanted roles
        if module.params['roles']:
            for role in roles:
                if role['name'] in module.params['roles']:
                    # This roles is wanted
                    wanted_roles.append({"ref": role['ref'],
                                         "objType": "Roles",
                                         "name": role['name']})

        if user_exists:
            # User already present, just update
            http_method = "PUT"
            url = "Users/%s" % user_ref
            databody = {"ref": user_ref,
                        "saveComment": "Ansible API",
                        "properties": {
                            "name": module.params['username'],
                            "password": module.params['password'],
                            "fullName": module.params['full_name'],
                            "email": module.params['email'],
                            "authenticationType": module.params['authentication_type'],
                            "groups": wanted_groups,
                            "roles": wanted_roles
                        }
                        }
        else:
            # User not present, create
            http_method = "POST"
            url = "Users"
            databody = {"saveComment": "Ansible API",
                        "user": {
                            "name": module.params['username'],
                            "password": module.params['password'],
                            "fullName": module.params['full_name'],
                            "description": module.params['desc'],
                            "email": module.params['email'],
                            "authenticationType": module.params['authentication_type'],
                            "groups": wanted_groups,
                            "roles": wanted_roles
                        }
                        }

        # Show some debugging
        display.vvv('databody:', databody)

    # If requested state is "absent"
    if state == "absent":
        url = "Users"
        databody = {}
        if user_exists:
            # User present, delete
            http_method = "DELETE"
            url = "Users/%s" % user_ref
        else:
            # User not present, done
            result = {
                'changed': False,
                'message': "User '%s' doesn't exist" % module.params['username']
            }
            skip = True

    if not skip:
        result = mm.doapi(url, http_method, provider, databody)

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()

if __name__ == '__main__':
    main()
