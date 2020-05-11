"""Ansible DHCP reservation module.

Part of the Men&Mice Ansible integration

Module to manage DHCP reservations in the Men&Mice Suite
  - Set or release a DHCP reservation
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
  module: mm_dhcp
  short_description: Manage DHCP reservations on the Men&Mice Suite
  author:
    - Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
  version_added: "2.7"
  description:
    - Manage DHCP reservations on the Men&Mice Suite
  options:
    state:
      description: The state of the claim
      type: bool
      required: False
      choices: [ absent, present ]
      default: present
    name:
      description:
        - Name of the reservation
      type: str
      required: True
    ipaddress:
      description:
        - The IP address(es) to make a reservation on
        - When the IP address is changed a new reservation is made
        - It is not allowed to make reservations in DHCP blocks
      type: list
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
    deleteunspecified:
      description: Clear properties that are not explicitly set
      type: bool
      required: False
    customproperties:
      description:
        - Custom properties for the zone
        - These properties must already exist
`        - See also C(mm_props)
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
- name: Add a reservation for an IP address
  mm_dhcp:
    state: present
    name: myreservation
    ipaddress: 172.16.17.8
    macaddress: 44:55:66:77:88:99
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
        ipaddress=dict(type='list', required=True),
        macaddress=dict(type='str', required=True),
        ddnshost=dict(type='str', required=False, default=""),
        filename=dict(type='str', required=False, default=""),
        servername=dict(type='str', required=False, default=""),
        nextserver=dict(type='str', required=False, default=""),
        deleteunspecified=dict(type='bool', required=False, default=False),
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

    for ipaddress in module.params['ipaddress']:
        # Get the existing reservation for requested IP address
        refs = "IPAMRecords/%s" % ipaddress
        resp = mm.get_single_refs(refs, provider)
        # If the 'invalid' key exists, the request failed.
        if resp.get('invalid', None):
            result.pop('message', None)
            result['warnings'] = resp.get('warnings', None)
            result['changed'] = False
            break

        scopes = mm.get_dhcp_scopes(provider, ipaddress)
        if not scopes:
            errormsg = 'No DHCP scope for IP address %s', ipaddress
            raise AnsibleError(errormsg)

        if resp['ipamRecord']['dhcpReservations']:
            # A reservation for this IP address was found
            if module.params['state'] == 'present':
                # Reservation wanted, already in place so update
                reservations = resp['ipamRecord']['dhcpReservations']
                http_method = "PUT"
                for reservation in reservations:
                    databody = {
                        "ref": reservation['ref'],
                        "saveComment": "Ansible API",
                        "deleteUnspecified": module.params.get('deleteunspecified', False),
                        "properties": [
                            {"name": "name", "value": module.params['name']},
                            {"name": "clientIdentifier", "value": module.params['macaddress']},
                            {"name": "addresses", "value": ipaddress},
                            {"name": "ddnsHostName", "value": module.params.get('ddnshost', '')},
                            {"name": "filename", "value": module.params.get('filename', '')},
                            {"name": "serverName", "value": module.params.get('servername', '')},
                            {"name": "nextServer", "value": module.params.get('nextserver', '')}
                        ]
                    }

                    # Check if the requested data is equal to the current data
                    # How lovely: The API returns the IP address as a list, so it seems
                    # logical to offer the IP address as a list as well. But this is
                    # not allowed, IP address needs to be a string. So that needs
                    # to be taken into consideration.
                    change = False
                    for key in databody['properties']:
                        name = key['name']
                        val  = key['value']
                        if name == 'addresses' and isinstance(val, str):
                            val = [val]

                        # Check if it is in the current values
                        if val != reservation.get(name, 'unknown'):
                            change = True
                            break

                    if change:
                        result['changed'] = True
                        url = "%s" % reservation['ref']
                        result = mm.doapi(url, http_method, provider, databody)
            else:
                # Delete the reservations. Empty body, as the ref is sufficient
                http_method = "DELETE"
                databody = {"saveComment": "Ansible API"}
                for ref in resp['ipamRecord']['dhcpReservations']:
                    if ipaddress in ref['addresses']:
                        url = ref['ref']
                        result = mm.doapi(url, http_method, provider, databody)
        else:
            if module.params['state'] == 'present':
                # If IP address is a string, turn it into a list, as the API
                # requires that
                if isinstance(ipaddress, str):
                    ipaddress = [ipaddress]

                # No reservation found. Create one. Try this in each scope.
                for scope in scopes:
                    http_method = "POST"
                    url = "%s/DHCPReservations" % scope
                    databody = {
                        "saveComment": "Ansible API",
                        "dhcpReservation": {
                            "name": module.params['name'],
                            "clientIdentifier": module.params['macaddress'],
                            "reservationMethod": "HardwareAddress",
                            "addresses": ipaddress,
                            "ddnsHostName": module.params.get('ddnshost', ''),
                            "filename": module.params.get('filename', ''),
                            "serverName": module.params.get('servername', ''),
                            "nextServer": module.params.get('nextserver', '')
                        }
                    }
                    # Define all custom properties, if needed
                    if module.params.get('customproperties', None):
                        props = []
                        for prop in module.params.get('customproperties'):
                            k = prop['name']
                            v = prop['value']
                            props.append({"name": k, "value": v})
                        databody["dhcpReservation"]['customProperties'] = props

                    # Execute the API
                    result = mm.doapi(url, http_method, provider, databody)
            else:
                result['changed'] = False

    # return collected results
    module.exit_json(**result)


def main():
    """Start here."""
    run_module()


if __name__ == '__main__':
    main()
