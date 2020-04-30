#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Men&Mice
# GNU General Public License v3.0 (see
# COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
# python 3 headers, required if submitting to Ansible
"""Ansible lookup plugin.

Lookup plugin for finding the next free IP address in
a network zone in the Men&Mice Suite.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
from ansible.errors import AnsibleError, AnsibleModuleError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display
from ansible.module_utils._text import to_text

ANSIBLE_METADATA = {'metadata_version': '0.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r"""
    lookup: mm_freeip
    author: Ton Kersten <t.kersten@atcomputing.nl> for Men&Mice
    version_added: "2.7"
    short_description: Find free IP address(es) in a given network range in the Men&Mice Suite
    description:
      - This lookup returns free IP address(es) in a range or ranges
        specified by the network names C(e.g. examplenet). This can be
        a string or a list
      - If multiple IP addresses are returned, the results will be returned as
        a comma-separated list.
        In such cases you may want to pass option C(wantlist=True) to the plugin,
        which will result in the record values being returned as a list
        over which you can iterate later on (or use C(query) instead)
    requirements:
      - requests (python library, https://requests.readthedocs.io)
    options:
      _terms:
        description: url, user and password
      mmurl:
        description: Men&Mice API server to connect to
        type: str
        required: True
      user:
        description: userid to login with into the API
        type: str
        required: True
      password:
        description: password to login with into the API
        type: str
        required: True
        no_log: True
      network:
        description:
          - network zone(s) from which the first free IP address is to be found.
          - This is either a single network or a list of networks
        type: str
        required: True
      multi:
        description: Get a list of x number of free IP addresses from the
          requested zones
        type: int
        required: False
        default: False
      claim:
        description: Claim the IP address(es) for the specified amount of time
        type: int
        required: False
        default: False
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
    notes:
      - TODO - Add extra filtering
"""

EXAMPLES = r"""
- name: get the first free IP address in a zone
  debug:
    msg: "This is the next free IP: {{ lookup('mm_freeip', mmurl, user, passwd, network) }}"
  vars:
    mmurl: http://mmsuite.example.net
    user: apiuser
    passwd: apipasswd
    network: examplenet

- name: get the first free IP addresses in multiple zones
  debug:
    msg: "This is the next free IP: {{ query('mm_freeip', mmurl, user, passwd, network, multi=5, claim=60) }}"
  vars:
    mmurl: http://mmsuite.example.net
    user: apiuser
    passwd: apipasswd
    network:
      - examplenet
      - examplecom

  - name: get the first free IP address in a zone and ping
    debug:
      msg: "This is the next free IP: {{ query('mm_freeip', mmurl, user, passwd, network, ping=True) }}"
    vars:
      mmurl: http://mmsuite.example.net
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

# Try to import the not standard requests module
try:
    import requests
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False

display = Display()

# The API has another concept of true and false than Python does,
# so 0 is true and 1 is false.
TRUEFALSE = {
    True: 0,
    False: 1,
}


def getrequest(sess, url, user, passwd, params={}):
    """Conduct the API call and return the result."""
    headers = {'Content-Type': 'application/json'}

    try:
        answer = sess.get(url, auth=(user, passwd),
                          headers=headers,
                          params=params)
    except requests.ConnectionError:
        raise AnsibleError("Could not connect to M&M server")

    try:
        json = answer.json()
    except ValueError:
        json = {}

    display.vvv("statuscode  = |%s|" % answer.status_code)
    display.vvv("answer_json = |%s|" % json)

    return answer.status_code, json


class LookupModule(LookupBase):
    """Extension to the base looup."""

    def run(self, terms, variables=None, **kwargs):
        """Variabele terms contains a list with supplied parameters.

        - MMURL   -> The URL to connect to (M&M top URL)
        - User    -> Userid to login with
        - Pass    -> Password to login with
        - Network -> The zone from which the free IP address(es) are found
                    Either: CIDR notation, network notation or network name
                    e.g. 192.168.63.0/24 or 192.168.63.0 or examplenet
                    Either string or list
        """
        # Is the requests module available
        if not HAVE_REQUESTS:
            raise AnsibleError("The mm_freeip lookup requires the python 'requests' library which is not installed")

        # Sufficient parameters
        if len(terms) < 4:
            raise AnsibleError("Insufficient parameters. Need at least: MMURL, User, Password and network(s).")

        # Get the parameters
        url          = terms[0].strip()
        user         = terms[1].strip()
        passwd       = terms[2].strip()
        if isinstance(terms[3], str):
            networks = [terms[3].strip()]
        else:
            networks = list(map(str.strip, terms[3]))
        multi        = kwargs.get('multi', 1)
        claim        = kwargs.get('claim', 0)
        ping         = TRUEFALSE[kwargs.get('ping', True)]
        excludedhcp  = TRUEFALSE[kwargs.get('excludedhcp', False)]
        startaddress = kwargs.get('startaddress', "")

        # Loop over all networks
        ret = []
        for network in networks:
            # Set the network filter
            params   = {'filter': network}
            rangeurl = '%s/mmws/api/Ranges' % url

            display.vvv("rangeurl    = |%s|" % rangeurl)
            display.vvv("user        = |%s|" % user)
            display.vvv("params      = |%s|" % params)

            # Check if the requested network exists (use a requests session for
            # persistent connections)
            sess = requests.Session()
            rcode, answer = getrequest(sess, rangeurl, user, passwd, params)

            # If the returncode != 200 something is wrong
            if rcode != 200:
                raise AnsibleError("An api error occured. %s", answer)

            # Some ranges found?? If the network does not exist or when there
            #  are no more IPs available an empty list is returned
            if not answer['result']['ranges']:
                return []

            # Get the range reference
            ref = answer['result']['ranges'][0]['ref']

            # Build parameter list
            params = {}
            params['temporaryClaimTime'] = claim
            params['ping']               = ping
            params['excludeDHCP']        = excludedhcp
            if startaddress:
                params['startAddress'] = startaddress
            freeipurl = '%s/mmws/api/%s/NextFreeAddress' % (url, ref)

            display.vvv("freeipurl    = |%s|" % freeipurl)
            display.vvv("params       = |%s|" % params)
            display.vvv("multi        = |%s|" % multi)
            display.vvv("claim        = |%s|" % claim)
            display.vvv("excludedhcp  = |%s|" % excludedhcp)
            display.vvv("startAddress = |%s|" % startaddress)

            # Get requested number of free IP addresses
            sess = requests.Session()
            for dummy in range(multi):
                rcode, answer = getrequest(sess, freeipurl, user, passwd, params)
                display.vvv("looprcode   = |%s|" % rcode)
                display.vvv("loopanswer  = |%s|" % answer)

                if rcode != 200:
                    raise AnsibleModuleError("Insufficient free IP addresses for '%s'" % network)

                ret.append(to_text(answer['result']['address']))

        return ret
