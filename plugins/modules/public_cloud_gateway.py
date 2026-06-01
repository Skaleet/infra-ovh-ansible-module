#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.synthesio.ovh.plugins.module_utils.ovh import OVH, ovh_argument_spec

__metaclass__ = type

DOCUMENTATION = '''
---
module: public_cloud_gateway
short_description: Manage OVHcloud Public Cloud gateways
description:
  - Create, update, or delete gateways in an OVHcloud public cloud project.
  - The gateway is identified by its C(name) within a C(region).
  - Supports creating a gateway on an existing subnet (C(network_id) + C(subnet_id))
    or creating a gateway together with a new private network (C(network) dict).
  - Use C(exposed=true) to attach the gateway to the public network (SNAT).
requirements:
  - python-ovh >= 0.5.0
options:
  service_name:
    description: Public cloud project ID.
    required: true
    type: str
  region:
    description: OpenStack region (e.g. C(GRA7), C(SBG5)).
    required: true
    type: str
  name:
    description: Gateway name.
    required: true
    type: str
  model:
    description:
      - Gateway sizing model.
      - Required when creating a gateway.
    required: false
    type: str
    choices: ['s', 'm', 'l', 'xl', '2xl', '3xl']
  network_id:
    description:
      - Existing OpenStack private network ID to attach the gateway to.
      - Must be used together with C(subnet_id).
      - Mutually exclusive with C(network).
    required: false
    type: str
  subnet_id:
    description:
      - Existing OpenStack subnet ID to attach the gateway to.
      - Must be used together with C(network_id).
      - Mutually exclusive with C(network).
    required: false
    type: str
  network:
    description:
      - Create a new private network together with the gateway.
      - Mutually exclusive with C(network_id)/C(subnet_id).
    required: false
    type: dict
    suboptions:
      name:
        description: Name of the private network to create.
        required: true
        type: str
      vlan_id:
        description: VLAN ID (1-4095).
        required: false
        type: int
      subnet:
        description: Subnet configuration for the new network.
        required: true
        type: dict
        suboptions:
          cidr:
            description: Subnet range in CIDR notation (e.g. C(10.0.0.0/24)).
            required: true
            type: str
          enable_dhcp:
            description: Enable DHCP on the subnet.
            required: true
            type: bool
          ip_version:
            description: IP version.
            required: false
            type: int
            default: 4
          gateway_ip:
            description: Gateway IP address within the subnet.
            required: false
            type: str
          dns_name_servers:
            description: List of DNS nameserver IPs.
            required: false
            type: list
            elements: str
  exposed:
    description:
      - Expose the gateway to the public network (enables SNAT).
      - Once exposed, a gateway cannot be un-exposed.
    required: false
    type: bool
    default: false
  state:
    description: Desired state of the gateway.
    choices: ['present', 'absent']
    default: present
    type: str
author:
  - Steven Maulny <steven.maulny@skaleet.com>
'''

EXAMPLES = r'''
- name: Create a gateway on an existing subnet
  synthesio.ovh.public_cloud_gateway:
    service_name: "{{ project_id }}"
    region: GRA7
    name: my-gateway
    model: s
    network_id: "{{ network_id }}"
    subnet_id: "{{ subnet_id }}"
    exposed: true
    state: present

- name: Create a gateway with a new private network
  synthesio.ovh.public_cloud_gateway:
    service_name: "{{ project_id }}"
    region: GRA7
    name: my-gateway
    model: s
    network:
      name: my-private-net
      vlan_id: 100
      subnet:
        cidr: "10.0.0.0/24"
        enable_dhcp: true
        ip_version: 4
        gateway_ip: "10.0.0.1"
    exposed: true
    state: present

- name: Scale up a gateway
  synthesio.ovh.public_cloud_gateway:
    service_name: "{{ project_id }}"
    region: GRA7
    name: my-gateway
    model: l
    state: present

- name: Delete a gateway
  synthesio.ovh.public_cloud_gateway:
    service_name: "{{ project_id }}"
    region: GRA7
    name: my-gateway
    state: absent
'''

RETURN = ''' # '''


def _find_gateway_by_name(client, service_name, region, name):
    """Return the gateway dict matching the given name, or None."""
    gateways = client.wrap_call(
        "GET",
        f"/cloud/project/{service_name}/region/{region}/gateway",
    )
    for gw in gateways:
        if gw.get("name") == name:
            return gw
    return None


def _build_subnet_params(subnet):
    """Convert snake_case subnet params to camelCase API fields."""
    result = dict(
        cidr=subnet["cidr"],
        enableDhcp=subnet["enable_dhcp"],
    )
    if subnet.get("ip_version") is not None:
        result["ipVersion"] = subnet["ip_version"]
    if subnet.get("gateway_ip") is not None:
        result["gatewayIp"] = subnet["gateway_ip"]
    if subnet.get("dns_name_servers") is not None:
        result["dnsNameServers"] = subnet["dns_name_servers"]
    if subnet.get("name") is not None:
        result["name"] = subnet["name"]
    return result


def _build_network_params(network):
    """Convert snake_case network params to camelCase API fields."""
    result = dict(
        name=network["name"],
        subnet=_build_subnet_params(network["subnet"]),
    )
    if network.get("vlan_id") is not None:
        result["vlanId"] = network["vlan_id"]
    return result


def run_module():
    module_args = ovh_argument_spec()
    module_args.update(dict(
        service_name=dict(required=True, type="str"),
        region=dict(required=True, type="str"),
        name=dict(required=True, type="str"),
        model=dict(
            required=False, type="str", default=None,
            choices=["s", "m", "l", "xl", "2xl", "3xl"],
        ),
        network_id=dict(required=False, type="str", default=None),
        subnet_id=dict(required=False, type="str", default=None),
        network=dict(required=False, type="dict", default=None),
        exposed=dict(required=False, type="bool", default=False),
        state=dict(choices=["present", "absent"], default="present"),
    ))

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        mutually_exclusive=[
            ("network_id", "network"),
            ("subnet_id", "network"),
        ],
        required_together=[
            ("network_id", "subnet_id"),
        ],
    )
    client = OVH(module)

    service_name = module.params["service_name"]
    region = module.params["region"]
    name = module.params["name"]
    state = module.params["state"]

    current = _find_gateway_by_name(client, service_name, region, name)

    # --- state: absent ---
    if state == "absent":
        if current is None:
            module.exit_json(changed=False, msg=f"Gateway '{name}' does not exist")

        gw_id = current["id"]
        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"Gateway '{name}' [{gw_id}] would be deleted (dry run)",
            )

        client.wrap_call(
            "DELETE",
            f"/cloud/project/{service_name}/region/{region}/gateway/{gw_id}",
        )
        module.exit_json(changed=True, msg=f"Gateway '{name}' [{gw_id}] deleted")

    # --- state: present ---

    # CREATE
    if current is None:
        if not module.params.get("model"):
            module.fail_json(msg="'model' is required when creating a gateway")

        network_id = module.params.get("network_id")
        subnet_id = module.params.get("subnet_id")
        network = module.params.get("network")

        if not network_id and not network:
            module.fail_json(
                msg="Either 'network_id'+'subnet_id' or 'network' is required when creating a gateway",
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"Gateway '{name}' would be created (dry run)",
            )

        if network_id:
            result = client.wrap_call(
                "POST",
                f"/cloud/project/{service_name}/region/{region}"
                f"/network/{network_id}/subnet/{subnet_id}/gateway",
                name=name,
                model=module.params["model"],
            )
        else:
            result = client.wrap_call(
                "POST",
                f"/cloud/project/{service_name}/region/{region}/gateway",
                name=name,
                model=module.params["model"],
                network=_build_network_params(network),
            )

        gw = _find_gateway_by_name(client, service_name, region, name)
        if gw is None:
            module.exit_json(changed=True, msg=f"Gateway '{name}' created", **result)

        if module.params.get("exposed") and gw.get("type") != "public":
            client.wrap_call(
                "POST",
                f"/cloud/project/{service_name}/region/{region}/gateway/{gw['id']}/expose",
            )
            gw = client.wrap_call(
                "GET",
                f"/cloud/project/{service_name}/region/{region}/gateway/{gw['id']}",
            )

        module.exit_json(changed=True, msg=f"Gateway '{name}' created", **gw)

    # UPDATE
    gw_id = current["id"]
    changed = False
    msgs = []

    model = module.params.get("model")
    if model is not None and model != current.get("model"):
        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"Gateway '{name}' [{gw_id}] would be updated (dry run)",
            )

        client.wrap_call(
            "PUT",
            f"/cloud/project/{service_name}/region/{region}/gateway/{gw_id}",
            name=name,
            model=model,
        )
        changed = True
        msgs.append("model updated")

    if module.params.get("exposed") and current.get("type") != "public":
        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"Gateway '{name}' [{gw_id}] would be exposed (dry run)",
            )

        client.wrap_call(
            "POST",
            f"/cloud/project/{service_name}/region/{region}/gateway/{gw_id}/expose",
        )
        changed = True
        msgs.append("exposed")

    if not changed:
        module.exit_json(
            changed=False,
            msg=f"Gateway '{name}' [{gw_id}] is already up to date",
            **current,
        )

    updated = client.wrap_call(
        "GET",
        f"/cloud/project/{service_name}/region/{region}/gateway/{gw_id}",
    )
    module.exit_json(
        changed=True,
        msg=f"Gateway '{name}' [{gw_id}] updated ({', '.join(msgs)})",
        **updated,
    )


def main():
    run_module()


if __name__ == '__main__':
    main()
