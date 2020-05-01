"""Ansible IP address module.

Part of the Men&Mice Ansible integration

Module to manage IP addresses in the Men&Mice Suite.
  - Claim an IP address in DHCP
  - Set custom properties
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
  module: mm_ipa
  short_description: Manage IP addresses and properties on the Men&Mice Suite
  author:
    - Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
  version_added: "2.7"
  description:
    - Manage IP addresses and properties on the Men&Mice Suite installation
  options:
    ipaddress:
      description: The IP address to work on
      type: str
      required: True
    claimed:
      description: Claim the IP address
      type: bool
      required: False
    dnsrecord:
      description: DNS record definition for the IP address
      type: dict
      required: False
      suboption:
        name:
          description: DNS name of the IP address
          type: str
          required: True
        zone:
          description: Zone to place the name in
          type: str
          required: True
        rrtype:
          description: DNS resource type
          type: str
          required: False
          default: A
        ttl:
          description: Time To Live in seconds
          type: int
          required: False
    dhcpreservation:
        description: Create a DHCP reservation for the IP address
        type: dict
        required: False
        suboption:
          name:
            description: Name of the DHCP reservation
            type: str
            required: True
          macaddress:
            description: MAC address for this IP address
            type: str
            required: True
          ddnshost:
            description: The dynamic DNS host to place the entry in
            type: str
            required: False
          filename:
            description: Filename to place the entry in
            type: str
            required: False
          servername:
            description: Server to place the entry in
            type: str
            required: False
          nextserver:
            description: Next server as DHCP option (bootp)
            type: str
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
        ipaddress=dict(type='str', required=True),
        claimed=dict(type='bool', required=False),
        provider=dict(type='dict', required=True,
                      mmurl=dict(type='str', required=True, no_log=False),
                      user=dict(type='str', required=True, no_log=False),
                      password=dict(type='str', required=True, no_log=True)
                      ),
        dnsrecord=dict(type='dict', required=False),
        dhcpreservation=dict(type='dict', required=False),
    )

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

    # Get the IP address and find the reference
    refs = "IPAMRecords/%s" % module.params['ipaddress']
    resp = mm.get_single_refs(refs, provider)
    ipaddr_ref = resp['ipamRecord']['addrRef']
    curclaim = resp['ipamRecord']['claimed']

    # Set the claim for the IP address
    if module.params['claimed'] is not None and curclaim != module.params['claimed']:
        http_method = "PUT"
        url = ipaddr_ref
        databody = {"ref": ipaddr_ref,
                    "saveComment": "Ansible API",
                    "properties": {
                        "claimed": module.params['claimed']
                    }
                    }
        resp, result = mm.doapi(url, http_method, provider, databody)
        result['message'] = 'Claim set to %s for %s' % (str(module.params['claimed']).lower(), module.params['ipaddress'])

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()

if __name__ == '__main__':
    main()
