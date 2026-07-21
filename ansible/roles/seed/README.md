# Seed

Waits for the backend Deployment, creates the Super Admin account, then runs
the demo seed script inside a backend pod.

Requires the `deploy` role (Helm release) to have succeeded first.

## Variables

See `defaults/main.yml`.

| Variable | Default | Notes |
|----------|---------|-------|
| `palms_admin_email` | `admin@example.com` | |
| `palms_admin_password` | `Admin12345678` | Override via vault |
| `palms_admin_name` | `Super Admin` | |
| `palms_seed_script` | `seed_full_demo_data.py` | Or `seed_demo_data.py` |
| `palms_create_admin` | `true` | |
| `palms_run_seed_data` | `true` | |

## Example

```yaml
roles:
  - deploy
  - seed
```

```bash
ansible-playbook playbook.yaml
```
