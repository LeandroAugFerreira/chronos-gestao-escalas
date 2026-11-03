"""Chronos 1.0 — revisão otimista nos catálogos da Fase 3."""
from alembic import op
import sqlalchemy as sa

revision = "005_catalog_revisions"
down_revision = "004_idempotency"
branch_labels = None
depends_on = None


def upgrade():
    for table in ["job_roles", "skills", "qualifications"]:
        op.add_column(table, sa.Column("revision", sa.Integer(), server_default="1", nullable=False))


def downgrade():
    for table in ["qualifications", "skills", "job_roles"]:
        op.drop_column(table, "revision")
