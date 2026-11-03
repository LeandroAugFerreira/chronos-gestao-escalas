import hashlib
import hmac
import json
import re

from sqlalchemy import select

from app.api.dependencies import fail
from app.models.entities import IdempotencyRecord


def prepare(session, request, principal, model, payload):
    key = request.headers.get("Idempotency-Key")
    if key is None:
        return None, None
    if not re.fullmatch(r"[a-zA-Z0-9._:-]{8,128}", key):
        fail(422, "INVALID_IDEMPOTENCY_KEY", "Use uma chave opaca de 8 a 128 caracteres.")
    secret = request.app.state.settings.jwt_secret.get_secret_value().encode()
    key_hash = hmac.new(secret, key.encode(), hashlib.sha256).hexdigest()
    digest = hmac.new(secret, json.dumps(payload, sort_keys=True, default=str).encode(), hashlib.sha256).hexdigest()
    record = session.scalar(select(IdempotencyRecord).where(IdempotencyRecord.organization_id == principal.user.organization_id,
        IdempotencyRecord.actor_id == principal.user.id, IdempotencyRecord.route == request.url.path, IdempotencyRecord.key_hash == key_hash))
    if record:
        if record.payload_hash != digest or record.entity_type != model.__tablename__:
            fail(409, "IDEMPOTENCY_CONFLICT", "Esta chave já foi usada com outro conteúdo.")
        row = session.scalar(select(model).where(model.id == record.entity_id, model.organization_id == principal.user.organization_id))
        if row is None:
            fail(409, "IDEMPOTENCY_EXPIRED", "O registro original não está mais disponível.")
        request.state.idempotent_replay = True
        return row, None
    return None, {"organization_id": principal.user.organization_id, "actor_id": principal.user.id,
        "route": request.url.path, "key_hash": key_hash, "payload_hash": digest, "entity_type": model.__tablename__}


def record(session, pending, entity_id):
    if pending:
        session.add(IdempotencyRecord(entity_id=entity_id, **pending))
