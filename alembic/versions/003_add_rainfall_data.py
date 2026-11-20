"""Create rainfall_data telemetry table (gauge hyetograph storage)

Revision: 003
Revises: 002
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the rainfall telemetry table consumed by /api/v1/rainfall/gauges."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rainfall_data (
            gauge_id VARCHAR(64) NOT NULL,
            subbasin_id VARCHAR(32) NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            rainfall_mm DOUBLE PRECISION NOT NULL DEFAULT 0,
            quality_flag VARCHAR(32) NOT NULL DEFAULT 'OK',
            PRIMARY KEY (gauge_id, timestamp)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rainfall_data")
