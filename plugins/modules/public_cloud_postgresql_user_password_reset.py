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
module: public_cloud_postgresql_user_password_reset
short_description: Reset the password of a PostgreSQL user on an OVH Public Cloud database
description:
  - Reset the credentials of a PostgreSQL user attached to a database cluster and
    return the new password.
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
    description: PostgreSQL database cluster ID
  user_id:
    type: str
    required: true
    description: PostgreSQL database user ID
"""

RETURN = """#"""


def run_module():
    module_args = ovh_argument_spec()
    module_args.update(
        dict(
            service_name=dict(type="str", required=True),
            cluster_id=dict(type="str", required=True),
            user_id=dict(type="str", required=True),
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
    user_id = module.params["user_id"]

    user = client.wrap_call(
        "POST",
        f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/user/{user_id}/credentials/reset"
    )

    module.exit_json(
        changed=False,
        user=user,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
