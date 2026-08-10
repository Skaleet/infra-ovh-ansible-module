#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.synthesio.ovh.plugins.module_utils.ovh import (
    OVH,
    ovh_argument_spec,
)

DOCUMENTATION = """
---
module: public_cloud_ai_token_renew
short_description: Renew an OVHcloud AI Solutions application token
description:
  - Renew an AI Solutions application token, bumping its version and returning a new token value.
  - This is a non-idempotent action and always reports C(changed=True).
author:
  - Synthesio SRE Team
requirements:
  - python-ovh >= 0.5.0
options:
  service_name:
    type: str
    required: true
    description: OVH Public Cloud project ID
  token_id:
    type: str
    required: true
    description: AI token ID (UUID)
"""

EXAMPLES = r'''
- name: Renew an AI token
  synthesio.ovh.public_cloud_ai_token_renew:
    service_name: "{{ project_id }}"
    token_id: "{{ token_id }}"
  register: renewed_token
  no_log: true
'''

RETURN = """
token:
  description: The renewed token properties, including its new value and version.
  returned: success
  type: dict
"""


def run_module():
    module_args = ovh_argument_spec()
    module_args.update(
        dict(
            service_name=dict(type="str", required=True),
            token_id=dict(type="str", required=True),
        )
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    if module.check_mode:
        module.exit_json(changed=False)

    client = OVH(module)

    service_name = module.params["service_name"]
    token_id = module.params["token_id"]

    token = client.wrap_call(
        "POST",
        f"/cloud/project/{service_name}/ai/token/{token_id}/renew",
    )

    module.exit_json(
        changed=True,
        token=token,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
