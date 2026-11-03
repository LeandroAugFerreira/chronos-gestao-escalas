"""Chronos 1.0 — cenários e simulações financeiras imutáveis."""
from uuid import NAMESPACE_URL, uuid5
from alembic import op
import sqlalchemy as sa

revision = "007_scenarios_finance"
down_revision = "006_calendar_rules"
branch_labels = None
depends_on = None


def common():
    return [sa.Column("id", sa.String(36), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False), sa.UniqueConstraint("organization_id", "id")]


def ref(column, table):
    return sa.ForeignKeyConstraint(["organization_id", column], [table + ".organization_id", table + ".id"])


def upgrade():
    op.create_table("scenario_versions", *common(), sa.Column("unit_id", sa.String(36), nullable=False), sa.Column("department_id", sa.String(36)),
        sa.Column("actor_id", sa.String(36), nullable=False), sa.Column("key", sa.String(80), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.String(36)), sa.Column("name", sa.String(160), nullable=False), sa.Column("reference_month", sa.Date(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False), sa.Column("capacity", sa.JSON(), nullable=False), sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("payroll_snapshot", sa.JSON(), nullable=False), sa.Column("digest", sa.String(64), nullable=False),
        ref("unit_id", "units"), ref("actor_id", "users"), ref("parent_id", "scenario_versions"),
        sa.ForeignKeyConstraint(["organization_id", "unit_id", "department_id"], ["departments.organization_id", "departments.unit_id", "departments.id"]),
        sa.UniqueConstraint("organization_id", "key", "version"), sa.UniqueConstraint("organization_id", "unit_id", "id"), sa.CheckConstraint("version > 0", name="positive_version"))
    op.create_table("financial_runs", *common(), sa.Column("unit_id", sa.String(36), nullable=False), sa.Column("scenario_id", sa.String(36), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False), sa.Column("digest", sa.String(64), nullable=False), ref("unit_id", "units"), ref("actor_id", "users"),
        sa.ForeignKeyConstraint(["organization_id", "unit_id", "scenario_id"], ["scenario_versions.organization_id", "scenario_versions.unit_id", "scenario_versions.id"]))
    for table in ["scenario_versions", "financial_runs"]:
        op.create_index("ix_" + table + "_organization_id", table, ["organization_id"])
    connection = op.get_bind()
    for code, roles in {"scenario:read": ["admin", "hr", "manager", "analyst", "finance"], "scenario:write": ["admin", "hr", "manager", "analyst"], "finance:simulate": ["admin", "hr", "finance"]}.items():
        pid = str(uuid5(NAMESPACE_URL, "chronos/permission/" + code))
        connection.execute(sa.text("INSERT INTO permissions (id, created_at, code) VALUES (:id, CURRENT_TIMESTAMP, :code)"), {"id": pid, "code": code})
        for role in roles:
            connection.execute(sa.text("INSERT INTO role_permissions (role_id, permission_id) SELECT id, :pid FROM roles WHERE name = :role"), {"pid": pid, "role": role})


def downgrade():
    connection = op.get_bind()
    for code in ["scenario:read", "scenario:write", "finance:simulate"]:
        pid = str(uuid5(NAMESPACE_URL, "chronos/permission/" + code))
        connection.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :id"), {"id": pid})
        connection.execute(sa.text("DELETE FROM permissions WHERE id = :id"), {"id": pid})
    op.drop_table("financial_runs")
    op.drop_table("scenario_versions")
