"""Establish the initial Alembic baseline before domain tables are introduced."""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260718_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Record the baseline; this foundation intentionally owns no domain tables."""
    pass


def downgrade() -> None:
    """Return to an unversioned empty schema."""
    pass
