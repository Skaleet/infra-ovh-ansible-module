#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.synthesio.ovh.plugins.module_utils.ovh import OVH, OVHResourceNotFound, ovh_argument_spec

__metaclass__ = type

DOCUMENTATION = '''
---
module: public_cloud_postgresql_user
short_description: Manage users on an OVHcloud Managed PostgreSQL cluster
description:
  - Create, update, or delete users on an OVHcloud Managed PostgreSQL cluster.
  - The user is identified by its C(name). The username cannot be changed after creation.
  - The C(roles) field controls the roles the user belongs to.
  - The initial password is only returned in the module result on creation. Use
    M(synthesio.ovh.public_cloud_postgresql_user_password_reset) to rotate it later.
requirements:
  - python-ovh >= 0.5.0
options:
  service_name:
    description: Public cloud project ID.
    required: true
    type: str
  cluster_id:
    description: PostgreSQL cluster ID (UUID).
    required: true
    type: str
  name:
    description:
      - Username. Immutable after creation.
    required: true
    type: str
  roles:
    description:
      - List of roles the user belongs to (e.g. C(replication), or a role defined on the cluster).
    required: false
    type: list
    elements: str
  state:
    description: Desired state of the user.
    choices: ['present', 'absent']
    default: present
    type: str
author:
  - Jonathan Piron <jonathan@piron.at>
'''

EXAMPLES = r'''
- name: Create a user with the replication role
  synthesio.ovh.public_cloud_postgresql_user:
    service_name: "{{ project_id }}"
    cluster_id: "{{ cluster_id }}"
    name: replicator
    roles:
      - replication
    state: present

- name: Create a user without any specific role
  synthesio.ovh.public_cloud_postgresql_user:
    service_name: "{{ project_id }}"
    cluster_id: "{{ cluster_id }}"
    name: app-user
    state: present

- name: Update the roles of an existing user
  synthesio.ovh.public_cloud_postgresql_user:
    service_name: "{{ project_id }}"
    cluster_id: "{{ cluster_id }}"
    name: app-user
    roles:
      - replication
    state: present

- name: Delete a user
  synthesio.ovh.public_cloud_postgresql_user:
    service_name: "{{ project_id }}"
    cluster_id: "{{ cluster_id }}"
    name: replicator
    state: absent
'''

RETURN = ''' # '''


def _find_user_by_name(client, service_name, cluster_id, name):
    """Return the user dict matching the given name, or None."""
    try:
        user_ids = client.wrap_call(
            "GET",
            f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/user",
        )
    except OVHResourceNotFound:
        return None
    for user_id in user_ids:
        try:
            user = client.wrap_call(
                "GET",
                f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/user/{user_id}",
            )
        except OVHResourceNotFound:
            continue
        if user.get("username") == name:
            return user
    return None


def _build_update_params(module_params, current):
    """
    Compare desired roles against the current user state.
    Return (needs_update, put_kwargs) where put_kwargs contains only changed fields.
    """
    put_kwargs = {}
    needs_update = False

    value = module_params.get("roles")
    if value is not None:
        current_value = current.get("roles", [])
        if sorted(value) != sorted(current_value):
            needs_update = True
            put_kwargs["roles"] = value

    return needs_update, put_kwargs


def run_module():
    module_args = ovh_argument_spec()
    module_args.update(dict(
        service_name=dict(required=True, type="str"),
        cluster_id=dict(required=True, type="str"),
        name=dict(required=True, type="str"),
        roles=dict(required=False, type="list", elements="str", default=None),
        state=dict(choices=["present", "absent"], default="present"),
    ))

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )
    client = OVH(module)

    service_name = module.params["service_name"]
    cluster_id = module.params["cluster_id"]
    name = module.params["name"]
    state = module.params["state"]

    current = _find_user_by_name(client, service_name, cluster_id, name)

    # --- state: absent ---
    if state == "absent":
        if current is None:
            module.exit_json(changed=False, msg=f"User '{name}' does not exist on cluster '{cluster_id}'")

        user_id = current["id"]
        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"User '{name}' [{user_id}] would be deleted (dry run)",
            )

        client.wrap_call(
            "DELETE",
            f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/user/{user_id}",
        )
        module.exit_json(changed=True, msg=f"User '{name}' [{user_id}] deleted")

    # --- state: present ---

    # CREATE
    if current is None:
        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"User '{name}' would be created on cluster '{cluster_id}' (dry run)",
            )

        post_kwargs = dict(name=name)
        roles = module.params.get("roles")
        if roles is not None:
            post_kwargs["roles"] = roles

        result = client.wrap_call(
            "POST",
            f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/user",
            **post_kwargs,
        )
        module.exit_json(changed=True, msg=f"User '{name}' created on cluster '{cluster_id}'", **result)

    # UPDATE
    user_id = current["id"]
    needs_update, put_kwargs = _build_update_params(module.params, current)

    if not needs_update:
        module.exit_json(
            changed=False,
            msg=f"User '{name}' [{user_id}] is already up to date",
            **current,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            msg=f"User '{name}' [{user_id}] would be updated (dry run)",
        )

    client.wrap_call(
        "PUT",
        f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/user/{user_id}",
        **put_kwargs,
    )
    updated = client.wrap_call(
        "GET",
        f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/user/{user_id}",
    )
    module.exit_json(
        changed=True,
        msg=f"User '{name}' [{user_id}] updated",
        **updated,
    )


def main():
    run_module()


if __name__ == '__main__':
    main()
