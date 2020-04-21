# python 3 headers, required if submitting to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
        lookup: mmfreeip
        author: Ton Kersten <t.kersten@atcomputing.nl>
        version_added: "2.7"
        short_description: Get the first free IP address in a zone
        description:
            - This lookup returns the first free IP address in a zone
        options:
          _terms:
            host: Men&Mice API server to connect to
            required: True
            user: userid to login
            required: True
            password: password to login with
            required: True
            zone: The zone the first IP address is requested from
            required: True
        notes:
          - if read in variable context, the file can be interpreted as YAML if the content is valid to the parser.
          - TODO: Add extra filtering
"""
from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display

display = Display()


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        # lookups in general are expected to both take a list as input and output a list
        # this is done so they work with the looping construct 'with_'.
        ret = []
        for term in terms:
            display.debug("Term : |%s|" % term)

            # Find the file in the expected search path, using a class method
            # that implements the 'expected' search path for Ansible plugins.
            url = self.find_file_in_search_path(variables, 'files', term)

        return ret
