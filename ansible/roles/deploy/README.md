# Deploy

Clones the Palms repo, builds app images with Docker on each node, then
installs/upgrades the Helm chart at `helm/palms`.

This cluster installs k3s with `--docker`, so images only need to exist in the
local Docker daemon. `k3s ctr` import is disabled by default
(`palms_import_images_to_k3s: false`).

## Requirements

- Docker (role `docker`)
- Helm (role `helm`)
- k3s with kubeconfig at `/etc/rancher/k3s/k3s.yaml`
- ingress-nginx (role `nginx-ingress`) before deploy

## Variables

See `defaults/main.yml`. Override secrets in vault/group_vars:

- `palms_postgres_password`
- `palms_minio_root_password`

Optional ConfigMap overrides via `palms_config` (dict merged into chart `config`).

Set `palms_import_images_to_k3s: true` only if you later switch k3s off `--docker`
(containerd runtime).

## Example

```yaml
roles:
  - deploy
```
