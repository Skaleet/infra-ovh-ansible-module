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
module: public_cloud_valkey_user_present
short_description: Create a Valkey user with ACL rules
description:
  - Create a Valkey user in an OVH Public Cloud Valkey database if it does not exist.
author:
  - Synthesio SRE Team
requirements:
  - ovh >= 0.5.0
options:
  service_name:
    type: str
    required: true
    description: OVH Public Cloud project ID
  cluster_id:
    type: str
    required: true
    description: Valkey database cluster ID
  name:
    type: str
    required: true
    description: Valkey username
  categories:
    type: list
    elements: str
    default: []
  commands:
    type: list
    elements: str
    default: []
  keys:
    type: list
    elements: str
    default: []
  channels:
    type: list
    elements: str
    default: []
  state:
    type: str
    choices: [present]
    default: present
"""

RETURN = """
user:
  description: Valkey user information
  returned: success
  type: dict
"""

def run_module():
    module_args = ovh_argument_spec()
    module_args.update(
        dict(
            service_name=dict(type="str", required=True),
            cluster_id=dict(type="str", required=True),
            name=dict(type="str", required=True),
            categories=dict(type="list", elements="str", default=[]),
            commands=dict(type="list", elements="str", default=[]),
            keys=dict(type="list", elements="str", default=[]),
            channels=dict(type="list", elements="str", default=[]),
            state=dict(type="str", choices=["present"], default="present"),
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
    cluster_id = module.params["cluster_id"]
    name = module.params["name"]
    categories = module.params["categories"]
    commands = module.params["commands"]
    keys = module.params["keys"]
    channels = module.params["channels"]

    user_ids = client.wrap_call(
        "GET",
        f"/cloud/project/{service_name}/database/valkey/{cluster_id}/user"
    )

    for user_id in user_ids:
        user = client.wrap_call(
            "GET",
            f"/cloud/project/{service_name}/database/valkey/{cluster_id}/user/{user_id}"
        )
        if user.get("username") == name:
            module.exit_json(
                changed=False,
                user=user,
                msg="Valkey user already exists",
            )

    created_user = client.wrap_call(
        "POST",
        f"/cloud/project/{service_name}/database/valkey/{cluster_id}/user",
        name=name,
        categories=categories,
        commands=commands,
        keys=keys,
        channels=channels,
    )

    module.exit_json(
        changed=True,
        user=created_user,
        msg="Valkey user created",
    )

def main():
    run_module()

if __name__ == "__main__":
    main()
