# Ansible mm_ipinfo plugin

This Men&Mice IPInfo lookup plugin finds a lot of info about a
specified IP address, defined in the Men&Mice suite.

## Usage

The `mm_ipinfo` plugin delivers a complete set of information about an
IP address, as it is delivered by the Men&Mice Suite API.

Example usage:

```yaml
- name: Get all info for this IP address
  debug:
    var: ipinfo
  vars:
    ipinfo: "{{ query('mm_ipinfo', provider, '172.16.17.2') | to_nice_json }}"
```

With output like (output shortened):

```bash
ok: [localhost] => {
    "ipinfo": {
        "addrRef": "IPAMRecords/11",
        "address": "172.16.17.2",
        "claimed": false,
        "customProperties": {
            "location": "At the attic"
        },
    }
}
```
