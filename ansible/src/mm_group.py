"""Ansible group module.

Part of the Men&Mice Ansible integration

Module to manage groups in the Men&Mice Suite.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

#IMPORTS_START
import sys
import os
import urllib
import include as mm
from ansible.errors import AnsibleError
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url
from ansible.utils.display import Display
try:
    from ansible.utils_utils.common import json
except ImportError:
    import json
#IMPORTS_END

ANSIBLE_METADATA = {'metadata_version': '0.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
  module: mm_group
  short_description: Manage groups on the Men&Mice Suite
  author:
    - Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
  version_added: "2.7"
  description:
    - Manage groups on a Men&Mice Suite installation
  notes:
    - When in check mode, this module pretends to have done things
      and returns C(changed = True).
  options:
    state:
      description:
        - Should the group exist or not.
      type: str
      required: False
      choices: [ absent, present ]
      default: present
    name:
      description:
        - Name of the group to create, remove or modify.
      type: str
      required: True
      aliases: [ group ]
    descr:
      description: Description of the group.
      required: False
      type: str
    provider:
      description: Definition of the Men&Mice suite API provider.
      type: dict
      required: True
      suboptions:
        mmurl:
          description: Men&Mice API server to connect to.
          required: True
          type: str
        user:
          description: userid to login with into the API.
          required: True
          type: str
        password:
          description: password to login with into the API.
          required: True
          type: str
          no_log: True
'''

EXAMPLES = r'''
- name: Add the 'local' group
    mm_group:
      name: local
      desc: A local group
      state: present
    provider:
      mmurl: http://mmsuite.example.net
      user: apiuser
      password: apipasswd
  delegate_to: localhost

- name: Remove the 'local' group
  mm_group:
    name: local
    state: absent
    provider:
      mmurl: http://mmsuite.example.net
      user: apiuser
      password: apipasswd
  delegate_to: localhost
'''

RETURN = r'''
message:
    description: The output message from the Men&Mice Suite.
    type: str
    returned: always
'''

# Make display easier
display = Display()

#IMPORT_INCLUDE


def run_module():
    """Run Ansible module."""
    # Define available arguments/parameters a user can pass to the module
    module_args = dict(
        state=dict(type='str', required=False, default='present', choices=['absent', 'present']),
        name=dict(type='str', required=True, aliases=['group']),
        desc=dict(type='str', required=False),
        provider=dict(
            type='dict', required=True,
            options=dict(mmurl=dict(type='str', required=True, no_log=False),
                         user=dict(type='str', required=True, no_log=False),
                         password=dict(type='str', required=True, no_log=True)
                         )))

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

    # Get all groups from the Men&Mice server, start with Groups url
    state = module.params['state']
    display.vvv("State:", state)

    # Get list of all groups in the system
    resp = mm.getrefs("Groups", provider)
    groups = resp['message']['result']['groups']
    if resp.get('warnings', None):
        module.fail_json(msg="Collecting groups: %s" % resp.get('warnings'))
    display.vvv("Groups:", groups)

    # Setup loop vars
    group_exists = False
    group_ref = ""

    # Check if the group already exists
    for group in groups:
        if group['name'] == module.params['name']:
            group_exists = True
            group_ref = group['ref']
            group_data = group
            break

    # If requested state is "present"
    if state == "present":
        if group_exists:
            # Group already present, just update.
            http_method = "PUT"
            url = "Groups/%s" % group_ref
            databody = {"ref": group_ref,
                        "saveComment": "Ansible API",
                        "properties": [
                            {"name": 'name', "value": module.params['name']},
                            {"name": 'description', "value": module.params['desc']}
                        ],
                        }

            # Check idempotency
            change = False
            change = (group_data['name'] != module.params['name']) or change
            change = (group_data['description'] != module.params['desc']) or change

            if change:
                result = mm.doapi(url, http_method, provider, databody)
            result['changed'] = change
        else:
            # Group not present, create
            http_method = "POST"
            url = "Groups"
            databody = {"saveComment": "Ansible API",
                        "group": {
                            "name": module.params['name'],
                            "description": module.params['desc'],
                            "builtIn": False,
                            "adIntegrated": False,
                        }
                        }
            result = mm.doapi(url, http_method, provider, databody)
            if result.get('warnings', None):
                module.fail_json(msg=result.get('warnings'))
            group_ref = result['message']['result']['ref']
        # Show some debugging
        display.vvv('databody:', databody)

    # If requested state is "absent"
    if state == "absent":
        url = "Groups"
        databody = {}
        if group_exists:
            # Group present, delete
            http_method = "DELETE"
            url = "Groups/%s" % group_ref
            databody = {"saveComment": "Ansible API"}
            result = mm.doapi(url, http_method, provider, databody)
        else:
            # Group not present, done
            result = {
                'changed': False,
                'message': "Group '%s' doesn't exist" % module.params['name']
            }

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()


if __name__ == '__main__':
    main()
