#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Men&Mice
# GNU General Public License v3.0
# see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt
#
# python 3 headers, required if submitting to Ansible
"""Ansible lookup plugin.

Lookup plugin for finding the next free IP address in
a network zone in Micetro.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import time
from ansible.errors import AnsibleError, AnsibleModuleError
from ansible.plugins.lookup import LookupBase
from ansible.utils import unicode
from ansible.utils.display import Display
from ansible.module_utils._text import to_text, to_native
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.module_utils.urls import open_url, SSLValidationError
try:
    from ansible.utils_utils.common import json
except ImportError:
    import json

ANSIBLE_METADATA = {'metadata_version': '0.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r"""
    lookup: mm_freeip
    author: Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
    version_added: "2.7"
    short_description: Find free IP address(es) in a given network range in Micetro
    description:
      - This lookup returns free IP address(es) in a range or ranges
        specified by the network names C(e.g. examplenet). This can be
        a string or a list
      - If multiple IP addresses are returned, the results will be returned as
        a comma-separated list.
        In such cases you may want to pass option C(wantlist=True) to the plugin,
        which will result in the record values being returned as a list
        over which you can iterate later on (or use C(query) instead)
    options:
      provider:
        description: Definition of the Micetro API provider
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
      network:
        description:
          - network zone(s) from which the first free IP address is to be found.
          - This is either a single network or a list of networks
        type: list
        required: True
      multi:
        description: Get a list of x number of free IP addresses from the
          requested zones
        type: int
        required: False
        default: False
      claim:
        description: Claim the IP address(es) for the specified amount of time in seconds
        type: int
        required: False
      ping:
        description: ping the address found before returning
        type: bool
        required: False
        default: False
      excludedhcp:
        description: exclude DHCP reserved ranges from result
        type: bool
        required: False
        default: False
      startaddress:
        description:
          - Start address when looking for the next free address
          - When the start address is not in de zone it will be ignored
        type: str
        required: False
        default: None
      filter:
        description:
          - Micetro filter statement
          - Filter validation is done by Micetro, not in the plugin
          - More filter info on https://docs.menandmice.com/en/latest/guides/user-manual/webapp_quick_filter/
        type: str
        required: False
        default: None
"""

EXAMPLES = r"""
- name: get the first free IP address in a zone
  debug:
    msg: "This is the next free IP: {{ lookup('mm_freeip', provider, network) }}"
  vars:
    provider:
      mmurl: http://micetro.example.net
      user: apiuser
      password: apipasswd
    network: examplenet

- name: get the first free IP addresses in multiple zones
  debug:
    msg: "This is the next free IP: {{ query('mm_freeip', provider, network, multi=5, claim=60) }}"
  vars:
    mmurl: http://micetro.example.net
    user: apiuser
    passwd: apipasswd
    network:
      - examplenet
      - examplecom

  - name: get the first free IP address in a zone and ping
    debug:
      msg: "This is the next free IP: {{ query('mm_freeip', provider, network, ping=True) }}"
    vars:
      mmurl: http://micetro.example.net
      user: apiuser
      passwd: apipasswd
      network: examplenet
"""

RETURN = r"""
_list:
  description: A list containing the free IP address(es) in the network range
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
                            force_basic_auth=True,
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
                # Sometimes (older Python) the data is not a string but a
                # byte array.
                if isinstance(response, bytes):
                    response = response.decode('utf8')
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

        - provider -> Definition of the Micetro API provider
        - Network  -> The zone from which the free IP address(es) are found
                      Either: CIDR notation, network notation or network name
                      e.g. 172.16.17.0/24 or 172.16.17.0 or examplenet
                      Either string or list
        """
        # Sufficient parameters
        if len(terms) < 2:
            raise AnsibleError("Insufficient parameters. Need at least: provider and network(s).")

        # Get the parameters
        provider = terms[0]
        if isinstance(terms[1], str):
            networks = [str(terms[1]).strip()]
        else:
            # First make sure all elements are string (Sometimes it's
            # AnsibleUnicode, depending on Ansible and Python version)
            terms[1] = list(map(str, terms[1]))
            networks = list(map(str.strip, terms[1]))
        multi = kwargs.get('multi', 1)
        claim = kwargs.get('claim', 0)
        ping = TRUEFALSE[kwargs.get('ping', True)]
        excludedhcp = TRUEFALSE[kwargs.get('excludedhcp', False)]
        startaddress = kwargs.get('startaddress', "")
        ipfilter = kwargs.get('filter', "")

        # Loop over all networks
        ret = []
        for network in networks:
            # Get the requested network ranges
            http_method = "GET"
            url = "Ranges"
            databody = {'filter': network}
            result = doapi(url, http_method, provider, databody)

            # Some ranges found? If the network does not exist or when there
            # are no more IPs available an empty list is returned
            if result.get('message').get('result').get('totalResults', 1) == 0:
                return []

            # Get the range reference
            ref = result['message']['result']['ranges'][0]['ref']

            # Build parameter list
            databody = {}
            databody['temporaryClaimTime'] = claim
            databody['ping'] = ping
            databody['excludeDHCP'] = excludedhcp
            if startaddress:
                databody['startAddress'] = startaddress
            url = '%s/NextFreeAddress' % ref

            # Collect the options
            options = ""
            if claim:
                options += "temporaryClaimTime=%d" % claim

            # Was a filter specified?
            if ipfilter:
                if options:
                    options += '&'
                options += 'filter=%s' % ipfilter

            # Exclude DHCP ranges
            if excludedhcp:
                if options:
                    options += '&'
                options += 'excludeDHCP=%s' % excludedhcp

            # Ping?
            if ping:
                if options:
                    options += '&'
                options += 'ping=%s' % ping

            # Start address?
            if startaddress:
                if options:
                    options += '&'
                options += 'startAddress=%s' % startaddress

            # Construct the url
            if options:
                url += "?%s" % options

            # Get requested number of free IP addresses
            for dummy in range(multi):
                result = doapi(url, http_method, provider, databody)
                display.vvv("loopanswer  = |%s|" % result)

                # If there are no more free IP Addresses, the API returns
                # an empty result.
                if result['message'] == '':
                    raise AnsibleModuleError("Insufficient free IP addresses for '%s'" % network)

                # Keep what was found
                ret.append(to_text(result['message']['result']['address']))

        # Return the result
        return ret
