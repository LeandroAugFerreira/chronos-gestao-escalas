"""Chronos 1.0 — calendário, versões normativas e avaliações imutáveis."""
from uuid import NAMESPACE_URL, uuid5
from alembic import op
import sqlalchemy as sa

revision = "006_calendar_rules"
down_revision = "005_catalog_revisions"
branch_labels = None
depends_on = None


def common():
    return [sa.Column("id", sa.String(36), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False), sa.UniqueConstraint("organization_id", "id")]


def ref(column, table):
    return sa.ForeignKeyConstraint(["organization_id", column], [table + ".organization_id", table + ".id"])


def upgrade():
    op.add_column("work_patterns", sa.Column("configuration", sa.JSON(), server_default="{}", nullable=False))
    op.create_table("labor_rules", *common(), sa.Column("key", sa.String(80), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("supersedes_id", sa.String(36)), ref("supersedes_id", "labor_rules"), sa.UniqueConstraint("organization_id", "supersedes_id"),
        sa.Column("kind", sa.String(40), nullable=False), sa.Column("minutes", sa.Integer(), nullable=False), sa.Column("threshold_minutes", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.String(36)), sa.Column("job_role_id", sa.String(36)), sa.Column("contract_id", sa.String(36)),
        sa.Column("agreement", sa.String(200), nullable=False), sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False), sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("review_evidence", sa.Text(), nullable=False), sa.Column("reviewer_id", sa.String(36)),
        ref("unit_id", "units"), ref("job_role_id", "job_roles"), ref("contract_id", "contracts"), ref("reviewer_id", "users"),
        sa.UniqueConstraint("organization_id", "key", "version"), sa.CheckConstraint("version > 0 AND minutes >= 0 AND threshold_minutes >= 0", name="positive_parameters"),
        sa.CheckConstraint("valid_until > valid_from", name="valid_interval"), sa.CheckConstraint("status IN ('pending_review','validated')", name="valid_status"))
    op.create_table("calendar_shifts", *common(), sa.Column("employee_id", sa.String(36), nullable=False), sa.Column("unit_id", sa.String(36), nullable=False), sa.Column("department_id", sa.String(36), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False), sa.Column("end_at", sa.DateTime(timezone=True), nullable=False), sa.Column("breaks", sa.JSON(), nullable=False),
        sa.Column("label", sa.String(80), nullable=False), sa.Column("state", sa.String(16), nullable=False), sa.Column("revision", sa.Integer(), nullable=False), sa.Column("evaluation", sa.JSON(), nullable=False),
        ref("employee_id", "employees"), ref("unit_id", "units"), sa.ForeignKeyConstraint(["organization_id", "unit_id", "department_id"], ["departments.organization_id", "departments.unit_id", "departments.id"]),
        sa.CheckConstraint("end_at > start_at", name="positive_interval"), sa.CheckConstraint("state IN ('draft','cancelled')", name="valid_state"))
    op.create_index("ix_calendar_shifts_scope", "calendar_shifts", ["organization_id", "unit_id", "start_at"])
    op.create_table("schedule_evaluations", *common(), sa.Column("shift_id", sa.String(36), nullable=False), sa.Column("actor_id", sa.String(36), nullable=False),
        sa.Column("shift_revision", sa.Integer(), nullable=False), sa.Column("snapshot", sa.JSON(), nullable=False), ref("shift_id", "calendar_shifts"), ref("actor_id", "users"))
    for table in ["labor_rules", "calendar_shifts", "schedule_evaluations"]:
        op.create_index("ix_" + table + "_organization_id", table, ["organization_id"])
    # IDs determinísticos iguais ao provisionamento. Não depender do código futuro.
    connection = op.get_bind()
    for code, roles in {"schedule:read": ["admin", "hr", "manager"], "schedule:write": ["admin", "hr", "manager"], "rules:read": ["admin", "hr", "manager", "analyst"], "rules:write": ["admin", "hr"]}.items():
        pid = str(uuid5(NAMESPACE_URL, "chronos/permission/" + code))
        connection.execute(sa.text("INSERT INTO permissions (id, created_at, code) VALUES (:id, CURRENT_TIMESTAMP, :code)"), {"id": pid, "code": code})
        for role in roles:
            connection.execute(sa.text("INSERT INTO role_permissions (role_id, permission_id) SELECT id, :pid FROM roles WHERE name = :role"), {"pid": pid, "role": role})


def downgrade():
    connection = op.get_bind()
    for code in ["schedule:read", "schedule:write", "rules:read", "rules:write"]:
        pid = str(uuid5(NAMESPACE_URL, "chronos/permission/" + code))
        connection.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :id"), {"id": pid})
        connection.execute(sa.text("DELETE FROM permissions WHERE id = :id"), {"id": pid})
    for table in ["schedule_evaluations", "calendar_shifts", "labor_rules"]:
        op.drop_table(table)
    op.drop_column("work_patterns", "configuration")
