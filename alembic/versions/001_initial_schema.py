"""
Initial database schema

Creates:
- historical_reports table with all columns and indexes
- pollutant_readings table with foreign key and indexes

Revision ID: 001
Revises:
Create Date: 2026-06-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "historical_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.String(50), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("accuracy_meters", sa.Float(), nullable=True),
        sa.Column("aqi_value", sa.Integer(), nullable=False),
        sa.Column("smoke_percentage", sa.Float(), nullable=False),
        sa.Column("primary_pollutant", sa.String(20), nullable=False),
        sa.Column("risk_level", sa.String(50), nullable=False),
        sa.Column("image_filename", sa.String(255), nullable=True),
        sa.Column("image_width", sa.Integer(), nullable=True),
        sa.Column("image_height", sa.Integer(), nullable=True),
        sa.Column("image_metadata", sa.JSON(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("humidity", sa.Float(), nullable=True),
        sa.Column("pressure", sa.Float(), nullable=True),
        sa.Column("wind_speed", sa.Float(), nullable=True),
        sa.Column("visibility", sa.Float(), nullable=True),
        sa.Column("health_recommendation", sa.Text(), nullable=True),
        sa.Column("risk_assessment", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("affected_groups", sa.JSON(), nullable=True),
        sa.Column("comparison_historical", sa.JSON(), nullable=True),
        sa.Column("trend", sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id"),
    )

    op.create_index(op.f("ix_historical_reports_id"), "historical_reports", ["id"], unique=False)
    op.create_index(op.f("ix_historical_reports_report_id"), "historical_reports", ["report_id"], unique=True)
    op.create_index(op.f("ix_historical_reports_timestamp"), "historical_reports", ["timestamp"], unique=False)
    op.create_index(op.f("ix_historical_reports_aqi_value"), "historical_reports", ["aqi_value"], unique=False)
    op.create_index("idx_location", "historical_reports", ["latitude", "longitude"], unique=False)
    op.create_index("idx_timestamp_location", "historical_reports", ["timestamp", "latitude", "longitude"], unique=False)
    op.create_index("idx_aqi_date", "historical_reports", ["aqi_value", "timestamp"], unique=False)
    op.create_index("idx_city_date", "historical_reports", ["city", "timestamp"], unique=False)

    op.create_table(
        "pollutant_readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("pollutant_type", sa.String(20), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("aqi_index", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["historical_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_pollutant_readings_id"), "pollutant_readings", ["id"], unique=False)
    op.create_index(op.f("ix_pollutant_readings_report_id"), "pollutant_readings", ["report_id"], unique=False)
    op.create_index(op.f("ix_pollutant_readings_pollutant_type"), "pollutant_readings", ["pollutant_type"], unique=False)
    op.create_index("idx_pollutant_report", "pollutant_readings", ["report_id", "pollutant_type"], unique=False)
    op.create_index("idx_pollutant_type", "pollutant_readings", ["pollutant_type"], unique=False)


def downgrade() -> None:
    op.drop_table("pollutant_readings")
    op.drop_table("historical_reports")
