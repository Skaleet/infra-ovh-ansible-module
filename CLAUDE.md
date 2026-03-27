# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Ansible collection (`synthesio.ovh`) providing modules for managing OVHcloud infrastructure — dedicated servers, public cloud instances, Kubernetes clusters, IP management, DNS, and VPS.

- **Collection namespace/name**: `synthesio.ovh` (v5.11.0)
- **Requirements**: Python 3.9+, python-ovh >= 1.0, Ansible 2.12+

## Development Commands

**Lint** (the only CI check):
```bash
flake8 plugins/modules/
# or via Docker:
docker run -ti --rm -v $(pwd):/apps alpine/flake8 -v plugins/modules/*
```

Flake8 config (`.flake8`): ignores E402, W503; max line length 150.

There are no unit or integration tests in this repository.

## Architecture

### Module pattern

Every module follows this exact structure:

```python
DOCUMENTATION = '''...'''   # ansible-doc content
EXAMPLES = r'''...'''
RETURN = '''...'''

from ansible_collections.synthesio.ovh.plugins.module_utils.ovh import OVH, OVHResourceNotFound, ovh_argument_spec

def run_module():
    module_args = ovh_argument_spec()   # adds endpoint/application_key/application_secret/consumer_key
    module_args.update(dict(...))       # module-specific args

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    client = OVH(module)

    # call OVH API
    result = client.wrap_call("GET"|"POST"|"PUT"|"DELETE", "/path/...", **kwargs)
    module.exit_json(changed=..., **result)

def main():
    run_module()
```

### `plugins/module_utils/ovh.py`

The shared OVH client wrapper. Key points:
- `ovh_argument_spec()` — returns the 4 credential params; always call this first in `module_args`
- `OVH(module)` — instantiates the client; uses inline params if all 4 credentials are provided, otherwise falls back to `/etc/ovh.conf`
- `client.wrap_call(verb, path, **kwargs)` — wraps `ovh.Client.call()`; for GET/DELETE, kwargs become query string params; for POST/PUT, they become the request body
- `OVHResourceNotFound` — raised when API returns 404; use to detect missing resources
- All other API errors call `module.fail_json()` directly

### Idempotency pattern

Modules implement idempotency manually:
1. Fetch current state via GET
2. Compare with desired state
3. Skip (return `changed=False`) if already in desired state
4. Create/update/delete only when needed
5. Support `check_mode` — report what *would* happen without making API calls

### State machines

Modules with `state: present/absent` follow:
- `absent` + resource missing → `changed=False`
- `absent` + resource exists → DELETE → `changed=True`
- `present` + resource missing → POST (create) → `changed=True`
- `present` + resource exists → compare mutable fields → PUT if diff → `changed=True/False`

### API field naming

OVH API uses camelCase (`desiredNodes`, `flavorName`). Module params use snake_case (`desired_nodes`, `flavor_name`). Map explicitly in the module code.

### Immutable fields

Some fields cannot be changed after creation (e.g. `flavor_name`, `anti_affinity` on node pools). These must only be sent in the POST body, never in PUT. Document them with "Immutable after creation." in DOCUMENTATION.

## Adding a New Module

1. Create `plugins/modules/<name>.py` following the pattern above
2. Add the module name to the relevant action groups in `meta/runtime.yml`
3. Add an entry to `README.md` under the appropriate section
