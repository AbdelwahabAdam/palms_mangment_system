"""Seed a small demonstration dataset for local Compose smoke tests."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from palms_api.config import get_settings
from palms_api.database import Database
from palms_api.models import (
    Donor,
    HarvestRecord,
    Palm,
    PalmRelationship,
    Section,
    utcnow,
)
from palms_api.seeding import seed_system_rbac


def main() -> None:
    database = Database(get_settings())
    session = database.session_factory()
    try:
        seed_system_rbac(session)

        existing = session.scalar(select(Palm.id).where(Palm.code == "PALM-001"))
        if existing is not None:
            print("Demo data already present; skipping.")
            session.commit()
            return

        donor = Donor(
            full_name="Ahmed Ali",
            phone="+966501234567",
            email="ahmed.ali@example.com",
            address="Riyadh, Saudi Arabia",
            donation_date=date(2020, 3, 15),
            notes="Founding donor for the demonstration orchard.",
        )
        section = Section(
            name="North Section",
            description="Demonstration orchard section with drip irrigation.",
            location_name="Lifemaker Farm North",
            soil_type="Sandy loam",
            irrigation_type="Drip",
            gps_latitude=Decimal("24.7136000"),
            gps_longitude=Decimal("46.6753000"),
        )
        session.add_all([donor, section])
        session.flush()

        parent = Palm(
            code="PALM-001",
            donor_id=donor.id,
            section_id=section.id,
            plantation_date=date(2020, 3, 15),
            status="active",
            current_health_status="healthy",
            description="Flagship demonstration palm.",
        )
        child = Palm(
            code="PALM-002",
            donor_id=donor.id,
            section_id=section.id,
            plantation_date=date(2022, 6, 1),
            status="active",
            current_health_status="healthy",
            description="Offspring of PALM-001.",
        )
        session.add_all([parent, child])
        session.flush()

        session.add(
            PalmRelationship(
                parent_palm_id=parent.id,
                child_palm_id=child.id,
                relationship_type="parent_child",
            )
        )
        session.add(
            HarvestRecord(
                palm_id=parent.id,
                harvest_date=utcnow().date() - timedelta(days=40),
                amount=Decimal("120.50"),
                unit="kg",
                revenue=Decimal("850.00"),
                notes="Spring harvest sample.",
            )
        )
        session.commit()
        print("Seeded donors, sections, palms, relationships, and harvests.")
    finally:
        session.close()
        database.dispose()


if __name__ == "__main__":
    main()
