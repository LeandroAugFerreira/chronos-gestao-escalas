from uuid import uuid4

from app.models.entities import AuditLog


def audit(session, org, actor, action, entity, entity_id, correlation=None, details=None):
    # Nunca guardar senhas/tokens, payload integral de pessoas ou credenciais de banco.
    row = AuditLog(id=str(uuid4()), organization_id=org, actor_id=actor, action=action,
                         entity_type=entity, entity_id=entity_id,
                         correlation_id=correlation or str(uuid4()), details=details or {})
    session.add(row)
    from app.services.automation_events import publish_audit
    publish_audit(session, row)
