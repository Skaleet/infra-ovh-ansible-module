#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.synthesio.ovh.plugins.module_utils.ovh import OVH, OVHResourceNotFound, ovh_argument_spec

__metaclass__ = type

DOCUMENTATION = '''
---
module: public_cloud_ai_token
short_description: Manage OVHcloud AI Solutions application tokens
description:
  - Create or delete AI Solutions application tokens in an OVHcloud Public Cloud project.
  - The token is identified by its C(name).
  - The token spec (C(region), C(role), C(label_selector)) is immutable after creation;
    the API exposes no update operation.
requirements:
  - python-ovh >= 0.5.0
options:
  service_name:
    description: Public cloud project ID.
    required: true
    type: str
  name:
    description:
      - Application token name. Used to identify the token idempotently.
    required: true
    type: str
  region:
    description:
      - Public Cloud storage region (e.g. C(GRA)).
      - Required when creating a token.
      - Immutable after creation.
    required: false
    type: str
  role:
    description:
      - Role granted by this application token.
      - Required when creating a token.
      - Immutable after creation.
    required: false
    type: str
    choices:
      - ai_training_operator
      - ai_training_read
      - quantum_operator
      - quantum_reader
  label_selector:
    description:
      - Application token label selector.
      - Immutable after creation.
    required: false
    type: str
  state:
    description: Desired state of the token.
    choices: ['present', 'absent']
    default: present
    type: str
author:
  - Synthesio SRE Team
'''

EXAMPLES = r'''
- name: Create an AI token with read access
  synthesio.ovh.public_cloud_ai_token:
    service_name: "{{ project_id }}"
    name: my-ai-token
    region: GRA
    role: ai_training_read
    state: present
  register: ai_token
  no_log: true

- name: Create an AI token restricted by label selector
  synthesio.ovh.public_cloud_ai_token:
    service_name: "{{ project_id }}"
    name: my-scoped-token
    region: GRA
    role: ai_training_operator
    label_selector: "env=prod"
    state: present

- name: Delete an AI token
  synthesio.ovh.public_cloud_ai_token:
    service_name: "{{ project_id }}"
    name: my-ai-token
    state: absent
'''

RETURN = ''' # '''


def _find_token_by_name(client, service_name, name):
    """Return the token dict matching the given name, or None.

    The list endpoint returns full token objects, so no per-token GET is needed.
    """
    try:
        tokens = client.wrap_call("GET", f"/cloud/project/{service_name}/ai/token")
    except OVHResourceNotFound:
        return None
    for token in tokens:
        if token.get("spec", {}).get("name") == name:
            return token
    return None


def run_module():
    module_args = ovh_argument_spec()
    module_args.update(dict(
        service_name=dict(required=True, type="str"),
        name=dict(required=True, type="str"),
        region=dict(required=False, type="str", default=None),
        role=dict(
            required=False,
            type="str",
            default=None,
            choices=[
                "ai_training_operator",
                "ai_training_read",
                "quantum_operator",
                "quantum_reader",
            ],
        ),
        label_selector=dict(required=False, type="str", default=None),
        state=dict(choices=["present", "absent"], default="present"),
    ))

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )
    client = OVH(module)

    service_name = module.params["service_name"]
    name = module.params["name"]
    state = module.params["state"]

    current = _find_token_by_name(client, service_name, name)

    # --- state: absent ---
    if state == "absent":
        if current is None:
            module.exit_json(changed=False, msg=f"AI token '{name}' does not exist")

        token_id = current["id"]
        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"AI token '{name}' [{token_id}] would be deleted (dry run)",
            )

        client.wrap_call(
            "DELETE",
            f"/cloud/project/{service_name}/ai/token/{token_id}",
        )
        module.exit_json(changed=True, msg=f"AI token '{name}' [{token_id}] deleted")

    # --- state: present ---

    # CREATE
    if current is None:
        if not module.params.get("region"):
            module.fail_json(msg="'region' is required when creating an AI token")
        if not module.params.get("role"):
            module.fail_json(msg="'role' is required when creating an AI token")

        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"AI token '{name}' would be created (dry run)",
            )

        post_kwargs = dict(
            name=name,
            region=module.params["region"],
            role=module.params["role"],
        )
        if module.params.get("label_selector") is not None:
            post_kwargs["labelSelector"] = module.params["label_selector"]

        result = client.wrap_call(
            "POST",
            f"/cloud/project/{service_name}/ai/token",
            **post_kwargs,
        )
        module.exit_json(changed=True, msg=f"AI token '{name}' created", **result)

    # EXISTS — the spec is immutable, so any supplied change is an error
    token_id = current["id"]
    spec = current.get("spec", {})
    immutable_checks = [
        ("region", "region"),
        ("role", "role"),
        ("label_selector", "labelSelector"),
    ]
    for param, api_field in immutable_checks:
        value = module.params.get(param)
        if value is not None and spec.get(api_field) != value:
            module.fail_json(
                msg=f"Cannot change '{param}' for existing AI token '{name}' (immutable after creation)"
            )

    module.exit_json(
        changed=False,
        msg=f"AI token '{name}' [{token_id}] already exists",
        **current,
    )


def main():
    run_module()


if __name__ == '__main__':
    main()
