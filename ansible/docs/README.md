# Ansible setup for Men&Mice Suite

With the Ansible setup for the Men&Mice suite you can manage a Men&Mice
installation through Ansible. The Ansible modules and plugins connect to
the Men&Mice Suite API and perform all needed actions.

The modules and plugins need to be installed on the Ansible control
node, often called the Ansible Master and Ansible needs to be configured
so that the modules and plugins can be found by Ansible.

## Installation

Installing the Ansible modules and plugins is a straight forward
process.  Copy the Ansible modules and plugins to a directory on the
Ansible control node, let's assume `/tmp/mandm`.

### Ansible modules

The Ansible modules now can be placed in a number of directories, depending
on your installation and requirements.

1. `/usr/share/ansible/plugins/modules/`
   System wide installation, modules available to all users
2. `~/.ansible/plugins/modules/`
   Modules available only to the current user, as the modules are
   installed in the users home-directory
3. `/etc/ansible/library/`
   Local installation. As most Ansible installations use the
   `/etc/ansible` directory as the Ansible top-directory (as this is the
   default in an Ansible installation)
   When installing the modules in this directory, the Ansible `library`
   path needs to be set in the `/etc/ansible/ansible.cfg` file, pointing
   to the module directory.

```bash
library = /etc/ansible/library
```

After installing the Ansible modules a check can be run to determine if
the modules are installed correctly, by running the command:

```bash
ansible-doc -l | grep '^mm_'
```

which should produce a list with all the Men&Mice Suite Ansible modules.

### Ansible lookup plugins

The set of Ansible modules consists of multiple sets (`lookup` and
`inventory`) and these should be installed in their own directories

The `lookup` plugins can be installed in:

1. `/usr/share/ansible/plugins/lookup`
   System wide installation, modules available to all users
2. `~/.ansible/plugins/lookup`
   Plugins available only to the current user, as the plugins are
   installed in the users home-directory
3. `/etc/ansible/plugins/lookup`
   Local installation. As most Ansible installations use the
   `/etc/ansible` directory as the Ansible top-directory (as this is the
   default in an Ansible installation)
   When installing the lookup plugins in this directory, the Ansible
   `lookup` path needs to be set in the `/etc/ansible/ansible.cfg` file,
   pointing to the lookup plugin directory.

```bash
lookup_plugins = /usr/share/ansible/plugins/lookup:/etc/ansible/plugins/lookup
```

To check if the modules are installed correctly and are available to
Ansible, issue the command:

```bash
ansible-doc -t lookup -l
```

Which should produce a list with all the Men&Mice Suite Ansible lookup
plugins.

### Ansible inventory plugins

The set of Ansible modules consists of multiple sets (`lookup` and
`inventory`) and these should be installed in their own directories

The `inventory` plugins can be installed in:

1. `/usr/share/ansible/plugins/inventory`
   System wide installation, modules available to all users
2. `~/.ansible/plugins/inventory`
   Plugins available only to the current user, as the plugins are
   installed in the users home-directory
3. `/etc/ansible/plugins/inventory`
   Local installation. As most Ansible installations use the
   `/etc/ansible` directory as the Ansible top-directory (as this is the
   default in an Ansible installation)
   When installing the inventory plugins in this directory, the Ansible
   `lookup` path needs to be set in the `/etc/ansible/ansible.cfg` file,
   pointing to the lookup plugin directory.

```bash
inventory_plugins = /usr/share/ansible/plugins/inventory:/etc/ansible/plugins/inventory
```

To check if the modules are installed correctly and are available to
Ansible, issue the command:

```bash
ansible-doc -t inventory -l
```

which should produce a list with all the Men&Mice Suite Ansible
inventory plugins.

## API user

As the Ansible modules and plugins connect to a Men&Mice Suite
installation, a connection between Ansible and the Men&Mice Suite needs
to be made.

### API user for Men&Mice Suite

In the Men&Mice Suite a user needs to be defined that has all rights in
the Men&Mice Suite (`administrator`) so it is able to perform all needed
tasks.

### API Provider in Ansible

For the Ansible modules and plugins to function correctly a _provider_
has to be defined. This provider consist of a `user`, `password` and
connection url (`mmurl`) and this provider needs to be defined in the
Ansible setup, either through Ansible Tower/AWX or in the Ansible
directory.

As the modules and plugins can be used by for all systems under Ansible
control, it is advised to define the API provider for the `all` group.
Create a file `all` in the `/etc/ansible/group_vars` directory, or the
`/etc/ansible/inventory/group_vars` directory (if your inventory is
a directory instead of a file) which contains:

```yaml
---
provider:
  mmurl: http://mmsuite.example.net
  user: apiuser
  password: apipasswd
```

Where the `apipasswd` should be encrypted with `ansible-vault` to
prevent plain passwords in the Ansible tree. An example to achieve this

```bash
printf "apipasswd"             | \
    ansible-vault              \
        encrypt_string         \
        --stdin-name="password"
```

Which results in:

```bash
password: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  34646538383265336162666535313938333861323465333661376436656637643434316266666430
  6139656636383537336365313165663861383165616632330a333230356662336161393439666431
  35393130656565313138383565626137353639316239393735306663376362613861623135656634
  6332393063643531390a343661373263656132363737326666396132373461323631613034356565
  6138
```

The defined provider can be used in Ansible playlooks like:

```yaml
- name: Claim IP address
  mm_claimip:
    state: present
    ipaddress: 172.16.12.14
    provider: "{{ provider }"
  delegate_to: localhost
```

The reason for the `delegate_to: localhost` option, is that all commands
can be performed on the Ansible control node. So, it is possible to
protect the Men&Mice Suite API to only accept commands from the Ansible
control node and not from everywhere.
