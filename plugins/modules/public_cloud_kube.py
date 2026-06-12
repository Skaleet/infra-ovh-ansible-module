#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.synthesio.ovh.plugins.module_utils.ovh import OVH, ovh_argument_spec

__metaclass__ = type

DOCUMENTATION = '''
---
module: public_cloud_kube
short_description: Manage OVHcloud Managed Kubernetes clusters
description:
  - Create, update, or delete Managed Kubernetes clusters in an OVHcloud public cloud project.
  - The cluster is identified by its C(name).
  - Only C(update_policy) can be changed after creation; all other fields are immutable.
requirements:
  - python-ovh >= 0.5.0
options:
  service_name:
    description: Public cloud project ID.
    required: true
    type: str
  name:
    description: Kubernetes cluster name.
    required: true
    type: str
  region:
    description:
      - OpenStack region where the cluster will be deployed (e.g. C(GRA7), C(SBG5)).
      - Required when creating a cluster.
      - Immutable after creation.
    required: false
    type: str
  version:
    description:
      - Kubernetes version to install (e.g. C(1.31), C(1.32)).
      - When omitted, OVHcloud selects the latest stable version.
      - Immutable after creation (use the OVH API upgrade endpoint to upgrade).
    required: false
    type: str
  update_policy:
    description: Cluster update policy.
    required: false
    type: str
    choices: ['ALWAYS_UPDATE', 'MINIMAL_DOWNTIME', 'NEVER_UPDATE']
  kube_proxy_mode:
    description:
      - Mode for kube-proxy.
      - Immutable after creation.
    required: false
    type: str
    choices: ['iptables', 'ipvs']
  private_network_id:
    description:
      - OpenStack private network ID that the cluster will use.
      - When omitted, the cluster uses the public network.
      - Immutable after creation.
    required: false
    type: str
  private_network_configuration:
    description:
      - Private network routing configuration.
      - Only applicable when C(private_network_id) is set.
      - Immutable after creation.
    required: false
    type: dict
    suboptions:
      default_vrack_gateway:
        description:
          - IP address in the private network to route all egress traffic through.
          - Empty string means disabled.
        type: str
      private_network_routing_as_default:
        description: Use the private interface as default route instead of the public one.
        type: bool
  nodes_subnet_id:
    description:
      - OpenStack subnet ID that cluster nodes will use.
      - Can only be set when C(private_network_id) is also set.
      - Immutable after creation.
    required: false
    type: str
  load_balancers_subnet_id:
    description:
      - OpenStack subnet ID that load balancers will use.
      - Can only be set when both C(private_network_id) and C(nodes_subnet_id) are set.
      - Immutable after creation.
    required: false
    type: str
  customization:
    description:
      - Cluster customization (API server admission plugins, kube-proxy tuning, Cilium settings).
      - Immutable after creation.
    required: false
    type: dict
  ip_allocation_policy:
    description:
      - Custom CIDR ranges for pods and services.
      - Immutable after creation.
    required: false
    type: dict
    suboptions:
      pods_ipv4_cidr:
        description: CIDR used for pods IP allocation.
        type: str
      services_ipv4_cidr:
        description: CIDR used for services IP allocation.
        type: str
  plan:
    description:
      - Cluster plan.
      - Immutable after creation.
    required: false
    type: str
  state:
    description: Desired state of the cluster.
    choices: ['present', 'absent']
    default: present
    type: str
author:
  - Steven Maulny <steven.maulny@skaleet.com>
'''

EXAMPLES = r'''
- name: Create a basic Kubernetes cluster
  synthesio.ovh.public_cloud_kube:
    service_name: "{{ project_id }}"
    name: my-cluster
    region: GRA7
    version: "1.32"
    state: present

- name: Create a cluster with private networking
  synthesio.ovh.public_cloud_kube:
    service_name: "{{ project_id }}"
    name: private-cluster
    region: GRA7
    version: "1.32"
    private_network_id: "{{ network_id }}"
    nodes_subnet_id: "{{ subnet_id }}"
    load_balancers_subnet_id: "{{ lb_subnet_id }}"
    private_network_configuration:
      default_vrack_gateway: "10.0.0.1"
      private_network_routing_as_default: true
    state: present

- name: Create a cluster with custom IP allocation
  synthesio.ovh.public_cloud_kube:
    service_name: "{{ project_id }}"
    name: custom-cluster
    region: SBG5
    kube_proxy_mode: ipvs
    update_policy: MINIMAL_DOWNTIME
    ip_allocation_policy:
      pods_ipv4_cidr: "10.244.0.0/16"
      services_ipv4_cidr: "10.96.0.0/16"
    state: present

- name: Update the cluster update policy
  synthesio.ovh.public_cloud_kube:
    service_name: "{{ project_id }}"
    name: my-cluster
    update_policy: NEVER_UPDATE
    state: present

- name: Delete a cluster
  synthesio.ovh.public_cloud_kube:
    service_name: "{{ project_id }}"
    name: my-cluster
    state: absent
'''

RETURN = ''' # '''


def _find_cluster_by_name(client, service_name, name):
    """Return the cluster dict matching the given name, or None."""
    kube_ids = client.wrap_call(
        "GET",
        f"/cloud/project/{service_name}/kube",
    )
    for kube_id in kube_ids:
        cluster = client.wrap_call(
            "GET",
            f"/cloud/project/{service_name}/kube/{kube_id}",
        )
        if cluster.get("name") == name:
            return cluster
    return None


def _build_private_network_configuration(params):
    """Convert snake_case module params to camelCase API fields."""
    if params is None:
        return None
    result = {}
    if params.get("default_vrack_gateway") is not None:
        result["defaultVrackGateway"] = params["default_vrack_gateway"]
    if params.get("private_network_routing_as_default") is not None:
        result["privateNetworkRoutingAsDefault"] = params["private_network_routing_as_default"]
    return result or None


def _build_ip_allocation_policy(params):
    """Convert snake_case module params to camelCase API fields."""
    if params is None:
        return None
    result = {}
    if params.get("pods_ipv4_cidr") is not None:
        result["podsIpv4Cidr"] = params["pods_ipv4_cidr"]
    if params.get("services_ipv4_cidr") is not None:
        result["servicesIpv4Cidr"] = params["services_ipv4_cidr"]
    return result or None


def run_module():
    module_args = ovh_argument_spec()
    module_args.update(dict(
        service_name=dict(required=True, type="str"),
        name=dict(required=True, type="str"),
        region=dict(required=False, type="str", default=None),
        version=dict(required=False, type="str", default=None),
        update_policy=dict(
            required=False, type="str", default=None,
            choices=["ALWAYS_UPDATE", "MINIMAL_DOWNTIME", "NEVER_UPDATE"],
        ),
        kube_proxy_mode=dict(
            required=False, type="str", default=None,
            choices=["iptables", "ipvs"],
        ),
        private_network_id=dict(required=False, type="str", default=None),
        private_network_configuration=dict(required=False, type="dict", default=None),
        nodes_subnet_id=dict(required=False, type="str", default=None),
        load_balancers_subnet_id=dict(required=False, type="str", default=None),
        customization=dict(required=False, type="dict", default=None),
        ip_allocation_policy=dict(required=False, type="dict", default=None),
        plan=dict(required=False, type="str", default=None),
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

    current = _find_cluster_by_name(client, service_name, name)

    # --- state: absent ---
    if state == "absent":
        if current is None:
            module.exit_json(changed=False, msg=f"Cluster '{name}' does not exist")

        kube_id = current["id"]
        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"Cluster '{name}' [{kube_id}] would be deleted (dry run)",
            )

        client.wrap_call(
            "DELETE",
            f"/cloud/project/{service_name}/kube/{kube_id}",
        )
        module.exit_json(changed=True, msg=f"Cluster '{name}' [{kube_id}] deleted")

    # --- state: present ---

    # CREATE
    if current is None:
        if not module.params.get("region"):
            module.fail_json(msg="'region' is required when creating a cluster")

        if module.check_mode:
            module.exit_json(
                changed=True,
                msg=f"Cluster '{name}' would be created (dry run)",
            )

        post_kwargs = dict(
            name=name,
            region=module.params["region"],
        )
        for param, api_field in [
            ("version", "version"),
            ("update_policy", "updatePolicy"),
            ("kube_proxy_mode", "kubeProxyMode"),
            ("private_network_id", "privateNetworkId"),
            ("nodes_subnet_id", "nodesSubnetId"),
            ("load_balancers_subnet_id", "loadBalancersSubnetId"),
            ("customization", "customization"),
            ("plan", "plan"),
        ]:
            value = module.params.get(param)
            if value is not None:
                post_kwargs[api_field] = value

        pnc = _build_private_network_configuration(
            module.params.get("private_network_configuration"),
        )
        if pnc is not None:
            post_kwargs["privateNetworkConfiguration"] = pnc

        iap = _build_ip_allocation_policy(
            module.params.get("ip_allocation_policy"),
        )
        if iap is not None:
            post_kwargs["ipAllocationPolicy"] = iap

        result = client.wrap_call(
            "POST",
            f"/cloud/project/{service_name}/kube",
            **post_kwargs,
        )
        module.exit_json(changed=True, msg=f"Cluster '{name}' created", **result)

    # UPDATE
    kube_id = current["id"]

    for param, api_field in [
        ("region", "region"),
        ("kube_proxy_mode", "kubeProxyMode"),
        ("private_network_id", "privateNetworkId"),
    ]:
        value = module.params.get(param)
        if value is not None and value != current.get(api_field):
            module.fail_json(
                msg=f"Cannot change '{param}' for existing cluster '{name}'",
            )

    needs_update = False
    put_kwargs = {}

    update_policy = module.params.get("update_policy")
    if update_policy is not None and update_policy != current.get("updatePolicy"):
        needs_update = True
        put_kwargs["updatePolicy"] = update_policy

    if not needs_update:
        module.exit_json(
            changed=False,
            msg=f"Cluster '{name}' [{kube_id}] is already up to date",
            **current,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            msg=f"Cluster '{name}' [{kube_id}] would be updated (dry run)",
        )

    client.wrap_call(
        "PUT",
        f"/cloud/project/{service_name}/kube/{kube_id}",
        **put_kwargs,
    )
    updated = client.wrap_call(
        "GET",
        f"/cloud/project/{service_name}/kube/{kube_id}",
    )
    module.exit_json(
        changed=True,
        msg=f"Cluster '{name}' [{kube_id}] updated",
        **updated,
    )


def main():
    run_module()


if __name__ == '__main__':
    main()
