"""Add composite index on forecast_run_id for high-speed dashboard lookups

Revision: 002
Revises: 001
Create Date: 2026-11-13
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add leading index on forecast_run_id to bridge_stage_forecast and hydrograph_results."""
    op.create_index(
        "idx_bsf_run_site_lead",
        "bridge_stage_forecast",
        ["forecast_run_id", "site_id", "lead_hours"],
        if_not_exists=True,
    )


def downgrade() -> None:
    """Drop the composite index."""
    op.drop_index("idx_bsf_run_site_lead", table_name="bridge_stage_forecast")

