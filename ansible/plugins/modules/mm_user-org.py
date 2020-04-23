#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2019, Men & Mice
# GNU General Public License v3.0 (see
# COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible user module.

Part of the Men&Mice Ansible integration

Module to manage users in the Men&Mice Suite.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type
import json
import urllib
from ansible.errors import AnsibleError, AnsibleModuleError
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url
from ansible.module_utils._text import to_text
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
    description: The output message from the Men & Mice System
    type: str
    returned: always
'''

# Make display easier
display = Display()
# The API has another concept of true and false than Python does,
# so 0 is true and 1 is false.
TRUEFALSE = {
    True: 0,
    False: 1,
}


def run_module():
    """Run Ansible module."""
    # define available arguments/parameters a user can pass to the module
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
        provider=dict(type='dict', required=True, no_log=True),
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = {
        'changed': False,
        'message': ''
    }

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    provider = module.params['provider']
    display.vvv(provider)

    headers = {'Content-Type': 'application/json'}
    url = "%s/mmws/api/Users" % provider['mmurl']
    state = module.params['state']
    display.vvv("State:", state)

    resp = {}

    # If groups are requested, get all groups


    # get list of all users in the system
    databody = {}

    try:
        resp = open_url(url, method="GET",
                        url_username=provider['user'],
                        url_password=provider['password'],
                        data=json.dumps(databody),
                        validate_certs=False,
                        headers=headers)

        res = json.loads(resp.read())
        users = res['result']['users']

    except urllib.error.HTTPError as err:
        display.vvv('Error while connecting to Men & Mice webservice:', err.code)
        errbody = json.loads(err.read().decode())
        result['message'] = "%s: %s" % (err.msg, errbody['error']['message'])
        raise AnsibleError(result['message'])

    user_exists = False
    user_ref = ""
    skip = False
    expect_response = True
    http_method = "GET"

    for user in users:
        if user['name'] == module.params['username']:
            user_exists = True
            user_ref = user['ref']

    if state == "present":
        http_method = "POST"
        if user_exists:
            url = "%s/%s" % (url, user_ref)
            databody = {"ref": user_ref,
                        "saveComment": "Ansible API",
                        "properties": [
                            {"name": 'name', "value": module.params['username']},
                            {"name": 'password', "value": module.params['password']},
                            {"name": 'fullName', "value": module.params['full_name']},
                            {"name": 'authenticationType', "value": module.params['authentication_type']}
                        ]}
        else:
            databody = {"saveComment": "Ansible API",
                        "user": {
                            "name": module.params['username'],
                            "password": module.params['password'],
                            "fullName": module.params['full_name'],
                            "description": module.params['desc'],
                            "email": module.params['email'],
                            "authenticationType": module.params['authentication_type']
                        }}

    if state == "absent":
        if user_exists:
            http_method = "DELETE"
            expect_response = False
            url = url + "/" + user_ref
            url = "%s/%s" % (url, user_ref)
        else:
            skip = True

    display.vvv("URL:", url)
    display.vvv("Method:", http_method)
    display.vvv("DATA:", databody)
    display.vvv("Skip:", skip)

    print(json.dumps(databody, sort_keys=True, indent=4, separators=(',', ': ')))

    if not skip:
        try:
            print(url, http_method,
                  provider['user'],
                  provider['password'],
                  json.dumps(databody),
                  False,
                  {'Content-Type': 'application/json'})
            resp = open_url(url, method=http_method,
                            url_username=provider['user'],
                            url_password=provider['password'],
                            data=json.dumps(databody),
                            validate_certs=False,
                            headers={'Content-Type': 'application/json'})
            response = resp.read()
            if expect_response:
                result['message'] = json.loads(response)
            else:
                if resp.status == 200:
                    result['message'] = "OK"
                else:
                    result['message'] = resp.reason
            result['changed'] = True
        except urllib.error.HTTPError as err:
            display.vvv('Error', err.code)
            errbody = json.loads(err.read().decode())
            result['message'] = "%s: %s" % (err.msg, errbody['error']['message'])

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()

if __name__ == '__main__':
    main()
