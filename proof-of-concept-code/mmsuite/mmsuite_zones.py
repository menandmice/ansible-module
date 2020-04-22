#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2019, Men & Mice
# GNU General Public License v3.0 (see
# COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '0.1', 'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
--
module: mmsuite_zones
short_description: Manage DNS-Zones on a Men & Mice System
description:
  - Manage DNS Zones
'''


EXAMPLES = r'''
- name: Add a zone "example.com" to a DNS-Server
  mmsuite_zones:
    zonename: example.com
    dynamic: True
    type: master
    authority: dns1.example.net
    state: present
    provider:
      server: mm.dane.onl
      user: Administrator
      password: menandmice
  delegate_to: localhost
'''

RETURN = '''
message:
    description: The output message from the Men & Mice System
    type: str
    returned: always
'''

from ansible.module_utils.basic import *
from ansible.module_utils.urls import *
import urllib

def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        state=dict(type='str', required=True),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        full_name=dict(type='str', required=False),
        description=dict(type='str', required=False),
        email=dict(type='str', required=False),
        authentication_type=dict(type="str", required=True),
        provider=dict(type='dict', required=True, no_log=True),
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        message=''
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    provider = module.params['provider']

    print(provider)
    
    headers="{'Content-Type':'application/json'}"

    url = "http://" + provider['server'] +"/mmws/api/Users"

    state = module.params['state']
    print("State:", state)

    resp = '{}'

    # get list of all users in the system
    databody = { }

    try:
        resp = open_url(url, method="GET",
                        url_username=provider['user'],
                        url_password=provider['password'],
                        data=json.dumps(databody),
                        validate_certs=False,
                        headers={'Content-Type':'application/json'})

        res = json.loads(resp.read())
        users = res['result']['users']
        
    except urllib.error.HTTPError as err:
        print('Error while connecting to Men & Mice webservice:', err.code)
        errbody = json.loads(err.read().decode())
        result['message'] = err.msg +': ' + errbody['error']['message']
        sys.exit(err.code)
        
    user_exists = False
    user_ref = ""
    skip = False
    expect_response = True
    http_method = "GET"
    
    for user in users:
        if user['name'] == module.params['username']:
            user_exists = True
            user_ref = user['ref']
        
    if (state == "present"):
        http_method = "POST"
        if user_exists:
            url = url + "/" + user_ref
            databody = { "ref": user_ref,
                         "saveComment": "Ansible API",
                         "properties": [
                             { "name": 'name', "value": module.params['username'] }, 
                             { "name": 'password', "value": module.params['password'] },
                             { "name": 'fullName', "value": module.params['full_name'] },
                             { "name": 'authenticationType', "value": module.params['authentication_type'] }
                             ],
            }
        else:
            databody = { "user": {
                "name": module.params['username'],
                "password": module.params['password'],
                "fullName": module.params['full_name'],
                "description": module.params['description'],
                "email": module.params['email'],                
                "authenticationType": module.params['authentication_type']},
            "saveComment": "Ansible API" }
    if (state == "absent"):
        if user_exists:
            http_method = "DELETE"
            expect_response = False
            url = url + "/" + user_ref
        else:
            skip = True
            
    print("URL:", url)
    print("Method:", http_method)
    print("DATA:", databody)
    print("Skip:", skip)

    if not skip:
        try:
            resp = open_url(url, method=http_method,
                            url_username=provider['user'],
                            url_password=provider['password'],
                            data=json.dumps(databody),
                            validate_certs=False,
                            headers={'Content-Type':'application/json'})
            response = resp.read()
            if expect_response:
                result['message'] = json.loads(response)
            else:
                if resp.status == 200:
                    result['message'] = "OK"
                else:
                    result['message'] = resp.reason
            result['changed'] = True
        except urllib.error.HTTPError as err:
            print('Error', err.code)
            errbody = json.loads(err.read().decode())
            result['message'] = err.msg +': ' + errbody['error']['message']
        

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
