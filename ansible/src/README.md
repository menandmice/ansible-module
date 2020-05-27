# Setup the environment to develop modules

## General info

The Ansible modules (not the plugins) are developed in the `src`
directory, where there are a couple of things to consider:

- The Ansible modules *cannot* be run on their own, as they lack some
  included modules and other functionality

- As all modules use the same functions to connect to the API and so on,
  these general functions are placed in the file `include.py`
  This is to ensure all modules contain the same generic code, without
  editing a lot of files with every change to the API-call or some other
  generic function

- The script `doit` combines every `mm_*.py` file with the `header`,
  `imports` and `include.py` to a runnable module in the `library`
  directory. After _every_ edit of a module-file (`mm_*.py`) the `doit`
  script needs to be run

- To ensure you don't forget to run the `doit` script, a script called
  `trigger` is available and this runs the `doit` when a file in the
  `src` directory changes. This does need `inotify` to be installed

## Software

To develop a module some extra software is needed, e.g. Python and the
Ansible development tree.

Install Python2 and Python3, this depends on your operating system. If
you cannot find a suitable Python version for your OS, have a look at:
https://www.anaconda.com/products/individual

## Create a set of virtual environments

Note, this requires the _virtualenv_ package:

```
pip install virtualenv
```

Then:

```
mkdir ~/venv
cd ~/venv
virtualenv -p python2 python2
virtualenv -p python3 python3
```

## Get the Ansible sources

```
cd ~/venv
git clone https://github.com/ansible/ansible.git
```

This gives you the Ansible Development repository with the `devel`
branch as the default. Currently this is the Ansible 2.10 development
branch. As the complete development setup for Ansible is under heavy
revision in version 2.10 (the push forward to Ansible Collections) not
all needed modules and other bits and pieces are in the 2.10 branch.
In the development tree a branch from version 2.9 is needed.

So, issue the commands:

```
cd ansible
git checkout origin/stable-2.9
```

After this it needed to make sure all requirements for Ansible are
installed as well:

```
. ~/python2/venv/bin/activate
pip install -r requirements.txt
deactivate
. ~/python3/venv/bin/activate
pip install -r requirements.txt
deactivate
```


When you start coding, first ensure your environment is setup
correctly:

```
source ~/venv/python3/bin/activate && source ~/venv/ansible/hacking/env-setup
```

## Running the module in terminal mode

As the Men&Mice modules do not target Ansible nodes, it is possible to
test the modules from the development machine with:

```
python -m ansible.modules.mandm.mm_zone ~/venv/src/json/ansi_zone.json
```

With an Ansible JSON file that contains all @he module parameters, looking like:

```
{ "ANSIBLE_MODULE_ARGS": {
    "state": "present",
    "name": "testzone",
    "nameserver": "mmsuite.example.net",
    "masters": "172.16.17.2",
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

## Tested environments

All modules and plugins where tested on a CentOS7 and CentOS8 machine,
using Ansible 2.7, 2.8 and 2.9.

CentOS7                       CentOS8
Python 2.7.5                  Python 2.7.16
Python 3.6.8                  Python 3.6.8

## Linting

All modules and plugins have been checked with `pycodestyle` to ensure
valid code that adheres to the Python style-guide.

To install `pycodestyle` run

```
pip3 install pycodestyle
```

And create a configuration file in `~/.config/pycodestyle`, containing

```
[pycodestyle]
count = False
max-line-length = 160
statistics = True
```

The only override on the PEP8 standard is the maximum line-length.

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
[X] Add/modify/delete a DNS record (A/AAAA record, but also CNAME or
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

## Basic (67)

[X] (62) Run API commands against Men&Mice API
    [X] (63) Generic user authentication
    [X] (64) Handle High availability
        - TonK: If I understood correctly what David said, the HA
          functionality is created by a round-robin DNS entry.
          So, when one server is down, I just wait a little and
          give it a retry. This is what I have implemented in
          the API call, at the moment. This will be tested by Carsten
    [X] (65) Handle errors reported by Men&Mice Central API

## Generic (68)

[X] (42) Ansible plugin installer -> In documentation
[X] (43) Inline documentation for Ansible user
[ ] (44) General documentation for Ansible user
    - In progress
[X] (45) Inventory information to Ansible
[ ] (46) Ansible Playbook
    - In progress
    - Currently a test playbook per module, eventually a playbook
      that does something useful.
[ ] (47) Ansible roles for Men&Mice
    - Needs research by Carsten
[ ] (48) Support generically available Ansible version and
    support newer than 2.7
    - TonK: Support Ansible 2.[789] with Python[23]
    - TonK: Create a Molecule test set
      (lot of work, takes long, not easy, so expensive,
       currently out of scope)

## DNS (69)

[X] (49) Get/Set properties for DNS and IPAM
[X] (50) Create a DNS Resource record in Men&Mice
[X] (51) Modify a DNS Resource record in Men&Mice
[X] (52) Set hostname for IP address in Men&Mice

## IPAM (70)

[X] (53) Get next free IP address of a range

## DHCP (61)

[X] (61) Create/modify a DHCP reservation

## Nice to have

[ ] (54) Create/Remove Men&Mice users/groups
[X] (55) Create/delete a DNS zone
[ ] (56) Create/delete IP range
[ ] (57) Create/delete DHCP scope
[ ] (58) Get/set properties on DHCP scopes
[ ] Create/delete DHCP options
    [ ] (59) For a DHCP server
    [ ] (60) For a DHCP scope
