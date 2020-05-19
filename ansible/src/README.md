# Setup the environment to develop modules

## Software

Install Python2 and Python3, this depends on your operating
system. If you cannot find a suitable Python version for your OS,
have a look at: https://www.anaconda.com/products/individual

## Create a set of virtual environments

```
mkdir ~/venv
cd ~/venv
virtualenv -p python2 python2
virtualenv -p python3 python3
```

## Get the Ansible sources

```
git clone https://github.com/ansible/ansible.git
```

When you start coding, first ensure your environment is setup
correctly:

```
source ~/venv/python3/bin/activate && source ~/venv/ansible/hacking/env-setup
```

## Run module in terminal mode

```
python -m ansible.modules.mandm.mm_zone ~/venv/src/json/ansi_zone.json
```

With an Ansible JSON file looking like:

```
{ "ANSIBLE_MODULE_ARGS": {
    "state": "present",
    "name": "testzone",
    "nameserver": "mmsuite.example.net",
    "masters": "172.16.32.65",
    "dynamic": true,
    "servtype": "Master",
    "authority": "dns1.example.net",
    "customproperties": {
      "owner": "Ton Kersten",
      "place": "Groesbeek"
    },
    "provider" : {
        "mmurl": "http://mmsuite.example.net",
        "user": "apiuser",
        "password": "apipasswd"
    }
  }
}
```

## Route

[X] Allocate an IP address (meaning claim it/find the next free one, set
    a custom property) in an existing subnet/range
    - This is split into multiple parts
      [X] Create custom properties, for a server, zone, whatever
          `mm_props`
      [X] Find the next free IP address in a zone (lookup plugin)
          `mm_freeip`
      [X] Claim the IP address and set custom properties
          `mm_claimip`
[ ] Add/modify/delete a DNS record (A/AAAA record, but also CNAME or
    PTR. The PTR is usually maintained automatically, so you don't have
    to worry about it when you add an A or AAAA record)
    `mm_dnsrecord`

    - Get IPAM on IP address
    - Get DNSRecords ref
      if found:
        - Create DNS Record
        - Get DNS Record and change
      otherwise:
        - Get DNSZoneRef
        - Create DNS record

Not that often then:
[X] Create/delete/modify a DHCP reservation in an existing scope
    `mm_dhcp`
[x] Create/delete/modify a DNS zone
    `mm_zone`
[ ] Allocate/free up a new subnet
[ ] Then the rest of the functionality.. like create a scope and so on...


# The Module Map

## Basic

[ ] Run API commands against Men&Mice API
    [X] Generic user authentication
    [X] Handle High availability
        - TonK: If I understood correctly what David said, the HA
          functionality is created by a round-robin DNS entry.
          So, when one server is down, I just wait a little and
          give it a retry. This is what I have implemented in
          the API call, at the moment.
    [X] Handle errors reported by Men&Mice Central API

## Generic

[ ] Ansible plugin installer
[X] Inline documentation for Ansible user
[ ] General documentation for Ansible user
    - In progress
[ ] Inventory information to Ansible
[ ] Ansible Playbook
    - Currently a test playbook per module, eventually a playbook
      that does something useful.
[ ] Ansible roles for Men&Mice
[ ] Support generically available Ansible version and
    support newer than 2.7
    - TonK: Support Ansible 2.[789] with Python[23]
    - TonK: Create a Molecule test set
      (lot of work, takes long, not easy, so expensive,
       currently out of scope)

## DNS

[X] Get/Set properties for DNS and IPAM
[X] Create a DNS Resource record in Men&Mice
[X] Modify a DNS Resource record in Men&Mice
[X] Set hostname for IP address in Men&Mice

## IPAM

[X] Get next free IP address of a range

## DHCP

[X] Create/modify a DHCP reservation

## Nice to have

[ ] Create/Remove Men&Mice users/groups
[X] Create/delete a DNS zone
[ ] Create/delete IP range
[ ] Create/delete DHCP scope
[ ] Get/set properties on DHCP scopes
[ ] Create/delete DHCP options
    [ ] For a DHCP server
    [ ] For a DHCP scope
