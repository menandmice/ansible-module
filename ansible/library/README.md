# Ansible module information

https://ansible-docs.readthedocs.io/zh/stable-2.0/rst/developing_modules.html#common-pitfalls

This states that every module must be completely self contained, so code
is imported, except for standard Ansible and Python modules.

This is not handy for development, so all modules now include the
`mm_include` Python module.

Later on the `mm_include` must be injected into the separate modules
