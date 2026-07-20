# Local development

This project is designed to run locally with Docker Compose using **prebuilt**
application images. Compose itself never builds images.

## Prerequisites

- Docker Desktop with Compose v2
- Ability to build images locally (or pull published tags)

## 1. Build application images locally

From the repository root:

```powershell
docker build -t palms-backend:local ./backend
docker build -t palms-frontend:local ./frontend
```

## 2. Configure Compose env files

```powershell
cd deploy
Copy-Item compose.env.example compose.env
Copy-Item local.env.example local.env
```

`compose.env` points Compose at the image tags. `local.env` configures the
backend runtime (Postgres, Redis, MinIO, MailHog, sessions, email).

## 3. Start the stack

```powershell
docker compose --env-file compose.env pull
docker compose --env-file compose.env up -d
```

`pull` only affects official dependency images when tags are already local for
`palms-backend` / `palms-frontend`.

## 4. Bootstrap admin and demo data

```powershell
docker compose --env-file compose.env exec backend python scripts/create_super_admin.py --email admin@example.com --password "Admin12345678" --name "Super Admin"
docker compose --env-file compose.env exec backend python scripts/seed_demo_data.py
# Or a fuller dataset (10 donors, 20 palms with images, reports + schedules):
docker compose --env-file compose.env exec backend python scripts/seed_full_demo_data.py
```

## 5. Open the apps

- Public site: http://localhost:3000
- Admin portal: http://localhost:3000/admin/
- Backend API: http://localhost:8000
- MailHog: http://localhost:8025
- MinIO console: http://localhost:9001

Default local admin login after bootstrap:

- Email: `admin@example.com`
- Password: `Admin12345678`

Public search demo palm code: `PALM-001`

## Notes

- Compose contains no `build`, `context`, or `dockerfile` entries.
- The backend container runs migrations, then supervises API + RQ worker +
  report scheduler.
- The frontend image serves the public app at `/`, the admin app at `/admin/`,
  and proxies `/api/` and `/health` to the backend service.
