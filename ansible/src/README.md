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