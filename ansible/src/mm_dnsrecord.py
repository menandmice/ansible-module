"""Ansible DNS Record Management module.

Part of the Men&Mice Ansible integration

Module to manage DNS entries for IP addresses in the Men&Mice Suite
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
  module: mm_dnsrecord
  short_description: Manage DNS records in the Men&Mice Suite
  author:
    - Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
  version_added: "2.7"
  description:
    - Manage Manage DNS records in the Men&Mice Suite
  options:
    state:
        description: The state of the properties or properties
        type: bool
        required: False
        choices: [ absent, present ]
        default: present
    name:
      description:
        - The name of the DNS record
        - Can either be partially or fully qualified
      type: str
      required: True
    data:
      description: The record data in a tab-separated list
      type: str
      required: True
    dnszone:
      description: The DNS zone where the action should take place
      type: str
      required: True
    rrtype:
      description: RR Type for the IP address
      type: str
      required: True
      choices: [
                A, AAAA, CNAME, DNAME,
                DLV, DNSKEY, DS, HINFO,
                LOC, MX, NAPTR, NS,
                NSEC3PARAM, PTR, RP, SOA,
                SPF, SRV, SSHFP, TLSA, TXT
      ]
    ttl:
      description: Specifies the Time-To-Live of the DNS record
      type: str
      required: False
    comment:
      description:
        - Comment string for the record.
        - Note that only records in static DNS zones can have a comment string
      type: str
      required: False
    enabled:
      description:
        - True if the record is enabled.
        - If the record is disabled the value is false
      type: bool
      required: False
      default: False
    aging:
      description:
        - The aging timestamp of dynamic records in AD integrated zones.
        - Hours since January 1, 1601, UTC.
        - Providing a non-zero value creates a dynamic record
      type: int
      required: False
      default: 0
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
- name: Set deinition for custom properties
  mm_dnsrecord:
    name: beatles
    state: present
    rrtype: CNAME
    data: johnpaulgeorgeringo
    dest: zone
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


# Define all available Resource Record types
RRTYPES = [
    'A', 'AAAA', 'CNAME', 'DNAME',
    'DLV', 'DNSKEY', 'DS', 'HINFO',
    'LOC', 'MX', 'NAPTR', 'NS',
    'NSEC3PARAM', 'PTR', 'RP', 'SOA',
    'SPF', 'SRV', 'SSHFP', 'TLSA', 'TXT'
]


def run_module():
    """Run Ansible module."""
    # Define available arguments/parameters a user can pass to the module
    module_args = dict(
        state=dict(type='str', required=False, default='present', choices=['absent', 'present']),
        name=dict(type='str', required=True),
        data=dict(type='str', required=True),
        ttl=dict(type='str', required=False),
        comment=dict(type='str', required=False),
        enabled=dict(type='bool', required=False, default=True),
        aging=dict(type='int', required=False, default=0),
        dnszone=dict(type='str', required=True),
        rrtype=dict(type='str', required=True, choices=RRTYPES),
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

    # Try to get all name of DNS Zone info
    refs = "DNSZones?filter=%s" % module.params.get('dnszone')
    zoneresp = mm.get_single_refs(refs, provider)
    print("=" * 80)
    if zoneresp.get('invalid', False):
        # Zone does not exists
        # return collected results
        module.exit_json(**result)
    zoneref = zoneresp['dnsZones'][0]['ref']

    # And try to get the DNS record with this data
    refs = "%s/DNSRecords?filter=%s" % (zoneref, module.params.get('name'))
    iparesp = mm.get_single_refs(refs, provider)

    # If absent is requested, make a quick delete
    if module.params['state'] == 'absent':
        if iparesp.get('totalResults', 1) == 0:
            # DNS record does not exist. Just return
            result['change'] = False
            module.exit_json(**result)

        # It does exist. Delete it
        http_method = "DELETE"
        url = "%s" % iparesp['dnsRecords'][0]['ref']
        databody = {"saveComment": "Ansible API"}
        result = mm.doapi(url, http_method, provider, databody)
        module.exit_json(**result)

    # Come here the DNS record should be present
    if iparesp.get('totalResults', 1) == 0:
        # Absent, create
        http_method = "POST"
        url = "DNSRecords"
        databody = {
            "saveComment": "Ansible API",
            "dnsRecords": [
                {
                    "name": module.params.get('name'),
                    "type": module.params.get('rrtype'),
                    "ttl": module.params.get('ttl', ""),
                    "data": module.params.get('data'),
                    "comment": module.params.get('comment', ""),
                    "enabled": module.params.get('enabled'),
                    "aging": module.params.get('aging', 0),
                    "dnsZoneRef": zoneref
                }
            ]
        }
        result = mm.doapi(url, http_method, provider, databody)
    else:
        iparef = iparesp['dnsRecords'][0]['ref']
        http_method = "PUT"
        url = "%s" % iparef
        print('iparesp = ', iparesp['dnsRecords'][0])
        databody = {
            "saveComment": "Ansible API",
            "ref": iparef,
            "properties": [
                {"name": "name", "value": module.params.get('name')},
                {"name": "type", "value": module.params.get('rrtype')},
                {"name": "ttl", "value": module.params.get('ttl', "")},
                {"name": "data", "value": module.params.get('data')},
                {"name": "comment", "value": module.params.get('comment', "")},
                {"name": "enabled", "value": module.params.get('enabled')},
                {"name": "aging", "value": module.params.get('aging', 0)},
            ]
        }
        print('databody = ', databody)
        result = mm.doapi(url, http_method, provider, databody)

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()


if __name__ == '__main__':
    main()
