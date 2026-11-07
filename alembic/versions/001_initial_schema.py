"""Initial schema for HydroCast Panchganga database

Revision: 001
Revises:
Create Date: 2026-11-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Create subbasins table
    op.create_table(
        "subbasins",
        sa.Column("subbasin_id", sa.VARCHAR(32), nullable=False),
        sa.Column("subbasin_name", sa.VARCHAR(100), nullable=False),
        sa.Column("drainage_area_km2", sa.NUMERIC(8, 3), nullable=False),
        sa.Column("primary_station_id", sa.VARCHAR(64), nullable=False),
        sa.Column("centroid_lat", sa.NUMERIC(8, 4), nullable=False),
        sa.Column("centroid_lon", sa.NUMERIC(8, 4), nullable=False),
        sa.Column("tributary_stream", sa.VARCHAR(100), nullable=False),
        sa.Column("curve_number_amc3", sa.NUMERIC(4, 1), nullable=False, server_default="88.0"),
        sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("subbasin_id"),
    )

    # Create gauge_stations table
    op.create_table(
        "gauge_stations",
        sa.Column("station_id", sa.VARCHAR(64), nullable=False),
        sa.Column("station_name", sa.VARCHAR(100), nullable=False),
        sa.Column("subbasin_id", sa.VARCHAR(64), nullable=False),
        sa.Column("latitude", sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column("longitude", sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column("elevation_m", sa.NUMERIC(6, 1)),
        sa.Column("is_primary", sa.BOOLEAN(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.BOOLEAN(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("station_id"),
        sa.ForeignKeyConstraint(["subbasin_id"], ["subbasins.subbasin_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_gs_subbasin", "gauge_stations", ["subbasin_id"])

    # Create bridge_sites table
    op.create_table(
        "bridge_sites",
        sa.Column("site_id", sa.VARCHAR(50), nullable=False),
        sa.Column("site_name", sa.VARCHAR(100), nullable=False),
        sa.Column("latitude", sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column("longitude", sa.DOUBLE_PRECISION(), nullable=False),
        sa.Column("river_name", sa.VARCHAR(100), nullable=False, server_default="Panchganga"),
        sa.Column("alert_stage_m", sa.NUMERIC(6, 2), nullable=False),
        sa.Column("warning_stage_m", sa.NUMERIC(6, 2), nullable=False),
        sa.Column("danger_stage_m", sa.NUMERIC(6, 2), nullable=False),
        sa.Column("hfl_m", sa.NUMERIC(6, 2), nullable=False),
        sa.Column("bed_slope", sa.NUMERIC(8, 6), nullable=False),
        sa.Column("zero_datum_m", sa.NUMERIC(6, 2), nullable=False, server_default="530.18"),
        sa.Column("sensor_datum_m", sa.NUMERIC(6, 2), nullable=False, server_default="549.35"),
        sa.Column("manning_n_bed", sa.NUMERIC(4, 3), nullable=False, server_default="0.035"),
        sa.Column("manning_n_floodplain", sa.NUMERIC(4, 3), nullable=False, server_default="0.070"),
        sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("site_id"),
    )

    # Create simulation_runs table
    op.create_table(
        "simulation_runs",
        sa.Column("run_id", sa.VARCHAR(100), nullable=False),
        sa.Column("cycle_date", sa.DATE(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("cycle_time", sa.VARCHAR(32), nullable=False, server_default="00z"),
        sa.Column("start_time", sa.TIMESTAMPTZ(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("end_time", sa.TIMESTAMPTZ(), nullable=True),
        sa.Column("status", sa.VARCHAR(32), nullable=False, server_default="completed"),
        sa.Column("model_version", sa.VARCHAR(64), nullable=False, server_default="HEC-HMS-4.13"),
        sa.Column("peak_discharge_m3s", sa.NUMERIC(10, 2)),
        sa.Column("peak_stage_m", sa.NUMERIC(6, 2)),
        sa.Column("lead_hours_to_peak", sa.SMALLINT()),
        sa.Column("total_volume_mcm", sa.NUMERIC(10, 2)),
        sa.Column("total_rainfall_mm", sa.NUMERIC(8, 2)),
        sa.Column("total_rainfall_volume_mcm", sa.NUMERIC(10, 2)),
        sa.Column("alert_level", sa.VARCHAR(32), nullable=False, server_default="NORMAL"),
        sa.Column("spearman_rho", sa.NUMERIC(6, 4)),
        sa.Column("nse_score", sa.NUMERIC(6, 4)),
        sa.Column("error_message", sa.TEXT()),
        sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("idx_sim_runs_date", "simulation_runs", ["cycle_date", "start_time"])

    # Create forecast_validation_metrics table
    op.create_table(
        "forecast_validation_metrics",
        sa.Column("id", sa.BIGSERIAL(), nullable=False),
        sa.Column("run_id", sa.VARCHAR(100), nullable=False),
        sa.Column("spearman_rho", sa.NUMERIC(6, 4), nullable=False),
        sa.Column("spearman_rho_q", sa.NUMERIC(6, 4), nullable=False),
        sa.Column("pearson_r2", sa.NUMERIC(6, 4), nullable=False),
        sa.Column("nse_stage", sa.NUMERIC(6, 4), nullable=False),
        sa.Column("nse_discharge", sa.NUMERIC(6, 4), nullable=False),
        sa.Column("rmse_stage_m", sa.NUMERIC(6, 4), nullable=False),
        sa.Column("mae_stage_m", sa.NUMERIC(6, 4), nullable=False),
        sa.Column("rmse_q_m3s", sa.NUMERIC(8, 2)),
        sa.Column("mae_q_m3s", sa.NUMERIC(8, 2)),
        sa.Column("pbias_stage_pct", sa.NUMERIC(6, 2), nullable=False),
        sa.Column("pbias_discharge_pct", sa.NUMERIC(6, 2)),
        sa.Column("basin_rainfall_accuracy_pct", sa.NUMERIC(5, 2), nullable=False),
        sa.Column("performance_grade", sa.VARCHAR(32), nullable=False, server_default="EXCELLENT"),
        sa.Column("sample_size_hours", sa.SMALLINT(), nullable=False, server_default="48"),
        sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["simulation_runs.run_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_fvm_run", "forecast_validation_metrics", ["run_id"])

    # Create hydrograph_results table
    op.create_table(
        "hydrograph_results",
        sa.Column("id", sa.BIGSERIAL(), nullable=False),
        sa.Column("run_id", sa.VARCHAR(100), nullable=False),
        sa.Column("basin_id", sa.VARCHAR(50), nullable=False, server_default="PANCHGANGA_BASIN"),
        sa.Column("outlet_node", sa.VARCHAR(50), nullable=False, server_default="J_Outlet"),
        sa.Column("timestamp", sa.TIMESTAMPTZ(), nullable=False),
        sa.Column("lead_hours", sa.SMALLINT(), nullable=False),
        sa.Column("discharge_m3s", sa.NUMERIC(10, 2), nullable=False),
        sa.Column("surface_runoff_m3s", sa.NUMERIC(10, 2), nullable=False, server_default="0"),
        sa.Column("baseflow_m3s", sa.NUMERIC(10, 2), nullable=False, server_default="45.0"),
        sa.Column("is_peak", sa.BOOLEAN(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["simulation_runs.run_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_hg_run_lead", "hydrograph_results", ["run_id", "lead_hours"])
    op.create_index("idx_hg_timestamp", "hydrograph_results", ["timestamp"])

    # Create bridge_stage_forecast table
    op.create_table(
        "bridge_stage_forecast",
        sa.Column("id", sa.BIGSERIAL(), nullable=False),
        sa.Column("site_id", sa.VARCHAR(50), nullable=False),
        sa.Column("forecast_run_id", sa.VARCHAR(100), nullable=False),
        sa.Column("forecast_time", sa.TIMESTAMPTZ(), nullable=False),
        sa.Column("lead_hours", sa.SMALLINT(), nullable=False),
        sa.Column("discharge_m3s", sa.NUMERIC(10, 2), nullable=False),
        sa.Column("stage_m", sa.NUMERIC(6, 2), nullable=False),
        sa.Column(
            "alert_level",
            sa.VARCHAR(32),
            nullable=False,
            server_default="'NORMAL'",
        ),
        sa.Column("is_above_danger", sa.BOOLEAN(), nullable=False, server_default="false"),
        sa.Column("arrival_time", sa.TIMESTAMPTZ()),
        sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["site_id"], ["bridge_sites.site_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["forecast_run_id"], ["simulation_runs.run_id"], ondelete="CASCADE"
        ),
    )
    op.create_index("idx_bsf_site_run", "bridge_stage_forecast", ["site_id", "forecast_run_id"])

    # Create wrd_field_benchmarks table
    op.create_table(
        "wrd_field_benchmarks",
        sa.Column("record_id", sa.BIGSERIAL(), nullable=False),
        sa.Column("stage_m", sa.NUMERIC(6, 2), nullable=False),
        sa.Column("stage_feet_inches", sa.VARCHAR(32), nullable=False),
        sa.Column("discharge_cusecs", sa.NUMERIC(10, 1), nullable=False),
        sa.Column("discharge_m3s", sa.NUMERIC(10, 2), nullable=False),
        sa.Column(
            "source_agency",
            sa.VARCHAR(100),
            nullable=False,
            server_default="Maharashtra Water Resources Dept (WRD)",
        ),
        sa.Column("is_danger_threshold", sa.BOOLEAN(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("record_id"),
    )

    # Create pipeline_step_log table
    op.create_table(
        "pipeline_step_log",
        sa.Column("cycle_id", sa.VARCHAR(100), nullable=False),
        sa.Column("step_number", sa.SMALLINT(), nullable=False),
        sa.Column("step_name", sa.VARCHAR(256), nullable=False),
        sa.Column("status", sa.VARCHAR(32), nullable=False, server_default="running"),
        sa.Column("start_time", sa.TIMESTAMPTZ(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("end_time", sa.TIMESTAMPTZ(), nullable=True),
        sa.Column("duration_seconds", sa.NUMERIC(10, 2)),
        sa.Column("details_json", sa.JSONB()),
        sa.Column("error_message", sa.TEXT()),
        sa.PrimaryKeyConstraint("cycle_id", "step_number"),
    )
    op.create_index("idx_pipeline_step_log_cycle_id", "pipeline_step_log", ["cycle_id"])

    # Create visitor_counts table
    op.create_table(
        "visitor_counts",
        sa.Column("visit_date", sa.DATE(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("unique_visitors", sa.INTEGER(), nullable=False, server_default="1"),
        sa.Column("total_pageviews", sa.INTEGER(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.TIMESTAMPTZ(), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("visit_date"),
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""

    op.drop_table("visitor_counts")
    op.drop_table("pipeline_step_log")
    op.drop_table("wrd_field_benchmarks")
    op.drop_table("bridge_stage_forecast")
    op.drop_table("hydrograph_results")
    op.drop_table("forecast_validation_metrics")
    op.drop_table("simulation_runs")
    op.drop_table("bridge_sites")
    op.drop_table("gauge_stations")
    op.drop_table("subbasins")

    # Drop PostGIS extension
    op.execute("DROP EXTENSION IF EXISTS postgis")