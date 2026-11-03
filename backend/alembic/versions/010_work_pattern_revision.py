"""Chronos 1.0 — persist the work-pattern review revision already used by the API."""
from alembic import op
import sqlalchemy as sa

revision = "010_pattern_revision"
down_revision = "009_automations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("work_patterns", sa.Column("revision", sa.Integer(), server_default="1", nullable=False))


def downgrade():
    op.drop_column("work_patterns", "revision")
