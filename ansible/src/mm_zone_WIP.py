"""Ansible Zone Management module.

Part of the Men&Mice Ansible integration

Module to manage DNS-Zones in the Men&Mice Suite
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
  module: mm_zone
  short_description: Manage DNS zones in the Men&Mice Suite
  author:
    - Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
  version_added: "2.7"
  description:
    - Manage DNS zones in the Men&Mice Suite
  options:
    state:
      description: The state of the zone
      type: bool
      required: False
      choices: [ absent, present ]
      default: present
    name:
      description: Name of the zone
      type: str
      required: True
    nameserver:
      description: Namserver to define the zone on
      type: str
      required: True
    authority:
      description: Name of the DNS server that contains the zone or
                   the string "[Active Directory]" if the zone is AD integrated
      type: str
      required: False
    servtype:
      description: Type of the master server, like "master" or "slave"
      type: str
      required: True
    desc:
      description: Short description of the zone
      type: str
      required: False
    dynamic:
      description: Dynamic DNS zone
      type: bool
      required: False
      default: False
    masters:
      description: The IP addresses of the master servers if the new zone is
                   not a master zone.
      type: list
      required: False
    dnssecsigned:
      description: True if the zone is a DNSSEC signed zone
      type: bool
      required: False
    kskids:
      description: A comma separated string of IDs of KSKs, starting with
                   active keys, then inactive keys in parenthesis
      type: str
      required: False
    zskids:
      description: A comma separated string of IDs of ZSKs, starting with
                   active keys, then inactive keys in parenthesis
      type: str
      required: False
    adintegrated:
      description: True if the zone is Active Directory integrated
      type: bool
      required: False
    adreplicationtype:
      description: Type of the AD replication
      type: str
      required: False
    adpartition:
      description: The AD partition if the zone is Active Directory integrated
      type: str
      required: False
    customproperties:
      description: Custom properties for the zone, list of properties
      type: list
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
- name: Create a new zone
  mm_zone:
    state: present
    name: example.com
    nameserver: ns1.example.com
    desc: Example zone
    authority: mmsuite.example.net
    customproperties:
      - name: location
        value: Reykjavik
    provider:
      mmurl: http://mmsuite.example.net
      user: apiuser
      password: apipasswd
  delegate_to: localhost

- name: Release a zone
  mm_claimip:
    state: absent
    name: example.com
    nameserver: ns1.example.com
    authority: mmsuite.example.net
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
        name=dict(type='str', required=True),
        nameserver=dict(type='str', required=True),
        authority=dict(type='str', required=False),
        desc=dict(type='str', required=False),
        servtype=dict(type='str', required=False),
        dynamic=dict(type='bool', required=False, default=False),
        masters=dict(type='list', required=False),
        dnssecsigned=dict(type='bool', required=False),
        kskids=dict(type='str', required=False),
        zskids=dict(type='str', required=False),
        adintegrate=dict(type='bool', required=False),
        adreplicationtype=dict(type='str', required=False),
        adpartition=dict(type='str', required=False),
        customproperties=dict(type='list', required=False),
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

    # If absent is requested, make a quick delete
    if module.params['state'] == 'absent':
        http_method = "DELETE"
        url = "DNSZones/%s" % module.params.get('name')
        databody = {}
        result = mm.doapi(url, http_method, provider, databody)
        module.exit_json(**result)

    refs = "DNSZones/%s" % module.params.get('name')
    resp = mm.get_single_refs(refs, provider)
    if resp.get('invalid', None):
        # If the result is 'invalid', the zone does not exist yet
        zoneref = None

    # Come here, we have a zoneref
    if zoneref:
        # The zone exists, update: TODO
        pass
    else:
        # Get the existing DNS View for the nameserver
        refs = "DNSViews?dnsServerRef=%s" % module.params.get('nameserver')
        resp = mm.get_single_refs(refs, provider)
        # If the 'invalid' key exists, the request failed.
        if resp.get('invalid', None):
            result.pop('message', None)
            result['warnings'] = resp.get('warnings', None)
            result['changed'] = False
            module.exit_json(**result)
        dnsview_ref = resp['dnsViews'][0]['ref']

        # Create the API call
        http_method = "POST"
        url = "dnsZones"
        databody = {
            "saveComment": "Ansible API",
            "dnsZone": {
                "name": module.params['name'],
                "dnsViewRef": dnsview_ref,
                "dynamic": module.params['dynamic'],
                "authority": module.params['authority'],
                "type": module.params['servtype'],
            }
        }
        masters = module.params.get('masters', None)
        if module.params['servtype'] != 'Master' and masters is not None:
            databody["masters"] = masters
        if module.params.get('dnssecsigned'):
            databody["dnsZone"]["dnssecSigned"] = module.params.get('dnssecsigned')
        if module.params.get('kskids'):
            databody["dnsZone"]["kskIDs"] = module.params.get('kskids')
        if module.params.get('zskids'):
            databody["dnsZone"]["zskIDs"] = module.params.get('zskids')
        if module.params.get('adIntegrated'):
            databody["dnsZone"]["adIntegrated"] = module.params.get('adintegrated')
        if module.params.get('adReplicationType'):
            databody["dnsZone"]["adReplicationType"] = module.params.get('adreplicationtype')
        if module.params.get('adPartition'):
            databody["dnsZone"]["adPartition"] = module.params.get('adpartition')

        resp = mm.doapi(url, http_method, provider, databody)
        # If not an invalid result, the zone is created. Get the ref
        if resp.get('invalid', None):
            result.pop('message', None)
            result['warnings'] = resp.get('warnings', None)
            result['changed'] = False
            module.exit_json(**result)

        # Now create all custom properties, if needed
        if module.params.get('customproperties', None):
            zoneref = resp['message']['result']['ref']
            url = "%s/PropertyDefinitions" % zoneref
            props = []
            for prop in module.params.get('customproperties'):
                k = prop['name']
                v = prop['value']

                # Build the propertie list
                props.append({"name": k, "value": v})

                refs = "%s/%s" % (url, k)
                resp = mm.get_single_refs(refs, provider)

                if not resp.get('invalid', None):
                    # Property does not exist
                    http_method = "POST"

                    # Make sure the property exists
                    databody = {
                        "saveComment": "Ansible API",
                        "propertyDefinition": {
                            "name": k,
                            "type": "String"
                        }
                    }
                    resp = mm.doapi(url, http_method, provider, databody)

                    # If not an invalid result, the property is created
                    if resp.get('invalid', None):
                        result.pop('message', None)
                        result['warnings'] = resp.get('warnings', None)
                        result['changed'] = False
                        module.exit_json(**result)

                # And update the value
                http_method = "POST"
                databody = {
                    "saveComment": "Ansible API",
                    "ref": zoneref,
                    "properties": props
                }
                resp = mm.doapi(url, http_method, provider, databody)

                # If not an invalid result, the property is created
                if resp.get('invalid', None):
                    result.pop('message', None)
                    result['warnings'] = resp.get('warnings', None)
                    result['changed'] = False
                    module.exit_json(**result)

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()

if __name__ == '__main__':
    main()
