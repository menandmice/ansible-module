# Ansible mm_freeip plugin

This Men&Mice FreeIP lookup plugin finds one or more free IP addresses
in a certain network, defined in the Men&Mice suite.

## Installation

### Requirements

The Men&Mice FreeIP plugin needs Ansible to work with Ansible version
2.7 as the minimum. Either Python version 2 and Python version 3 will
do.

Of course the Men&Mice Suite is required with an API user with password
that has full rights in the Men&Mice Suite!

### Plugin installation

In the `ansible` top directory create a directory `plugins/lookups` and
place the file `mm_freeip.py` in this directory.

Now point Ansible to this directory so ansible can find the plugin.  In
the `ansible.cfg` set the `lookup_plugins` to search this directory as
well.

```
lookup_plugins = /usr/share/ansible_plugins/lookup_plugins:/etc/ansible/plugins/lookup
```

Of course it is possible to place the plugin in one of the standard
Ansible plugin directories (`${HOME}/.ansible/plugins/lookup` or
`/usr/share/ansible/plugins/lookup`)

An easy way to see if the plugin is installed correctly is:

```
ansible-doc -t lookup mm_freeip
```

## Usage

When using the Men&Mice FreeIP plugin something needs to be taken into
account.  When running an Ansible lookup plugin, this lookup action
takes place every time the variable is referenced. So it will not be
possible to claim an IP address for further reference, this way. This
has to do with the way Ansible works.  A solution for this is to assign
all collected IP addresses to an Ansible fact, but here you need to make
sure the factname is not used over multiple hosts.

Example usage:

```
---
- name: Men&Mice FreeIP test play
  hosts: localhost
  connection: local
  become: false

  vars:
    provider:
      mmurl: http://mandm.example.net
      user: apiuser
      password: apipassword
    network: examplenet

  tasks:
    - name: Set free IP addresses as a fact
      set_fact:
        freeips: "{{ query('mm_freeip',
                           provider,
                           network,
                           multi=15,
                           claim=60,
                           startaddress='192.168.63.100',
                           excludedhcp=True,
                           ping=True)
                 }}"

    - name: Get the free IP address and show info
      debug:
        msg:
          - "Free IPs          : {{ freeips }}"
          - "Queried network   : {{ network }}"
          - "Ansible version   : {{ ansible_version.full }}"
          - "Python version    : {{ ansible_facts['python_version'] }}"
          - "Python executable : {{ ansible_facts['python']['executable'] }}"

    - name: Loop over IP addresses
      debug:
        msg:
          - "Next free IP      : {{ item }}"
      loop: "{{ freeips }}"
```



```
# ansible-playbook mmtest.yml

PLAY [Men&Mice FreeIP test play] *************************************

TASK [Gathering Facts] ***********************************************
ok: [localhost]

TASK [Set free IP addresses as a fact] *******************************
ok: [localhost]

TASK [Get the free IP address and show info] *************************
ok: [localhost] => {
    "msg": [
        "Free IPs          : ['192.168.63.203', '192.168.63.204']",
        "Queried network   : nononet",
        "Ansible version   : 2.9.7",
        "Python version    : 3.6.8",
        "Python executable : /usr/libexec/platform-python"
    ]
}

TASK [Loop over IP addresses] ****************************************
ok: [localhost] => (item=192.168.63.203) => {
    "msg": [
        "Next free IP      : 192.168.63.203"
    ]
}
ok: [localhost] => (item=192.168.63.204) => {
    "msg": [
        "Next free IP      : 192.168.63.204"
    ]
}

PLAY RECAP ***********************************************************
localhost : ok=4  changed=0  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0
```
