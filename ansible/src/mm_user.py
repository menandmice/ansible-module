"""Ansible user module.

Part of the Men&Mice Ansible integration

Module to manage users in the Men&Mice Suite.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

#IMPORTS_START
import sys
import os
import urllib
import mm_include as mm
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
        - Whether the account should exist or not, taking action if the state
          is different from what is stated.
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
      description:
        - Users password (plaintext)
        - Required if I(state=present)
      type: str
      required: False
    descr:
      description: Description of the user
      required: False
      type: str
    email:
      description: The users email address
      required: False
      type: str
    authentication_type:
      description:
        - Authentication type to use. e.g. Internal, AD
        - Required if I(state=present)
      required: False
      type: str
    groups:
      description: Make the user a member of these groups
      required: False
      type:
      elements: str
    roles:
      description: Make the user a member of these roles
      required: False
      type: list
      elements: str
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
    authentication_type: internal
    roles:
        - Administrators (built-in)
        - DNS Administrators (built-in)
        - DHCP Administrators (built-in)
        - IPAM Administrators (built-in)
        - User Administrators (built-in)
        - Approvers (built-in)
        - Requesters (built-in)
    provider:
      mmurl: http://mmsuite.example.net
      user: apiuser
      password: apipasswd
  delegate_to: localhost

- name: Remove user 'johnd'
  mm_user:
    username: johnd
    state: absent
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

#IMPORT_INCLUDE


def run_module():
    """Run Ansible module."""
    # Define available arguments/parameters a user can pass to the module
    module_args = dict(
        state=dict(type='str', required=False, default='present', choices=['absent', 'present']),
        username=dict(type='str', required=True, aliases=['user']),
        password=dict(type='str', required=False, no_log=True),
        full_name=dict(type='str', required=False),
        desc=dict(type='str', required=False),
        email=dict(type='str', required=False),
        authentication_type=dict(type='str', required=False),
        groups=dict(type='list', required=False),
        roles=dict(type='list', required=False),
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

    # Get all users from the Men&Mice server, start with Users url
    state = module.params['state']
    display.vvv("State:", state)

    # Get list of all users in the system
    resp = mm.getrefs("Users", provider)
    users = resp['message']['result']['users']
    if resp.get('warnings', None):
        module.fail_json(msg="Collecting users: %s" % resp.get('warnings'))
    display.vvv("Users:", users)

    # If groups are requested, get all groups
    if module.params['groups']:
        resp = mm.getrefs("Groups", provider)
        if resp.get('warnings', None):
            module.fail_json(msg="Collecting groups: %s" % resp.get('warnings'))
        groups = resp['message']['result']['groups']
        display.vvv("Groups:", groups)

    # If roles are requested, get all roles
    if module.params['roles']:
        resp = mm.getrefs("Roles", provider)
        if resp.get('warnings', None):
            module.fail_json(msg="Collecting roles: %s" % resp.get('warnings'))
        roles = resp['message']['result']['roles']
        display.vvv("Roles:", roles)

    # Setup loop vars
    user_exists = False
    user_ref = ""

    # Check if the user already exists
    for user in users:
        if user['name'] == module.params['username']:
            user_exists = True
            user_ref = user['ref']
            user_data = user
            break

    # If requested state is "present"
    if state == "present":
        # If the users needs to be present, a password is required
        if not module.params['password']:
            module.fail_json(msg='missing required arguments: password')

        if not module.params['authentication_type']:
            module.fail_json(msg='missing required arguments: authentication_type')

        # Check if all requested groups exist
        if module.params['groups']:
            # Create a list with all names, for easy checking
            names = []
            for grp in groups:
                names.append(grp['name'])

            # Check all requested names against the names list
            for name in module.params['groups']:
                if name not in names:
                    module.fail_json(msg="Requested a non existing group: %s" % name)

        # Check if all requested roles exist
        if module.params['roles']:
            # Create a list with all names, for easy checking
            names = []
            for role in roles:
                names.append(role['name'])

            # Check all requested names against the names list
            for name in module.params['roles']:
                if name not in names:
                    module.fail_json(msg="Requested a non existing role: %s" % name)

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

        # Fix capitalization for the authenticationType
        if module.params['authentication_type'].lower() == 'internal':
            module.params['authentication_type'] = 'Internal'
        else:
            module.params['authentication_type'] = module.params['authentication_type'].upper()

        if user_exists:
            # User already present, just update. As it is not possible to
            # determine the current password, this will always be executed
            # and we pretend not to be changed.
            http_method = "PUT"
            url = "Users/%s" % user_ref
            databody = {"ref": user_ref,
                        "saveComment": "Ansible API",
                        "properties": [
                            {"name": 'name', "value": module.params['username']},
                            {"name": 'password', "value": module.params['password']},
                            {"name": 'fullName', "value": module.params['full_name']},
                            {"name": 'authenticationType', "value": module.params['authentication_type']},
                        ],
                        }
            result = mm.doapi(url, http_method, provider, databody)
            result['changed'] = False

            # Now figure out if groups need to be added or deleted
            # The ones in the playbook are in `wanted_(roles|groups)`
            # and the users ref is in `user_ref` and all users data is
            # in `user_data`
            display.vvv("wanted  groups =", wanted_groups)
            display.vvv("current groups =", user_data['groups'])
            display.vvv("wanted  roles  =", wanted_roles)
            display.vvv("current roles  =", user_data['roles'])

            # Add or delete a user to or from a group
            # API call with PUT or DELETE
            # http://mandm.example.net/mmws/api/Groups/6/Users/31
            databody = {"saveComment": "Ansible API"}
            for thisgrp in wanted_groups + user_data['groups']:
                http_method = ""
                if (thisgrp in wanted_groups) and (thisgrp not in user_data['groups']):
                    # Wanted but not yet present.
                    http_method = "PUT"
                elif (thisgrp not in wanted_groups) and (thisgrp in user_data['groups']):
                    # Present, but not wanted
                    http_method = "DELETE"

                # Execute wanted action
                if http_method:
                    display.vvv("Executing %s on %s for %s" % (http_method, thisgrp['ref'], user_ref))
                    url = "%s/%s" % (thisgrp['ref'], user_ref)
                    result = mm.doapi(url, http_method, provider, databody)
                    result['changed'] = True

            # Be aware. Calling adding and deleting roles and groups is just the
            # otherway around!
            # http://mandm.example.net/mmws/api/Users/31/Roles/2
            for thisrole in wanted_roles + user_data['roles']:
                http_method = ""
                if (thisrole in wanted_roles) and (thisrole not in user_data['roles']):
                    # Wanted but not yet present.
                    http_method = "PUT"
                elif (thisrole not in wanted_roles) and (thisrole in user_data['roles']):
                    # Present, but not wanted
                    http_method = "DELETE"

                # Execute wanted action
                if http_method:
                    display.vvv("Executing %s on %s for %s" % (http_method, thisrole['ref'], user_ref))
                    url = "%s/%s" % (user_ref, thisrole['ref'])
                    result = mm.doapi(url, http_method, provider, databody)
                    result['changed'] = True
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
            result = mm.doapi(url, http_method, provider, databody)
            if result.get('warnings', None):
                module.fail_json(msg=result.get('warnings'))
            user_ref = result['message']['result']['ref']

            # For some reason the Groups are not accepted, so just loop over it
            databody = {"saveComment": "Ansible API"}
            for grp in wanted_groups:
                http_method = "PUT"
                url = "%s/%s" % (grp['ref'], user_ref)
                print(url)
                result = mm.doapi(url, http_method, provider, databody)

            # For some reason the Roles are not accepted, so just loop over it
            databody = {"saveComment": "Ansible API"}
            for role in wanted_roles:
                http_method = "PUT"
                url = "%s/%s" % (user_ref, role['ref'])
                print(url)
                result = mm.doapi(url, http_method, provider, databody)

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
            databody = {"saveComment": "Ansible API"}
            result = mm.doapi(url, http_method, provider, databody)
        else:
            # User not present, done
            result = {
                'changed': False,
                'message': "User '%s' doesn't exist" % module.params['username']
            }

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()


if __name__ == '__main__':
    main()
