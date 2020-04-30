#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Men&Mice
# GNU General Public License v3.0 (see
# COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Include file with standard functions for Men&Mice modules.

Part of the Men&Mice Ansible integration
"""

import json
from ansible.errors import AnsibleError
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.module_utils.urls import open_url, SSLValidationError
from ansible.utils.display import Display
from ansible.module_utils._text import to_text, to_native

# Make display easier
display = Display()

# The API has another concept of true and false than Python does,
# so 0 is true and 1 is false.
TRUEFALSE = {
    True: 0,
    False: 1,
}

STATEBOOL = {
    'present': True,
    'absent': False
}

def doapi(url, method, provider, databody):
    """Run an API call.

    Parameters:
        - url          -> Relative URL for the API entry point
        - method       -> The API method (GET, POST, DELETE,...)
        - provider     -> Needed credentials for the API provider
        - databody     -> Data needed for the API to perform the task

    Returns:
        - The response from the API call
        - The Ansible result dict
    """
    headers = {'Content-Type': 'application/json'}
    apiurl = "%s/mmws/api/%s" % (provider['mmurl'], url)
    res = {}
    result = {}

    try:
        resp = open_url(apiurl,
                        method=method,
                        url_username=provider['user'],
                        url_password=provider['password'],
                        data=json.dumps(databody),
                        validate_certs=False,
                        headers=headers)

        # Get all API data and format return message
        response = resp.read()
        if response:
            res = json.loads(response)
            result['message'] = json.loads(response)
        else:
            # No response from API
            res = {}
            if resp.status == 200:
                result['message'] = "OK"
            else:
                result['message'] = resp.reason
        result['changed'] = True
    except HTTPError as err:
        errbody = json.loads(err.read().decode())
        if errbody['error']['code'] == 2049:
            result['message'] = "%s: %s" % (err.msg, errbody['error']['message'])
        else:
            result['message'] = "%s: %s" % (err.msg, errbody['error']['message'])
            raise AnsibleError(result['message'])
    except URLError as err:
        raise AnsibleError("Failed lookup url for %s : %s" % (apiurl, to_native(err)))
    except SSLValidationError as err:
        raise AnsibleError("Error validating the server's certificate for %s: %s" % (apiurl, to_native(err)))
    except ConnectionError as err:
        raise AnsibleError("Error connecting to %s: %s" % (apiurl, to_native(err)))

    return res.get('result', ''), result


def getrefs(objtype, provider):
    """Get all objects of a certain type.

    Parameters
        - objtype  -> Object type to get all refs for (User, Group, ...)
        - provider -> Needed credentials for the API provider

    Returns:
        - The response from the API call
        - The Ansible result dict
    """
    return doapi(objtype, "GET", provider, {})


def getsinglerefs(objname, provider):
    """Get all information about a single object.

    Parameters
        - objname  -> Object name to get all refs for (IPAMRecords/172.16.17.201)
        - provider -> Needed credentials for the API provider

    Returns:
        - The response from the API call
        - The Ansible result dict
    """
    return doapi(objname, "GET", provider, {})


def get_dhcp_scopes(provider, ipaddress):
    """Given an IP Address, find the DHCP scopes."""
    url = "Ranges?filter=%s" % ipaddress

    # Get the information of this IP range.
    # I'm not sure if an IP address can be part of multiple DHCP
    # scopes, but in the API it's defined as a list, so find them all.
    resp, dummy = doapi(url, 'GET', provider, {})

    # Gather all DHCP scopes for this IP address
    scopes = []
    if resp:
        for dhcpranges in resp['ranges']:
            for scope in dhcpranges['dhcpScopes']:
                scopes.append(scope['ref'])

    # Return all scopes
    return scopes
