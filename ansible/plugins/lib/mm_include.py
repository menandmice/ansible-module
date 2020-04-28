#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Men&Mice
# GNU General Public License v3.0 (see
# COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Include file with standard functions for Men&Mice modules

Part of the Men&Mice Ansible integration
"""

import json
import urllib
from ansible.errors import AnsibleError
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url
from ansible.utils.display import Display

# Make display easier
display = Display()
# The API has another concept of true and false than Python does,
# so 0 is true and 1 is false.
TRUEFALSE = {
    True: 0,
    False: 1,
}

def doapi(url, method, provider, databody, result):
    """Run an API call.

    Parameters:
        - url          -> Relative URL for the API entry point
        - method       -> The API method (GET, POST, DELETE,...)
        - provider     -> Needed credentials for the API provider
        - databody     -> Data needed for the API to perform the task
        - result       -> Result dict for the end result of the module

    Returns:
        - The response from the API call
        - The Ansible result dict
    """
    headers = {'Content-Type': 'application/json'}
    apiurl = "%s/mmws/api/%s" % (provider['mmurl'], url)

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
    except urllib.error.HTTPError as err:
        display.vvv('Error while connecting to Men & Mice webservice:', err.code)
        errbody = json.loads(err.read().decode())
        result['message'] = "%s: %s" % (err.msg, errbody['error']['message'])
        raise AnsibleError(result['message'])

    return res.get('result', ''), result


def getrefs(objtype, provider):
    """Get all objects of a certain type

    Parameters
        - objtype  -> Object type to get all refs for (User, Group, ...)
        - provider -> Needed credentials for the API provider

    Returns:
        - The response from the API call
        - The Ansible result dict
    """
    result = {}
    return doapi(objtype, "GET", provider, {}, result)


def getsinglerefs(objname, provider):
    """Get all information about a single object

    Parameters
        - objname  -> Object name to get all refs for (IPAMRecords/172.16.17.201)
        - provider -> Needed credentials for the API provider

    Returns:
        - The response from the API call
        - The Ansible result dict
    """
    result = {}
    return doapi(objname, "GET", provider, {}, result)

