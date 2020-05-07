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
        result['warnings'] = "%s: %s (%s)" % (
            err.msg,
            errbody['error']['message'],
            errbody['error']['code']
            )
    except URLError as err:
        raise AnsibleError("Failed lookup url for %s : %s" % (apiurl, to_native(err)))
    except SSLValidationError as err:
        raise AnsibleError("Error validating the server's certificate for %s: %s" % (apiurl, to_native(err)))
    except ConnectionError as err:
        raise AnsibleError("Error connecting to %s: %s" % (apiurl, to_native(err)))

    if result.get('message', "") == "No Content":
        result['message'] = ""
    return result


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


def get_single_refs(objname, provider):
    """Get all information about a single object.

    Parameters
        - objname  -> Object name to get all refs for (IPAMRecords/172.16.17.201)
        - provider -> Needed credentials for the API provider

    Returns:
        - The response from the API call
        - The Ansible result dict
    """
    resp = doapi(objname, "GET", provider, {})
    if resp.get('message'):
        return resp['message']['result']

    if resp.get('warnings'):
        resp['invalid'] = True
        return resp

    return "Unknow error"


def get_dhcp_scopes(provider, ipaddress):
    """Given an IP Address, find the DHCP scopes."""
    url = "Ranges?filter=%s" % ipaddress

    # Get the information of this IP range.
    # I'm not sure if an IP address can be part of multiple DHCP
    # scopes, but in the API it's defined as a list, so find them all.
    resp = doapi(url, 'GET', provider, {})

    # Gather all DHCP scopes for this IP address
    scopes = []
    if resp:
        for dhcpranges in resp['message']['result']['ranges']:
            for scope in dhcpranges['dhcpScopes']:
                scopes.append(scope['ref'])

    # Return all scopes
    return scopes
