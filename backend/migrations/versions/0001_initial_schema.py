"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-16

The baseline migration creates every table from the current SQLAlchemy metadata. Later schema
changes should be generated with ``alembic revision --autogenerate -m "describe change"``.
"""
from alembic import op

from app import models  # noqa: F401
from app.database import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
