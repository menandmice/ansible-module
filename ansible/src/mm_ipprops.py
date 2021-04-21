"""Ansible IP properties address module.

Part of the Men&Mice Ansible integration

Module to set properties on an IP addresses in Micetro
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
  module: mm_pprops
  short_description: Set properties on an IP address in Micetro
  author:
    - Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
  version_added: "2.7"
  description:
    - Set properties on an IP address in Micetro
    - This can be properties as custom properties, claim and so on
  notes:
    - When in check mode, this module pretends to have done things
      and returns C(changed = True).
  options:
    state:
      description: Property present or not.
      type: bool
      required: False
      choices: [ absent, present ]
      default: present
    ipaddress:
      description: The IP address(es) to work on.
      type: list
      elements: str
      required: True
    deleteunspecified:
      description: Clear properties that are not explicitly set.
      type: bool
      required: False
      default: False
    properties:
      description:
        - Custom properties for the IP address.
        - These properties must already be defined.
      seealso: See also M(mm_props)
      type: dict
      required: True
    provider:
      description: Definition of the Micetro API provider.
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
- name: Set properties on IP
  mm_ipprops:
    state: present
    ipaddress: 172.16.12.14
    properties:
      claimed: false
      location: London
    provider:
      mmurl: http://micetro.example.net
      user: apiuser
      password: apipasswd
  delegate_to: localhost
'''

RETURN = r'''
message:
    description: The output message from the Men&Mice System.
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
        ipaddress=dict(type='list', required=True),
        properties=dict(type='dict', required=True),
        deleteunspecified=dict(type='bool', required=False, default=False),
        provider=dict(
            type='dict', required=True,
            options=dict(mmurl=dict(type='str', required=True, no_log=False),
                         user=dict(type='str', required=True, no_log=False),
                         password=dict(type='str', required=True, no_log=True)
                         )))

    # Seed the result dict in the object
    # We primarily care about changed and state
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

    for ipaddress in module.params['ipaddress']:
        # Get the IP address and find the reference
        # If the 'invalid' key exists, the request failed.
        refs = "IPAMRecords/%s" % ipaddress
        resp = mm.get_single_refs(refs, provider)
        if resp.get('invalid', None):
            result.pop('message', None)
            result['warnings'] = resp.get('warnings', None)
            result['changed'] = False
            break
        curstat = resp['ipamRecord']

        # Get the IP address reference
        ipaddr_ref = resp['ipamRecord']['addrRef']

        # Set the properties for the IP address
        http_method = "PUT"
        url = ipaddr_ref
        databody = {"ref": ipaddr_ref,
                    "saveComment": "Ansible API",
                    "deleteUnspecified": module.params.get('deleteunspecified'),
                    "properties": {}
                    }

        # Define all custom properties, if needed
        for key, val in module.params.get('properties').items():
            databody["properties"][key] = val

        # Find out if a change is needed
        change = False
        str2bool = {'true': True, 'false': False}
        for key, val in databody['properties'].items():
            # The value from the parameters is always type str
            # but the API could return bool. So, convert the string
            # to boolean
            if isinstance(val, str) and (val.lower() in str2bool):
                val = str2bool[val.lower()]

            # The property could be in the standard list or in the
            # customProperties dict
            if key in curstat:
                if curstat.get(key) != val:
                    change = True
                    break
            elif key in curstat['customProperties']:
                if curstat['customProperties'].get(key) != val:
                    change = True
                    break
            else:
                # This property does not exist, yet. Make sure it's created
                change = True

        # If 'deleteunspecified' is set, assume an 'change always'
        if module.params.get('deleteunspecified'):
            change = True

        # Execute the API
        if change:
            result = mm.doapi(url, http_method, provider, databody)

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()


if __name__ == '__main__':
    main()
