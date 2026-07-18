# Palms API

This directory contains the Pyramid 2 backend for administration, public palm
profiles, storage-backed media, reports, scheduled report jobs, and email.

## Prerequisites

- Python 3.11–3.14
- PostgreSQL is optional for local development; tests use SQLite in memory.

## Install

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run tests

```powershell
pytest
```

The test suite injects an in-memory SQLite URL and never needs a running
PostgreSQL server.

## Run locally

```powershell
$env:DATABASE_URL = "sqlite+pysqlite:///./palms.db"
pserve development.ini
```

For PostgreSQL, set `DATABASE_URL` before starting the service:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://palms_user:password@localhost:5432/palms_db"
pserve development.ini
```

The local server exposes `GET /health`, `GET /api/v1/meta`, unauthenticated
public APIs at `/api/v1/public/*`, authentication at `/api/v1/auth/*`, and
authenticated administration APIs at `/api/v1/admin/*`.

## Core API surface

- Auth: login/logout/me, password change/reset requests, and 2FA state
  placeholders. Sessions are opaque server-side records and are delivered in
  `HttpOnly`, `SameSite=Lax` cookies.
- Super Admin user operations: list, invite, patch, enable/disable, reset
  requests, and actor audit history. Reset and invitation secrets are stored
  only as hashes and are never returned by the API.
- Donors, sections, and palms: CRUD with soft deletion, filtering, sorting,
  pagination, ownership checks, section reassignment, and palm bulk actions.
- Palm histories: harvests, diseases/treatments, notes, parent/child
  relationships, and processed image variants.
- Public APIs: normalized name/phone/palm-code search, donor suggestions, and
  contact-safe palm profiles.
- Reports: strict field/filter allowlists, CSV/PDF output, templates, durable
  files and signed download links, plus scheduled runs.
- Email: Jinja2 password-reset, invitation, notification, and report-result
  templates. Delivery is disabled by default; set `EMAIL_ENABLED=true` and
  MailHog-compatible `SMTP_*` values to send.

## Advanced runtime configuration

Tests and local development use the safe in-memory object store and synchronous
report executor by default. Set `STORAGE_PROVIDER=s3` with `S3_ENDPOINT_URL`
(for MinIO), `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, and `S3_BUCKET_NAME`
to use S3-compatible storage. Set `REPORT_EXECUTION_MODE=rq` and `REDIS_URL`
to queue persisted report runs through RQ.

Run a scheduler pass from a separate process:

```powershell
palms-report-scheduler
```

The scheduler creates a durable queued run before it submits execution. A
completed run always has a corresponding stored file; otherwise it remains
queued/running or is explicitly marked failed.

## Migrations

```powershell
alembic upgrade head
```

`20260718_0001` is an intentional empty baseline. `20260718_0002` creates the
core schema and seeds Super Admin, Admin, Editor, Viewer, and their granular
permissions. `20260718_0003` adds media, report, email, setting, and activity
persistence plus report permissions. Create the first Super Admin
after migrating with:

```powershell
python scripts/create_super_admin.py --email admin@example.com --password "StrongPassword123" --name "Super Admin"
```

The application deliberately does not expose a public registration endpoint.
