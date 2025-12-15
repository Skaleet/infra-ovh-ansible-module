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
module: public_cloud_valkey_user_info
short_description: Retrieve Valkey users from an OVH Public Cloud database
description:
  - Retrieve the list of Valkey user IDs attached to a database cluster.
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
"""

RETURN = """
users:
  description: List of Valkey user IDs
  returned: success
  type: list
  elements: str
"""

def run_module():
    module_args = ovh_argument_spec()
    module_args.update(
        dict(
            service_name=dict(type="str", required=True),
            cluster_id=dict(type="str", required=True),
        )
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    client = OVH(module)

    service_name = module.params["service_name"]
    cluster_id = module.params["cluster_id"]

    users = client.wrap_call(
        "GET",
        f"/cloud/project/{service_name}/database/valkey/{cluster_id}/user"
    )

    module.exit_json(
        changed=False,
        users=users,
    )

def main():
    run_module()

if __name__ == "__main__":
    main()
