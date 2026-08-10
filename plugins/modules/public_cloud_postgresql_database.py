#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.synthesio.ovh.plugins.module_utils.ovh import OVH, OVHResourceNotFound, ovh_argument_spec

__metaclass__ = type

DOCUMENTATION = '''
---
module: public_cloud_postgresql_database
short_description: Manage databases on an OVHcloud Managed PostgreSQL cluster
description:
  - Create or delete databases on an OVHcloud Managed PostgreSQL cluster.
  - The database is identified by its C(name). The name is immutable after creation,
    so there is no update operation; changing it means deleting and recreating.
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
      - Database name. Immutable after creation.
    required: true
    type: str
  state:
    description: Desired state of the database.
    choices: ['present', 'absent']
    default: present
    type: str
author:
  - Vivien Moretto <vivien.moretto@skaleet.com>
'''

EXAMPLES = r'''
- name: Create a database
  synthesio.ovh.public_cloud_postgresql_database:
    service_name: "{{ project_id }}"
    cluster_id: "{{ cluster_id }}"
    name: my_app
    state: present

- name: Delete a database
  synthesio.ovh.public_cloud_postgresql_database:
    service_name: "{{ project_id }}"
    cluster_id: "{{ cluster_id }}"
    name: my_app
    state: absent
'''

RETURN = ''' # '''


def _find_database_by_name(client, service_name, cluster_id, name):
    """Return the database dict matching the given name, or None."""
    try:
        database_ids = client.wrap_call(
            "GET",
            f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/database",
        )
    except OVHResourceNotFound:
        return None
    for database_id in database_ids:
        try:
            database = client.wrap_call(
                "GET",
                f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/database/{database_id}",
            )
        except OVHResourceNotFound:
            continue
        if database.get("name") == name:
            return database
    return None


def run_module():
    module_args = ovh_argument_spec()
    module_args.update(dict(
        service_name=dict(required=True, type="str"),
        cluster_id=dict(required=True, type="str"),
        name=dict(required=True, type="str"),
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

    current = _find_database_by_name(client, service_name, cluster_id, name)

    # --- state: absent ---
    if state == "absent":
        if current is None:
            module.exit_json(changed=False, msg=f"Database '{name}' does not exist on cluster '{cluster_id}'")

        database_id = current["id"]
        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"Database '{name}' [{database_id}] would be deleted (dry run)",
            )

        client.wrap_call(
            "DELETE",
            f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/database/{database_id}",
        )
        module.exit_json(changed=True, msg=f"Database '{name}' [{database_id}] deleted")

    # --- state: present ---

    # The database name is immutable and is the only writable field, so an
    # existing database is always already in the desired state.
    if current is not None:
        module.exit_json(
            changed=False,
            msg=f"Database '{name}' [{current['id']}] already exists on cluster '{cluster_id}'",
            **current,
        )

    # CREATE
    if module.check_mode:
        module.exit_json(
            changed=True,
            msg=f"Database '{name}' would be created on cluster '{cluster_id}' (dry run)",
        )

    result = client.wrap_call(
        "POST",
        f"/cloud/project/{service_name}/database/postgresql/{cluster_id}/database",
        name=name,
    )
    module.exit_json(changed=True, msg=f"Database '{name}' created on cluster '{cluster_id}'", **result)


def main():
    run_module()


if __name__ == '__main__':
    main()
