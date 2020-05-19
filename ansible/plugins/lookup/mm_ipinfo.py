#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Men&Mice
# GNU General Public License v3.0
# see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt
#
# python 3 headers, required if submitting to Ansible
"""Ansible lookup plugin.

Lookup plugin for finding information about an IP address
in the Men&Mice Suite.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import time
from ansible.errors import AnsibleError, AnsibleModuleError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display
from ansible.module_utils._text import to_text
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.module_utils.urls import open_url, SSLValidationError
from ansible.utils.display import Display
try:
    from ansible.utils_utils.common import json
except ImportError:
    import json

ANSIBLE_METADATA = {'metadata_version': '0.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r"""
    lookup: mm_ipinfo
    author: Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
    version_added: "2.7"
    short_description: Find information Rof an IP address
    description:
      - This lookup collects info of an IP address
    options:
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
      ipaddress:
        description:
          - The IP address that is examined
        type: str
        required: True
"""

EXAMPLES = r"""
- name: Find all info for IP 172.16.17.2
  debug:
    msg: "Info for IP: {{ lookup('mm_ipinfo', provider, '172.16.17.2') }}"
  vars:
    provider:
      mmurl: http://mmsuite.example.net
      user: apiuser
      password: apipasswd

- name: Get DHCP reservations for 172.16.17.2
  debug:
        msg: "{{ ipinfo['dhcpReservations'] }}"
  vars:
    provider:
      mmurl: http://mmsuite.example.net
      user: apiuser
      password: apipasswd
    ipinfo: "{{ query('mm_ipinfo', provider, '172.16.17.2') }}"
"""

RETURN = r"""
_list:
  description: A dict containing all results
  fields:
    0: IP address(es)
"""

display = Display()

# The API has another concept of true and false than Python does,
# so 0 is true and 1 is false.
TRUEFALSE = {
    True: 0,
    False: 1,
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

    When connection errors arise, there will be a multiple of tries,
    each a couple of seconds apart, this to handle high-availability
    """
    headers = {'Content-Type': 'application/json'}
    apiurl = "%s/mmws/api/%s" % (provider['mmurl'], url)
    result = {}

    # Maximum and current number of tries to connect to the Men&Mice API
    MAXTRIES = 5
    tries = 0

    while tries <= 4:
        tries += 1
        try:
            resp = open_url(apiurl,
                            method=method,
                            url_username=provider['user'],
                            url_password=provider['password'],
                            data=json.dumps(databody),
                            validate_certs=False,
                            headers=headers)

            # Response codes of the API are:
            #  - 200 => All OK, data returned in the body
            #  - 204 => All OK, no data returned in the body
            #  - *   => Something is wrong, error data in the body
            # But sometimes there is a situation where the response code
            # was 201 and with data in the body, so that is picked up as well

            # Get all API data and format return message
            response = resp.read()
            if resp.code == 200:
                # 200 => Data in the body
                result['message'] = json.loads(response)
            elif resp.code == 201:
                # 201 => Sometimes data in the body??
                try:
                    result['message'] = json.loads(response)
                except ValueError:
                    result['message'] = ""
            else:
                # No response from API (204 => No data)
                try:
                    result['message'] = resp.reason
                except AttributeError:
                    result['message'] = ""
            result['changed'] = True
        except HTTPError as err:
            errbody = json.loads(err.read().decode())
            result['changed'] = False
            result['warnings'] = "%s: %s (%s)" % (err.msg,
                                                  errbody['error']['message'],
                                                  errbody['error']['code']
                                                  )
        except URLError as err:
            raise AnsibleError("Failed lookup url for %s : %s" % (apiurl, to_native(err)))
        except SSLValidationError as err:
            raise AnsibleError("Error validating the server's certificate for %s: %s" % (apiurl, to_native(err)))
        except ConnectionError as err:
            if tries == MAXTRIES:
                raise AnsibleError("Error connecting to %s: %s" % (apiurl, to_native(err)))
            else:
                # There was a connection error, wait a little and retry
                time.sleep(0.25)

        if result.get('message', "") == "No Content":
            result['message'] = ""
        return result


class LookupModule(LookupBase):
    """Extension to the base looup."""

    def run(self, terms, variables=None, **kwargs):
        """Variabele terms contains a list with supplied parameters.

        - provider  -> Definition of the Men&Mice suite API provider
        - IPAddress -> The IPAddress to examine
        """
        # Is the requests module available
        # Sufficient parameters
        if len(terms) < 2:
            raise AnsibleError("Insufficient parameters. Need at least: MMURL, User, Password and IPAddress.")

        # Build the result list
        ret = []

        # Get the parameters
        provider  = terms[0]
        ipaddress = terms[1].strip()

        # Call the API to find info
        http_method = "GET"
        url = "%s/%s" % ('IPAMRecords', ipaddress)
        databody = {}
        result = doapi(url, http_method, provider, databody)

        if isinstance(result, dict):
            return result['message']['result']['ipamRecord']
        return result
