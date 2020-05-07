"""Ansible Custom Properties Management module.

Part of the Men&Mice Ansible integration

Module to manage DNS-Zone custom properties in the Men&Mice Suite
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
  module: mm_props
  short_description: Manage DNS-Zone custom properties in the Men&Mice Suite
  author:
    - Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
  version_added: "2.7"
  description:
    - Manage DNS-Zone custom properties in the Men&Mice Suite
  options:
    state:
        description: The state of the properties or properties
        type: bool
        required: False
        choices: [ absent, present ]
        default: present
    name:
        description: Name of the property
        required: True
        type: str
    proptype:
        description:
          - Type of the property
          - These are not the types as described in the API, but the types
            as you can see them in the Men&Mice Management Console
        choices: [ text, yesno, ipaddress, number ]
        required: False
        type: str
        default: text
    dest:
        description: Where to define the custom property
        choices: [ dnsserver, dhcpserver, zone, iprange, ipaddress, device, interface, cloudnet, cloudaccount ]
        required: True
        type: str
    madatory:
        description: Is the property mandatory
        required: False
        type: bool
        default: False
    system:
        description: Is the property system defined
        required: False
        type: bool
        default: False
    readonly:
        description: Is the property read only
        required: False
        type: bool
        default: False
    multiline:
        description: Is the property multiline
        required: False
        type: bool
        default: False
    defaultvalue
        description: Default value of the property
        required: False
        type: str
    listitems:
        description: The items in the selection list.
        required: False
        type: list
    cloudtags:
        description: Associated cloud tags
        required: False
        type: list
    updateexisting:
        description:
         - Should objects be updated with the new values
         - Only valid when updating a property, otherwise ignored
        required: False
        type: bool
        default: False
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
  mm_props:
    name: location
    state: present
    proptype: text
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


PROPTYPES = ['text', 'yesno', 'ipaddress', 'number']
DESTTYPES = ['dnsserver', 'dhcpserver', 'zone', 'iprange', 'ipaddress',
             'device', 'interface', 'cloudnet', 'cloudaccount']

DEST2URL = {
    'dnsserver': 'DNSServers',
    'dhcpserver': 'DHCPServers',
    'zone': 'DNSZones',
    'iprange': 'Ranges',
    'ipaddress': 'IPAMRecords',
    'device': 'Devices',
    'interface': 'Interfaces',
    'cloudnet': 'CloudNetworks',
    'cloudaccount': 'CloudServiceAccounts'
}

TYPE2TYPE = {
    'text': 'String',
    'yesno': 'Boolean',
    'ipaddress': 'IPAddress',
    'number': 'Integer',
}

def run_module():
    """Run Ansible module."""
    # Define available arguments/parameters a user can pass to the module
    module_args = dict(
        name=dict(type='str', required=True),
        state=dict(type='str', required=False, default='present', choices=['absent', 'present']),
        proptype=dict(type='str', required=False, default='text', choices=PROPTYPES),
        dest=dict(type='str', required=True, choices=DESTTYPES),
        mandatory=dict(type='bool', required=False, default=False),
        readonly=dict(type='bool', required=False, default=False),
        multiline=dict(type='bool', required=False, default=False),
        system=dict(type='bool', required=False, default=False),
        updateexisting=dict(type='bool', required=False, default=False),
        defaultvalue=dict(type='str', required=False, default=''),
        cloudtags=dict(type='list', required=False, default=[]),
        listitems=dict(type='list', required=False, default=[]),
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

    # Check if the property is already present
    http_method = "GET"
    url = "%s/1/PropertyDefinitions/%s" % (DEST2URL[module.params.get('dest')],
                                           module.params.get('name'))
    databody = {}
    resp = mm.doapi(url, http_method, provider, databody)

    # If absent is requested, make a quick delete
    # Just use `1` as the reference, as it should always be there
    if module.params['state'] == 'absent':
        if not resp.get('warnings', None):
            # Property is present, deletion is required
            http_method = "DELETE"
            url = "%s/1/PropertyDefinitions/%s" % (DEST2URL[module.params.get('dest')],
                                                   module.params.get('name'))
            databody = {}
            result = mm.doapi(url, http_method, provider, databody)
        module.exit_json(**result)

    # Whether adding or updating the property, the databody is almost the
    # same. So, define it once and change things when needed.
    databody = {
        "propertyDefinition": {
            "name": module.params.get('name'),
            "type": TYPE2TYPE[module.params.get('proptype')],
            "system": module.params.get('system'),
            "mandatory": module.params.get('mandatory'),
            "readOnly": module.params.get('readonly'),
            "multiLine": module.params.get('multiline'),
            "defaultValue": module.params.get('defaultvalue', ''),
        }
    }

    # Add the extra parameters when wanted
    if module.params.get('proptype') == 'text':
        # Tags are only supported for customfields of type string
        databody['propertyDefinition']['cloudTags'] = module.params.get('cloudtags', [])
        # Only string type custom properties can have a list of predefined values
        databody['propertyDefinition']['listItems'] = module.params.get('listitems', [])

    # Check if the property needs to be created or updated
    if resp.get('warnings', None):
        # Not there, yet. Create the property
        http_method = "POST"
        url = "%s/1/PropertyDefinitions" % DEST2URL[module.params.get('dest')]
    else:
        # Property already exists, check if it needs an update
        curprop = resp['message']['result']

        # To bad it is not possible to just compare two dicts.
        # When the property type is not string it is not allowed to have
        # tags and a predefined list. So they cannot be in the databody.
        # But a request to the API does return them as empty lists.
        # So, just loop.
        for k in databody:
            if databody[k] != curprop[k]:
                break
        else:
            # Current property in Men&Mice matches wanted property
            # No change needed
            result['changed'] = False
            module.exit_json(**result)

        http_method = "PUT"
        url = "%s/1/PropertyDefinitions/%s" % (DEST2URL[module.params.get('dest')],
                                               module.params.get('name'))

        # Add the extra parameters when wanted
        if module.params.get('updateexisting', None):
            databody['updateExisting'] = module.params.get('updatexisting')

    databody['saveComment'] = 'Ansible API'
    result = mm.doapi(url, http_method, provider, databody)

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()

if __name__ == '__main__':
    main()
