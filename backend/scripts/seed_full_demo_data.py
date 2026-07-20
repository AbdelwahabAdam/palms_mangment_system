"""Seed 10 donors, 20 palms (with images), report templates/runs, and schedules.

Idempotent: skips when SEED-PALM-001 already exists unless --force is passed
(force only re-seeds if you wipe data first; it will not delete existing rows).

Usage (Compose / k8s backend container)::

    python scripts/seed_full_demo_data.py
"""

from __future__ import annotations

import argparse
import colorsys
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from PIL import Image, ImageDraw
from sqlalchemy import select

from palms_api.config import get_settings
from palms_api.database import Database
from palms_api.email_service import EmailService
from palms_api.images import process_and_store_image
from palms_api.models import (
    Donor,
    HarvestRecord,
    Palm,
    PalmImage,
    PalmRelationship,
    ReportRun,
    ReportSchedule,
    ReportScheduleRecipient,
    ReportTemplate,
    Section,
    User,
    utcnow,
)
from palms_api.reporting import REPORT_FIELDS, SynchronousReportExecutor
from palms_api.scheduler import next_run_at
from palms_api.seeding import seed_system_rbac
from palms_api.storage import build_storage_client


SEED_MARKER_CODE = "SEED-PALM-001"
DONOR_COUNT = 10
PALM_COUNT = 20

DONOR_NAMES = [
    "Ahmed Al-Rashid",
    "Fatima Hassan",
    "Omar Khalil",
    "Layla Mansour",
    "Youssef Nasser",
    "Nour Ibrahim",
    "Karim Saleh",
    "Hana Farouk",
    "Tariq Abbas",
    "Sara Mahmoud",
]

HEALTH_STATUSES = ["healthy", "healthy", "healthy", "monitoring", "recovering"]
PALM_STATUSES = ["active", "active", "active", "active", "inactive"]


def _placeholder_jpeg(*, label: str, hue: float) -> bytes:
    """Generate a simple labeled JPEG so MinIO/S3 gets real image bytes."""
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 0.45, 0.75)
    color = (int(r * 255), int(g * 255), int(b * 255))
    image = Image.new("RGB", (960, 720), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 920, 160), fill=(20, 40, 20))
    draw.text((60, 70), label, fill=(255, 255, 255))
    draw.text((60, 200), "Palms seed image", fill=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the existing-seed marker check (fails if marker palm already exists).",
    )
    args = parser.parse_args()

    settings = get_settings()
    database = Database(settings)
    storage = build_storage_client(settings)
    storage.ensure_bucket()
    email_service = EmailService(settings)
    executor = SynchronousReportExecutor(storage, email_service)

    session = database.session_factory()
    try:
        seed_system_rbac(session)

        existing = session.scalar(select(Palm.id).where(Palm.code == SEED_MARKER_CODE))
        if existing is not None:
            if args.force:
                raise SystemExit(
                    f"Seed marker {SEED_MARKER_CODE} already exists. "
                    "Delete seeded data (or use a fresh DB) before re-seeding."
                )
            print("Full demo seed already present; skipping.")
            session.commit()
            return

        actor_id = session.scalar(select(User.id).order_by(User.created_at).limit(1))

        sections = [
            Section(
                name="North Orchard",
                description="Seeded north orchard with drip irrigation.",
                location_name="Lifemaker Farm North",
                soil_type="Sandy loam",
                irrigation_type="Drip",
                gps_latitude=Decimal("24.7136000"),
                gps_longitude=Decimal("46.6753000"),
            ),
            Section(
                name="South Grove",
                description="Seeded south grove with sprinkler irrigation.",
                location_name="Lifemaker Farm South",
                soil_type="Clay loam",
                irrigation_type="Sprinkler",
                gps_latitude=Decimal("24.6901000"),
                gps_longitude=Decimal("46.7102000"),
            ),
        ]
        session.add_all(sections)
        session.flush()

        donors: list[Donor] = []
        for index, name in enumerate(DONOR_NAMES[:DONOR_COUNT], start=1):
            donors.append(
                Donor(
                    full_name=name,
                    phone=f"+96650{1000000 + index:07d}"[:16],
                    email=f"seed-donor-{index:02d}@example.com",
                    address=f"District {index}, Riyadh, Saudi Arabia",
                    donation_date=date(2018, 1, 1) + timedelta(days=40 * index),
                    notes=f"Seeded donor #{index} for demo datasets.",
                )
            )
        session.add_all(donors)
        session.flush()

        palms: list[Palm] = []
        for index in range(1, PALM_COUNT + 1):
            donor = donors[(index - 1) % DONOR_COUNT]
            section = sections[(index - 1) % len(sections)]
            palm = Palm(
                code=f"SEED-PALM-{index:03d}",
                donor_id=donor.id,
                section_id=section.id,
                plantation_date=date(2019, 1, 1) + timedelta(days=45 * index),
                status=PALM_STATUSES[(index - 1) % len(PALM_STATUSES)],
                current_health_status=HEALTH_STATUSES[(index - 1) % len(HEALTH_STATUSES)],
                description=f"Seeded demonstration palm #{index}.",
            )
            palms.append(palm)
        session.add_all(palms)
        session.flush()

        # Parent/child sample + harvests on the first few palms
        session.add(
            PalmRelationship(
                parent_palm_id=palms[0].id,
                child_palm_id=palms[1].id,
                relationship_type="parent_child",
            )
        )
        for palm in palms[:5]:
            session.add(
                HarvestRecord(
                    palm_id=palm.id,
                    harvest_date=utcnow().date() - timedelta(days=30),
                    amount=Decimal("100.00") + Decimal(palm.code[-3:]),
                    unit="kg",
                    revenue=Decimal("700.00"),
                    notes="Seed harvest sample.",
                    created_by_user_id=actor_id,
                )
            )

        print(f"Uploading images for {len(palms)} palms...")
        for index, palm in enumerate(palms, start=1):
            content = _placeholder_jpeg(label=palm.code, hue=index / PALM_COUNT)
            variants = process_and_store_image(
                content=content,
                original_filename=f"{palm.code.lower()}.jpg",
                prefix=f"palms/{palm.id}",
                storage=storage,
                settings=settings,
            )
            session.add(
                PalmImage(
                    palm_id=palm.id,
                    storage_key=variants.storage_key,
                    thumbnail_key=variants.thumbnail_key,
                    medium_key=variants.medium_key,
                    webp_key=variants.webp_key,
                    thumbnail_url=variants.thumbnail_url,
                    medium_url=variants.medium_url,
                    full_url=variants.full_url,
                    webp_url=variants.webp_url,
                    uploaded_by_user_id=actor_id,
                    captured_at=utcnow() - timedelta(days=index),
                    metadata_json=variants.metadata,
                )
            )
        session.flush()

        palm_fields = list(REPORT_FIELDS["palms"])
        donor_fields = list(REPORT_FIELDS["donors"])

        palms_template = ReportTemplate(
            name="Seed Palms Inventory",
            report_type="palms",
            fields_json=palm_fields,
            filters_json={"status": "active"},
            created_by_user_id=actor_id,
        )
        donors_template = ReportTemplate(
            name="Seed Donors Roster",
            report_type="donors",
            fields_json=donor_fields,
            filters_json=None,
            created_by_user_id=actor_id,
        )
        session.add_all([palms_template, donors_template])
        session.flush()

        daily_values = {
            "frequency": "daily",
            "run_time": "08:00",
            "timezone": "Asia/Riyadh",
            "format": "csv",
            "cron_expression": None,
            "day_of_month": None,
            "weekday": None,
        }
        weekly_values = {
            "frequency": "weekly",
            "run_time": "09:30",
            "timezone": "Asia/Riyadh",
            "format": "pdf",
            "cron_expression": None,
            "day_of_month": None,
            "weekday": 0,  # Monday
        }

        daily_schedule = ReportSchedule(
            name="Seed Daily Palms Report",
            report_type="palms",
            template_id=palms_template.id,
            frequency=daily_values["frequency"],
            run_time=daily_values["run_time"],
            timezone=daily_values["timezone"],
            format=daily_values["format"],
            fields_json=palm_fields,
            filters_json={"status": "active"},
            email_subject="Daily seeded palms report",
            include_summary=True,
            attach_file=True,
            enabled=True,
            next_run_at=next_run_at(daily_values),
            created_by_user_id=actor_id,
        )
        weekly_schedule = ReportSchedule(
            name="Seed Weekly Donors Report",
            report_type="donors",
            template_id=donors_template.id,
            frequency=weekly_values["frequency"],
            run_time=weekly_values["run_time"],
            timezone=weekly_values["timezone"],
            format=weekly_values["format"],
            weekday=weekly_values["weekday"],
            fields_json=donor_fields,
            filters_json=None,
            email_subject="Weekly seeded donors report",
            include_summary=True,
            attach_file=True,
            enabled=True,
            next_run_at=next_run_at(weekly_values),
            created_by_user_id=actor_id,
        )
        daily_schedule.recipients = [
            ReportScheduleRecipient(email="reports@example.com"),
            ReportScheduleRecipient(email="seed-donor-01@example.com"),
        ]
        weekly_schedule.recipients = [
            ReportScheduleRecipient(email="reports@example.com"),
        ]
        session.add_all([daily_schedule, weekly_schedule])
        session.flush()

        # Materialize completed report runs now (in-process scheduler handles future due runs)
        palms_run = ReportRun(
            schedule=daily_schedule,
            report_type="palms",
            format="csv",
            fields_json=palm_fields,
            filters_json={"status": "active"},
            status="queued",
            requested_by_user_id=actor_id,
        )
        donors_run = ReportRun(
            schedule=weekly_schedule,
            report_type="donors",
            format="pdf",
            fields_json=donor_fields,
            filters_json=None,
            status="queued",
            requested_by_user_id=actor_id,
        )
        session.add_all([palms_run, donors_run])
        session.flush()

        executor.submit(session, palms_run)
        executor.submit(session, donors_run)

        daily_schedule.last_run_at = utcnow()
        weekly_schedule.last_run_at = utcnow()

        session.commit()
        print(
            "Seeded "
            f"{DONOR_COUNT} donors, {PALM_COUNT} palms with images, "
            "2 report templates, 2 schedules, and 2 report runs."
        )
        print(f"Marker palm: {SEED_MARKER_CODE}")
        print(
            f"Schedules next runs: "
            f"{daily_schedule.name} @ {daily_schedule.next_run_at}, "
            f"{weekly_schedule.name} @ {weekly_schedule.next_run_at}"
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        database.dispose()


if __name__ == "__main__":
    main()
