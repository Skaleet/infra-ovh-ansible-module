#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.synthesio.ovh.plugins.module_utils.ovh import OVH, ovh_argument_spec

__metaclass__ = type

DOCUMENTATION = '''
---
module: public_cloud_ai_token_info
short_description: Get details of OVHcloud AI Solutions application tokens
description:
  - When C(token_id) is provided, fetch the properties of that single token.
  - When C(name) is provided, find the token by name and return its properties.
  - When neither is provided, fetch the properties of all tokens in the project.
  - C(token_id) and C(name) are mutually exclusive.
requirements:
  - python-ovh >= 0.5.0
options:
  service_name:
    description: Public cloud project ID.
    required: true
    type: str
  token_id:
    description: AI token ID (UUID). Mutually exclusive with C(name).
    required: false
    type: str
  name:
    description: AI token name. Mutually exclusive with C(token_id).
    required: false
    type: str
author:
  - Synthesio SRE Team
'''

EXAMPLES = r'''
- name: Get a single AI token by ID
  synthesio.ovh.public_cloud_ai_token_info:
    service_name: "{{ project_id }}"
    token_id: "{{ token_id }}"
  register: token_info

- name: Get a single AI token by name
  synthesio.ovh.public_cloud_ai_token_info:
    service_name: "{{ project_id }}"
    name: my-ai-token
  register: token_info

- name: Get all AI tokens
  synthesio.ovh.public_cloud_ai_token_info:
    service_name: "{{ project_id }}"
  register: all_tokens
'''

RETURN = '''
token:
  description: Token properties. Returned when C(token_id) or C(name) is provided.
  returned: success, when token_id or name is provided
  type: dict
tokens:
  description: List of token properties. Returned when neither C(token_id) nor C(name) is provided.
  returned: success, when neither token_id nor name is provided
  type: list
  elements: dict
'''


def run_module():
    module_args = ovh_argument_spec()
    module_args.update(dict(
        service_name=dict(required=True, type="str"),
        token_id=dict(required=False, type="str", default=None),
        name=dict(required=False, type="str", default=None),
    ))

    module = AnsibleModule(
        argument_spec=module_args,
        mutually_exclusive=[("token_id", "name")],
        supports_check_mode=True,
    )
    client = OVH(module)

    service_name = module.params["service_name"]
    token_id = module.params["token_id"]
    name = module.params["name"]

    if token_id:
        token = client.wrap_call(
            "GET",
            f"/cloud/project/{service_name}/ai/token/{token_id}",
        )
        module.exit_json(changed=False, token=token)
        return

    tokens = client.wrap_call(
        "GET",
        f"/cloud/project/{service_name}/ai/token",
    )

    if name:
        for token in tokens:
            if token.get("spec", {}).get("name") == name:
                module.exit_json(changed=False, token=token)
                return
        module.fail_json(msg=f"No AI token found with name '{name}'")

    module.exit_json(changed=False, tokens=tokens)


def main():
    run_module()


if __name__ == '__main__':
    main()
