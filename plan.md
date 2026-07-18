## Project Implementation Plan — Palms View and Management System

This plan is ordered as requested:

1. **Backend implementation first**
2. **Frontend implementation second**
3. **Local Docker Compose setup**
4. **Infrastructure steps you can follow separately**

---

# 0. Recommended Project Structure

Use a monorepo so BE, FE, deployment files, and shared docs stay together.

```txt
palms-management-system/
├── backend/
│   ├── palms_api/
│   ├── migrations/
│   ├── tests/
│   ├── scripts/
│   ├── pyproject.toml
│   └── alembic.ini
│
├── frontend/
│   ├── public-app/
│   ├── admin-app/
│   └── shared/
│
├── deploy/
│   ├── docker-compose.yml
│   ├── compose.env.example
│   └── local.env.example
│
├── infra/
│   ├── helm/
│   ├── k8s/
│   └── notes/
│
├── docs/
│   ├── api.md
│   ├── database.md
│   ├── local-development.md
│   └── infra-runbook.md
│
└── README.md
```

---

# 1. Backend Implementation Plan

## 1.1 Backend Stack

Use:

- **Python Pyramid 2.x**
- **SQLAlchemy 2.x**
- **Alembic**
- **PostgreSQL**
- **Jinja2**
- **Pillow**
- **Boto3-compatible storage**
  - AWS S3 in production
  - MinIO locally
- **Redis**
  - Background tasks
  - Rate limiting
  - Optional caching
- **RQ or Celery**
  - For report generation, emails, image processing
- **JWT or secure cookie sessions**
  - For admin authentication
- **Pytest**
- **OpenAPI documentation**

Recommended additional backend libraries:

```txt
pyramid
pyramid_tm
pyramid_jinja2
SQLAlchemy
alembic
psycopg[binary]
pydantic
passlib[argon2]
python-jose or PyJWT
bcrypt or argon2-cffi
Pillow
boto3
redis
rq or celery
jinja2
weasyprint or reportlab
python-multipart
pytest
pytest-cov
```

---

## 1.2 Backend Phase 1 — Foundation

### Tasks

1. Create Pyramid application skeleton.
2. Configure settings using environment variables.
3. Add PostgreSQL connection.
4. Add SQLAlchemy session management.
5. Add Alembic migrations.
6. Add global API response format.
7. Add request validation layer.
8. Add error handling middleware.
9. Add health check endpoint.
10. Add logging.

### Deliverables

Endpoints:

```http
GET /health
GET /api/v1/meta
```

Example health response:

```json
{
  "status": "ok",
  "database": "ok",
  "version": "1.0.0"
}
```

---

# 1.3 Backend Phase 2 — Database Design

## Core Tables

### Users and Authentication

```txt
users
roles
permissions
role_permissions
user_permission_overrides
password_reset_tokens
user_invitations
user_sessions
two_factor_settings
audit_logs
```

### Donor and Palm Management

```txt
donors
sections
palms
palm_images
harvest_records
disease_records
treatment_records
palm_notes
palm_relationships
```

### Reports

```txt
report_templates
report_schedules
report_schedule_recipients
report_runs
report_files
```

### Optional Supporting Tables

```txt
email_logs
system_settings
activity_feed
```

---

## Main Entity Relationships

```txt
Donor 1 ── N Palms

Section 1 ── N Palms

Palm 1 ── N PalmImages

Palm 1 ── N HarvestRecords

Palm 1 ── N DiseaseRecords

DiseaseRecord 1 ── N TreatmentRecords

Palm 1 ── N PalmNotes

Palm 1 ── N Child Palms through palm_relationships

User 1 ── N AuditLogs

ReportSchedule 1 ── N ReportRuns
```

---

## Important Model Fields

### donors

```txt
id
full_name
phone
email
address
donation_date
notes
created_at
updated_at
deleted_at
```

### sections

```txt
id
name
description
location_name
soil_type
irrigation_type
gps_latitude
gps_longitude
image_url
created_at
updated_at
deleted_at
```

### palms

```txt
id
code
donor_id
section_id
plantation_date
status
current_health_status
description
created_at
updated_at
deleted_at
```

### palm_images

```txt
id
palm_id
storage_key
thumbnail_url
medium_url
full_url
webp_url
uploaded_by_user_id
captured_at
uploaded_at
metadata_json
```

### harvest_records

```txt
id
palm_id
harvest_date
amount
unit
revenue
notes
created_by_user_id
created_at
updated_at
```

### disease_records

```txt
id
palm_id
disease_name
detected_at
status
notes
created_by_user_id
created_at
updated_at
```

### treatment_records

```txt
id
disease_record_id
treatment_name
treatment_date
notes
created_by_user_id
created_at
```

### audit_logs

```txt
id
actor_user_id
action
entity_type
entity_id
old_values_json
new_values_json
ip_address
user_agent
created_at
```

---

# 1.4 Backend Phase 3 — Authentication and Authorization

## Features

Implement:

1. Admin login with email/password.
2. Secure password hashing.
3. Forgot password flow.
4. Password reset email.
5. Role-based access control.
6. Granular permissions.
7. Session timeout.
8. Audit logging.
9. Optional 2FA placeholder or full implementation.

## Roles

```txt
Super Admin
Admin
Editor
Viewer
```

## Permission Examples

```txt
users.read
users.create
users.update
users.disable

donors.read
donors.create
donors.update
donors.delete

palms.read
palms.create
palms.update
palms.delete
palms.bulk_update
palms.export

sections.read
sections.create
sections.update
sections.delete

reports.read
reports.generate
reports.schedule

audit_logs.read
```

## Auth Endpoints

```http
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
GET  /api/v1/auth/me
POST /api/v1/auth/change-password
POST /api/v1/auth/2fa/enable
POST /api/v1/auth/2fa/disable
```

---

# 1.5 Backend Phase 4 — Public API

These endpoints do not require authentication.

## Public Search

```http
GET /api/v1/public/search?query=...
GET /api/v1/public/donors/suggest?query=...
GET /api/v1/public/palms/{palm_code}
```

## Search Behavior

The search should support:

- Phone number
- Donor name
- Palm code

Example response:

```json
{
  "items": [
    {
      "palm_id": "uuid",
      "palm_code": "PALM-001",
      "donor_name": "Ahmed Ali",
      "section_name": "North Section",
      "plantation_date": "2020-03-15",
      "current_age": {
        "years": 4,
        "months": 9
      },
      "thumbnail_url": "https://..."
    }
  ]
}
```

## Palm Profile Response Should Include

```txt
Palm basic info
Donor info
Section info
Images
Harvest summary
Disease history
Treatment notes
Children palms
Current age
Total harvest amount
Total revenue
```

---

# 1.6 Backend Phase 5 — Admin APIs

## Dashboard Overview

```http
GET /api/v1/admin/dashboard/overview
GET /api/v1/admin/dashboard/activity
```

Should return:

```txt
Total palms
Total donors
Total sections
Recent harvests
Total revenue
Active vs inactive palms
Recent activity
Upcoming scheduled reports
```

---

## Palms Management API

```http
GET    /api/v1/admin/palms
POST   /api/v1/admin/palms
GET    /api/v1/admin/palms/{id}
PATCH  /api/v1/admin/palms/{id}
DELETE /api/v1/admin/palms/{id}

POST   /api/v1/admin/palms/bulk-delete
POST   /api/v1/admin/palms/bulk-update-section
POST   /api/v1/admin/palms/export

POST   /api/v1/admin/palms/{id}/images
DELETE /api/v1/admin/palms/{id}/images/{image_id}

POST   /api/v1/admin/palms/{id}/harvests
PATCH  /api/v1/admin/palms/{id}/harvests/{harvest_id}
DELETE /api/v1/admin/palms/{id}/harvests/{harvest_id}

POST   /api/v1/admin/palms/{id}/diseases
PATCH  /api/v1/admin/palms/{id}/diseases/{disease_id}
DELETE /api/v1/admin/palms/{id}/diseases/{disease_id}

POST   /api/v1/admin/palms/{id}/notes
DELETE /api/v1/admin/palms/{id}/notes/{note_id}
```

---

## Donors Management API

```http
GET    /api/v1/admin/donors
POST   /api/v1/admin/donors
GET    /api/v1/admin/donors/{id}
PATCH  /api/v1/admin/donors/{id}
DELETE /api/v1/admin/donors/{id}
GET    /api/v1/admin/donors/{id}/palms
```

---

## Sections Management API

```http
GET    /api/v1/admin/sections
POST   /api/v1/admin/sections
GET    /api/v1/admin/sections/{id}
PATCH  /api/v1/admin/sections/{id}
DELETE /api/v1/admin/sections/{id}
POST   /api/v1/admin/sections/{id}/image
```

For delete section, support reassignment:

```http
DELETE /api/v1/admin/sections/{id}?reassign_to_section_id=...
```

---

## Reports API

```http
GET  /api/v1/admin/reports/types
POST /api/v1/admin/reports/preview
POST /api/v1/admin/reports/generate
GET  /api/v1/admin/reports/templates
POST /api/v1/admin/reports/templates
```

Report formats:

```txt
CSV
PDF
```

---

## Scheduled Reports API

```http
GET    /api/v1/admin/report-schedules
POST   /api/v1/admin/report-schedules
GET    /api/v1/admin/report-schedules/{id}
PATCH  /api/v1/admin/report-schedules/{id}
DELETE /api/v1/admin/report-schedules/{id}

POST   /api/v1/admin/report-schedules/{id}/pause
POST   /api/v1/admin/report-schedules/{id}/resume

GET    /api/v1/admin/report-schedules/{id}/runs
GET    /api/v1/admin/report-runs/{id}/download
```

Schedule definitions can be stored in DB as primary source and exported/imported as YAML/JSON if required.

Example schedule config:

```json
{
  "name": "Monthly Donor Report",
  "report_type": "donors",
  "frequency": "monthly",
  "day_of_month": 1,
  "time": "08:00",
  "timezone": "Asia/Riyadh",
  "format": "pdf",
  "recipients": [
    "admin@example.com",
    "finance@example.com"
  ],
  "email_subject": "Monthly Donor Report",
  "include_summary": true,
  "attach_file": true,
  "enabled": true
}
```

---

## Admin Profile API

```http
GET   /api/v1/admin/profile
PATCH /api/v1/admin/profile
POST  /api/v1/admin/profile/avatar
POST  /api/v1/admin/profile/change-password
POST  /api/v1/admin/profile/change-email
```

---

## User Management API

Super Admin only.

```http
GET    /api/v1/admin/users
POST   /api/v1/admin/users/invite
GET    /api/v1/admin/users/{id}
PATCH  /api/v1/admin/users/{id}
POST   /api/v1/admin/users/{id}/disable
POST   /api/v1/admin/users/{id}/enable
POST   /api/v1/admin/users/{id}/reset-password
GET    /api/v1/admin/users/{id}/audit-logs
```

---

# 1.7 Backend Phase 6 — Image Processing

## Required Features

When an image is uploaded:

1. Validate file type.
2. Strip dangerous metadata.
3. Preserve safe EXIF data if required.
4. Generate:
   - Thumbnail
   - Medium
   - Full-size optimized
   - WebP version
5. Upload to storage.
6. Store image references in DB.

## Local Storage Strategy

Use **MinIO** locally because it is S3-compatible.

Production uses AWS S3.

Use one storage abstraction:

```python
class StorageClient:
    def upload_file(...)
    def delete_file(...)
    def get_public_url(...)
    def get_signed_url(...)
```

---

# 1.8 Backend Phase 7 — Email System

## Email Types

1. Password reset email
2. User invitation email
3. Scheduled report email
4. Notification email

## Use Jinja2 Templates

Example structure:

```txt
backend/palms_api/templates/emails/
├── base.html.jinja2
├── password_reset.html.jinja2
├── user_invitation.html.jinja2
├── scheduled_report.html.jinja2
└── notification.html.jinja2
```

## Local Email Testing

Use **MailHog** in Docker Compose.

---

# 1.9 Backend Phase 8 — Reporting

## Report Types

1. Palms report
2. Donors report
3. Sections report
4. Custom report

## Output Formats

- CSV
- PDF

## Generation Flow

```txt
Admin requests report
↓
Backend validates filters and permissions
↓
Report job is created
↓
Worker generates CSV/PDF
↓
File uploaded to S3/MinIO
↓
Report run record saved
↓
Download URL returned or email sent
```

---

# 1.10 Backend Phase 9 — Scheduled Reports Worker

Use a background worker process.

Recommended local services:

```txt
api
worker
scheduler
redis
postgres
```

## Scheduler Responsibilities

1. Check enabled report schedules.
2. Detect due schedules.
3. Enqueue report generation jobs.
4. Save execution history.
5. Send success/failure emails.

## Worker Responsibilities

1. Generate report.
2. Upload report file.
3. Send email.
4. Update report run status.

---

# 1.11 Backend Phase 10 — Testing

## Minimum Test Coverage

- Auth tests
- Permission tests
- Public search tests
- Palm CRUD tests
- Donor CRUD tests
- Section CRUD tests
- Image upload tests
- Report generation tests
- Scheduled report tests

## Commands

```bash
pytest
pytest --cov=palms_api
```

---

# 2. Frontend Implementation Plan

Use React with TypeScript for both public and admin apps.

Recommended structure:

```txt
frontend/
├── public-app/
│   ├── src/
│   └── package.json
│
├── admin-app/
│   ├── src/
│   └── package.json
│
└── shared/
    ├── api-client/
    ├── types/
    └── utils/
```

---

# 2.1 Frontend Shared Setup

## Common Libraries

```txt
React
TypeScript
Vite
TanStack Query
Axios
Zod
date-fns
```

## Shared API Client

Create a shared API client:

```txt
frontend/shared/api-client/
├── http.ts
├── auth.ts
├── public.ts
├── palms.ts
├── donors.ts
├── sections.ts
├── reports.ts
└── users.ts
```

Use:

- Axios interceptors
- Auth token/session handling
- Standardized error handling
- Query key constants for TanStack Query

---

# 2.2 Public Landing Page Implementation

## Stack

Use:

- React + TypeScript
- Tailwind CSS
- Headless UI
- Framer Motion
- PhotoSwipe
- TanStack Query
- React Hook Form where needed

---

## Public Pages

```txt
/
Search landing page

/search
Search results page

/palms/:palmCode
Palm profile page

/about
Optional foundation info page
```

---

## Public Components

```txt
HeroSection
SearchBar
SearchSuggestions
PalmResultCard
PalmImageGallery
PalmInfoCard
DonorInfoCard
HarvestSummaryCard
DiseaseHistoryTimeline
ChildrenPalmsList
SectionMap
LoadingSkeleton
EmptyState
```

---

## Public Implementation Steps

### Step 1 — Landing Page

Create a modern landing page with:

- Lifemaker Foundation branding
- Hero image/video background
- Search bar
- CTA sections
- Mobile-first layout

### Step 2 — Search

Implement:

- Debounced search
- Donor name typeahead
- Loading states
- Empty results state
- Result cards

### Step 3 — Palm Profile

Implement:

- Image masonry/gallery
- Lightbox
- Palm age calculation
- Total harvest
- Total revenue
- Disease history
- Children palms
- Donor card
- Section/location card

### Step 4 — Accessibility and Performance

Add:

- Semantic HTML
- Keyboard-friendly gallery
- Proper labels
- Lazy-loaded images
- Optimized assets
- Lighthouse checks

---

# 2.3 Admin Dashboard Implementation

## Stack

Use:

- React + TypeScript
- Material UI or Ant Design
- TanStack Query
- Zustand for UI state
- React Hook Form
- Zod
- TanStack Table or AG Grid
- Recharts
- React Dropzone

Recommended: **Material UI + TanStack Query + Zustand**.

---

## Admin Routes

```txt
/admin/login
/admin/forgot-password
/admin/reset-password

/admin
/admin/overview
/admin/palms
/admin/palms/new
/admin/palms/:id
/admin/palms/:id/edit

/admin/donors
/admin/donors/new
/admin/donors/:id

/admin/sections
/admin/sections/new
/admin/sections/:id

/admin/reports
/admin/reports/templates
/admin/report-schedules
/admin/report-schedules/new
/admin/report-schedules/:id

/admin/profile

/admin/users
/admin/users/new
/admin/users/:id

/admin/audit-logs
```

---

# 2.4 Admin Dashboard Implementation Steps

## Phase 1 — Admin Shell

Build:

- Login page
- Auth guard
- Dashboard layout
- Sidebar
- Header
- User menu
- Role-based menu visibility

---

## Phase 2 — Overview Dashboard

Build widgets for:

- Total palms
- Total donors
- Total sections
- Recent harvests
- Total revenue
- Active/inactive palms
- Recent activity feed
- Quick actions

Use Recharts for trends.

---

## Phase 3 — Palms Management

Features:

- Table listing
- Search
- Filters
- Sorting
- Pagination
- Bulk actions
- Add/edit palm form
- Detail page
- Image upload
- Harvest records
- Disease records
- Notes
- Children palms

---

## Phase 4 — Donors Management

Features:

- Donor table
- Search/filter/sort
- Donor detail page
- Associated palms list
- Donation history
- Add/edit donor form

---

## Phase 5 — Sections Management

Features:

- Section table
- Palm counts
- Add/edit section form
- Optional section image upload
- Delete with reassignment option

---

## Phase 6 — Reports

Features:

- Select report type
- Select fields
- Select filters
- Date range selection
- Preview report
- Export CSV/PDF
- Save templates

---

## Phase 7 — Scheduled Reports

Features:

- Schedule listing
- Create/edit schedule
- Frequency selector:
  - Daily
  - Weekly
  - Monthly
  - Cron
- Recipients manager
- Email subject field
- Pause/resume
- Execution history
- Download past reports

---

## Phase 8 — Admin Profile

Features:

- View profile
- Edit name
- Change email
- Change password
- Upload profile picture
- Enable/disable 2FA
- Language preference

---

## Phase 9 — User Management

Super Admin only.

Features:

- User table
- Invite user
- Change role
- Enable/disable account
- Reset password
- View audit logs

---

# 3. Local Docker Compose Plan

The goal is to test the whole system locally before infrastructure work.

---

## 3.1 Local Services

Docker Compose should include:

```txt
postgres
redis
minio
mailhog
backend (one image: API, RQ worker, and report scheduler)
frontend (one image: public site and admin portal)
```

Compose must use prebuilt images only. It must not contain `build`, `context`,
or `dockerfile` entries, and it must not rely on any Dockerfile in this
repository. The two custom application images are:

```txt
palms-backend:<tag>
palms-frontend:<tag>
```

The official PostgreSQL, Redis, MinIO, and MailHog images are supporting
services, not additional backend or frontend images.

The backend image owns the application, migrations, API server, worker, and
scheduler startup. The frontend image owns both static React builds and its
Nginx configuration. Public and admin behavior is separated by routes and
RBAC, not by Compose services or images:

```txt
http://localhost:3000/             public site
http://localhost:3000/admin/       admin portal
http://localhost:3000/api/v1/...   backend API proxy
```

---

## 3.2 Image configuration

Create `deploy/compose.env` from this example and point it at published,
versioned images:

```env
BACKEND_IMAGE=registry.example.com/palms-backend:1.0.0
FRONTEND_IMAGE=registry.example.com/palms-frontend:1.0.0
```

Build and publish those two images in CI or another image-build process before
running Compose. Local Compose only pulls and runs them.

---

## 3.3 Suggested Local Ports

```txt
Backend API:        http://localhost:8000
Public Frontend:    http://localhost:3000
Admin Frontend:     http://localhost:3000/admin/
PostgreSQL:        localhost:5432
Redis:             localhost:6379
MinIO Console:     http://localhost:9001
MinIO API:         http://localhost:9000
MailHog UI:        http://localhost:8025
```

---

## 3.4 Runtime topology

`deploy/docker-compose.yml` is the source of truth for local runtime
configuration. It starts one `backend` container from `BACKEND_IMAGE`, which
runs migrations before supervising the API, RQ worker, and report scheduler.
It starts one `frontend` container from `FRONTEND_IMAGE`, which serves the
public app at `/` and the admin app at `/admin/` through its built-in Nginx
with a same-origin `/api/` proxy. Neither service builds an image locally.

---

## 3.5 Standalone `deploy/docker-compose.yml`

```yaml
name: palms-local

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: palms_db
      POSTGRES_USER: palms_user
      POSTGRES_PASSWORD: palms_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U palms_user -d palms_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: palms_minio
      MINIO_ROOT_PASSWORD: palms_minio_password
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  mailhog:
    image: mailhog/mailhog:v1.0.1
    ports:
      - "1025:1025"
      - "8025:8025"

  backend:
    image: ${BACKEND_IMAGE:?Set BACKEND_IMAGE in compose.env}
    env_file:
      - ./local.env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_started
      mailhog:
        condition: service_started
    restart: unless-stopped

  frontend:
    image: ${FRONTEND_IMAGE:?Set FRONTEND_IMAGE in compose.env}
    ports:
      - "3000:80"
    depends_on:
      backend:
        condition: service_started
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

The frontend image must be published with an Nginx configuration that proxies
`/api/` to `http://backend:8000`; the Compose file does not mount or generate
that configuration.

---

## 3.6 Example `local.env`

```env
APP_ENV=local
APP_SECRET=change_me_local_secret
API_BASE_URL=http://localhost:8000
PUBLIC_APP_URL=http://localhost:3000
ADMIN_APP_URL=http://localhost:3000/admin/

DATABASE_URL=postgresql+psycopg://palms_user:palms_password@postgres:5432/palms_db

REDIS_URL=redis://redis:6379/0

JWT_SECRET=change_me_jwt_secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
SESSION_TIMEOUT_MINUTES=60

SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=no-reply@lifemaker.local
SMTP_FROM_NAME=Lifemaker Foundation

STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=palms_minio
S3_SECRET_ACCESS_KEY=palms_minio_password
S3_BUCKET_NAME=palms-images
S3_REGION=us-east-1
S3_PUBLIC_BASE_URL=http://localhost:9000/palms-images

IMAGE_MAX_UPLOAD_MB=15
```

---

## 3.7 Local Development Commands

From the `deploy/` directory, create `compose.env` and `local.env` from their
example files, then pull and start the already-published images:

```bash
docker compose --env-file compose.env pull
docker compose --env-file compose.env up -d
```

Migrations run automatically before the backend supervisor starts. To run them
manually if needed:

```bash
docker compose --env-file compose.env exec backend alembic upgrade head
```

Create initial Super Admin:

```bash
docker compose --env-file compose.env exec backend python scripts/create_super_admin.py \
  --email admin@example.com \
  --password Admin12345 \
  --name "Super Admin"
```

Seed sample data:

```bash
docker compose --env-file compose.env exec backend python scripts/seed_demo_data.py
```

Access local apps:

```txt
Public site:
http://localhost:3000

Admin dashboard:
http://localhost:3000/admin/

Backend API:
http://localhost:8000

MailHog:
http://localhost:8025

MinIO:
http://localhost:9001
```

---

# 4. Suggested Implementation Milestones

## Milestone 1 — Backend Base

Deliver:

- Pyramid app
- PostgreSQL connection
- Alembic setup
- Health endpoint
- Config system
- Versioned `palms-backend` image published by CI

---

## Milestone 2 — Auth and Users

Deliver:

- Login
- Logout
- Current user endpoint
- Password reset
- Roles and permissions
- User management base
- Audit logging

---

## Milestone 3 — Core Data APIs

Deliver:

- Donors CRUD
- Sections CRUD
- Palms CRUD
- Harvest records
- Disease records
- Palm notes
- Filtering, sorting, pagination

---

## Milestone 4 — Image Uploads

Deliver:

- Upload palm images
- Generate image sizes
- WebP conversion
- Store in MinIO/S3
- Delete images
- Public image access

---

## Milestone 5 — Public API

Deliver:

- Search by phone/name/code
- Typeahead donor search
- Public palm profile endpoint

---

## Milestone 6 — Reports

Deliver:

- CSV generation
- PDF generation
- Report preview
- Save report templates

---

## Milestone 7 — Scheduled Reports

Deliver:

- Schedule creation
- Scheduler process
- Worker process
- Email delivery
- Schedule history
- Download past reports

---

## Milestone 8 — Public Frontend

Deliver:

- Landing page
- Search
- Results
- Palm profile
- Gallery
- Responsive/mobile-first UI

---

## Milestone 9 — Admin Frontend

Deliver:

- Login
- Dashboard
- Palms management
- Donors management
- Sections management
- Reports
- Scheduled reports
- Profile
- User management

---

## Milestone 10 — Local Compose Complete

Deliver:

- One `palms-backend` image and one `backend` service running the API, worker,
  and scheduler
- PostgreSQL
- Redis
- MinIO
- MailHog
- One `palms-frontend` image and one `frontend` service serving `/` and
  `/admin/`
- Seed scripts
- Local testing documentation with no Compose build configuration

---

# 5. Infrastructure Steps You Can Follow

You said you will handle the infra part, so below is a practical runbook.

---

## 5.1 AWS Foundation

### Step 1 — Create VPC

Create:

- 1 VPC
- 2 or 3 Availability Zones
- Public subnets
- Private subnets
- NAT Gateway for private subnet outbound access
- Internet Gateway
- Route tables

Recommended layout:

```txt
Public subnets:
- ALB
- Bastion if needed

Private subnets:
- K3s nodes
- RDS
```

---

## 5.2 RDS PostgreSQL

### Step 2 — Create RDS PostgreSQL

Use:

- PostgreSQL 15+
- Multi-AZ enabled
- Instance type: `db.m7g.large` or similar
- Automated backups: 35 days
- Performance Insights enabled
- Storage autoscaling enabled
- Private subnet group
- Security group allowing access from K3s nodes only

Create database:

```txt
palms_db
```

Create app user:

```txt
palms_user
```

Store credentials in:

- AWS Secrets Manager, or
- Kubernetes Secret

Recommended: **AWS Secrets Manager**.

---

## 5.3 S3 and CloudFront

### Step 3 — Create S3 Bucket

Create bucket for palm images and generated reports.

Example:

```txt
lifemaker-palms-prod-assets
```

Enable:

- Versioning
- Server-side encryption
- Lifecycle rule:
  - Move older images/reports to Glacier after 1 year if appropriate

Suggested prefixes:

```txt
images/
reports/
avatars/
sections/
```

---

### Step 4 — Configure CloudFront

Use CloudFront for image delivery.

Options:

1. Public images through CloudFront.
2. Private images with signed URLs if required.

For public donor-facing palm images, public CDN delivery is simpler.

Configure:

- CloudFront distribution
- Origin Access Control
- S3 bucket policy allowing CloudFront
- Cache policy for images
- Custom domain, e.g.:

```txt
assets.palms.lifemaker.org
```

---

## 5.4 ECR

### Step 5 — Create Amazon ECR Repositories

Create repositories:

```txt
palms-backend
palms-frontend
```

Enable:

- Image scanning
- Lifecycle policies to remove old images

---

## 5.5 K3s Cluster

### Step 6 — Provision EC2 Nodes

Use:

```txt
m7i-flex.large
```

Create 2 EC2 instances in private subnets.

Both nodes act as masters and run workloads.

Recommended:

- Ubuntu 22.04 LTS
- Encrypted EBS volumes
- IAM role with access to ECR, CloudWatch, S3 if needed
- Security group allowing K3s node communication

---

### Step 7 — Install K3s

On node 1:

```bash
curl -sfL https://get.k3s.io | sh -s - server \
  --cluster-init \
  --write-kubeconfig-mode 644
```

Get token:

```bash
sudo cat /var/lib/rancher/k3s/server/node-token
```

On node 2:

```bash
curl -sfL https://get.k3s.io | K3S_TOKEN=<TOKEN> sh -s - server \
  --server https://<NODE_1_PRIVATE_IP>:6443 \
  --write-kubeconfig-mode 644
```

Verify:

```bash
kubectl get nodes
```

---

## 5.6 Ingress and Load Balancer

### Step 8 — Configure ALB

Use AWS Load Balancer Controller or expose K3s ingress through an ALB.

Recommended approach:

- Install AWS Load Balancer Controller
- Use ALB Ingress
- Use ACM certificate
- Route 53 DNS records

Domains:

```txt
palms.lifemaker.org            public site, /admin/, and /api/
assets.palms.lifemaker.org
```

---

## 5.7 Kubernetes Namespaces

### Step 9 — Create Namespaces

```bash
kubectl create namespace palms-prod
kubectl create namespace palms-staging
kubectl create namespace monitoring
```

---

## 5.8 Secrets

### Step 10 — Add Secrets

Create Kubernetes secrets or sync from AWS Secrets Manager.

Required values:

```txt
DATABASE_URL
APP_SECRET
JWT_SECRET
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
S3_BUCKET_NAME
S3_REGION
AWS_ACCESS_KEY_ID, if not using IAM role
AWS_SECRET_ACCESS_KEY, if not using IAM role
```

Recommended:

- Use IAM roles where possible.
- Avoid static AWS keys in Kubernetes.

---

## 5.9 Helm Charts

### Step 11 — Create Helm Chart

Create chart:

```txt
infra/helm/palms/
├── Chart.yaml
├── values.yaml
├── values.staging.yaml
├── values.prod.yaml
└── templates/
    ├── backend-deployment.yaml
    ├── backend-service.yaml
    ├── frontend-deployment.yaml
    ├── frontend-service.yaml
    ├── ingress.yaml
    ├── secrets.yaml
    ├── configmap.yaml
    └── hpa.yaml
```

Deploy components:

```txt
backend
frontend
```

Use the same `palms-backend` image for any separately scaled API, worker, or
scheduler workload. The public and admin applications are served by the one
`palms-frontend` image at `/` and `/admin/`.

---

## 5.10 Application Deployment

### Step 12 — Deploy to Staging

```bash
helm upgrade --install palms-staging ./infra/helm/palms \
  --namespace palms-staging \
  -f ./infra/helm/palms/values.staging.yaml
```

Run migrations:

```bash
kubectl -n palms-staging exec deploy/backend -- alembic upgrade head
```

Run smoke tests:

```bash
curl https://api-staging.palms.lifemaker.org/health
```

---

### Step 13 — Deploy to Production

```bash
helm upgrade --install palms-prod ./infra/helm/palms \
  --namespace palms-prod \
  -f ./infra/helm/palms/values.prod.yaml
```

Run production migration job:

```bash
kubectl -n palms-prod create job palms-migration-$(date +%s) \
  --from=cronjob/palms-migration
```

Or use a Helm migration hook.

---

## 5.11 CI/CD with GitHub Actions

### Step 14 — Create Pipeline

Pipeline stages:

```txt
Lint
Test
Security scan
Build Docker images
Push to ECR
Deploy to staging
Run migrations
Smoke test
Manual approval
Deploy to production
Rollback on failure
```

Suggested workflows:

```txt
.github/workflows/backend.yml
.github/workflows/frontend.yml
.github/workflows/deploy-staging.yml
.github/workflows/deploy-production.yml
```

---

## 5.12 Monitoring

### Step 15 — Install Monitoring Stack

Install:

- Prometheus
- Grafana
- Loki
- Promtail
- Alertmanager

You can use Helm:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
```

Install kube-prometheus-stack:

```bash
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring
```

Install Loki:

```bash
helm install loki grafana/loki-stack \
  --namespace monitoring
```

---

## 5.13 Alerts

Configure alerts for:

```txt
High API error rate
High API latency
Backend pod restarts
Worker queue backlog
Scheduler failures
RDS CPU high
RDS connection count high
Disk/storage usage
Failed scheduled reports
Email delivery failures
```

---

## 5.14 Backups

### RDS

Enable:

```txt
Automated backups
35-day retention
Point-in-time recovery
Manual snapshots before major releases
```

### S3

Enable:

```txt
Versioning
Lifecycle policies
Replication if needed
```

### Kubernetes

If needed:

```txt
Velero backups
Helm values backup
Secrets backup policy
```

---

# 6. Recommended MVP Scope

To avoid delaying the first usable release, build in this order:

## MVP 1

```txt
Backend auth
Roles
Donors CRUD
Sections CRUD
Palms CRUD
Image upload
Public search
Public palm profile
Basic admin dashboard
Local Docker Compose
```

## MVP 2

```txt
Harvest records
Disease/treatment history
Reports CSV/PDF
Email system
Scheduled reports
Audit logs
```

## MVP 3

```txt
2FA
Advanced custom reports
Advanced analytics
Map integration
CloudFront optimization
Fine-grained permission overrides
```

---

# 7. Final Build Order Summary

## Backend First

```txt
1. Project setup
2. Database models/migrations
3. Auth/RBAC
4. Donors API
5. Sections API
6. Palms API
7. Image upload/processing
8. Public search/profile API
9. Dashboard overview API
10. Reports API
11. Scheduled reports worker
12. Email system
13. Tests
```

## Frontend Second

```txt
1. Shared API client
2. Public landing page
3. Public search
4. Public palm profile
5. Admin login/layout
6. Admin overview dashboard
7. Palms management
8. Donors management
9. Sections management
10. Reports
11. Scheduled reports
12. Profile and users
```

## Compose Last

```txt
1. PostgreSQL
2. Redis
3. MinIO
4. MailHog
5. One prebuilt backend image (API, worker, and scheduler)
6. One prebuilt frontend image (public and admin routes)
7. Seed scripts
```

This gives you a complete local environment before moving to AWS/K3s infrastructure.