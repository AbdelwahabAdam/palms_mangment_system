# Palms View and Management System

Local-first monorepo for Lifemaker Foundation palm discovery and administration.

## Structure

- `backend/` — Pyramid API, workers, migrations, tests
- `frontend/shared/` — typed API client and contracts
- `frontend/public-app/` — public discovery site
- `frontend/admin-app/` — authenticated admin portal
- `deploy/` — build-free Docker Compose for local end-to-end testing
- `docs/` — local development notes

## Quick local Compose

```powershell
docker build -t palms-backend:local ./backend
docker build -t palms-frontend:local ./frontend
cd deploy
Copy-Item compose.env.example compose.env
Copy-Item local.env.example local.env
docker compose --env-file compose.env up -d
docker compose --env-file compose.env exec backend python scripts/create_super_admin.py --email admin@example.com --password "Admin12345678" --name "Super Admin"
docker compose --env-file compose.env exec backend python scripts/seed_demo_data.py
```

Then open http://localhost:3000 and http://localhost:3000/admin/.

See [docs/local-development.md](docs/local-development.md) for details.

## Backend tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

## Frontend checks

```powershell
cd frontend
npm install
npm test
npm run build
```

Infrastructure (cloud/Kubernetes/Helm/CI) is intentionally out of scope for this
repository stage.
