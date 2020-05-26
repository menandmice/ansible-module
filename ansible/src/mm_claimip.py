"""Ansible Claim IP address module.

Part of the Men&Mice Ansible integration

Module to claim IP addresses in DHCP in the Men&Mice Suite
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
  module: mm_claimip
  short_description: Claim IP addresses in DHCP in the Men&Mice Suite
  author:
    - Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
  version_added: "2.7"
  description:
    - Claim IP addresses in DHCP in the Men&Mice Suite
  options:
    state:
      description: The state of the claim
      type: bool
      required: False
      choices: [ absent, present ]
      default: present
    ipaddress:
      description: The IP address(es) to work on
      type: list
      required: True
    customproperties:
      description:
        - Custom properties for the IP address.
        - These properties must already exist.
        - See also C(mm_props).
      type: dict
      required: False
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
- name: Claim IP address
  mm_claimip:
    state: present
    ipaddress: 172.16.12.14
    provider:
      mmurl: http://mmsuite.example.net
      user: apiuser
      password: apipasswd
  delegate_to: localhost

- name: Release claim on IP addresses
  mm_claimip:
    state: present
    ipaddress:
      - 172.16.12.14
      - 172.16.12.15
      - 172.16.12.16
    provider:
      mmurl: http://mmsuite.example.net
      user: apiuser
      password: apipasswd
  delegate_to: localhost
'''

RETURN = r'''
message:
    description: The output message from the Men&Mice System
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
        customproperties=dict(type='dict', required=False),
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

        ipaddr_ref = resp['ipamRecord']['addrRef']
        curclaim = resp['ipamRecord']['claimed']

        # Set the claim for the IP address
        statebool = mm.STATEBOOL[module.params['state']]
        if curclaim != statebool:
            http_method = "PUT"
            url = ipaddr_ref
            databody = {"ref": ipaddr_ref,
                        "saveComment": "Ansible API",
                        "properties": {
                            "claimed": statebool
                        }
                        }

            # Define all custom properties, if needed
            if module.params.get('customproperties', None):
                for k, v in module.params.get('customproperties').items():
                    databody["properties"][k] = v

            # Execute the API
            result = mm.doapi(url, http_method, provider, databody)
        else:
            result['message'] = 'No claim change for %s' % ipaddress

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()


if __name__ == '__main__':
    main()
