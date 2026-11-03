"""Reparação conservadora de indisponibilidades da fixture antiga no SQLite."""
from datetime import UTC, datetime
from app.api.dependencies import aware
from app.models.entities import AvailabilityRule
from app.services.audit import audit
from app.services.seed import demo_id


def repair_demo_times(session, org, data, environment):
    if environment not in {"development", "test"} or not org.is_demo or org.id != demo_id("organization") or org.slug != "horizonte":
        raise ValueError("Reparação restrita ao Hospital Horizonte sintético em desenvolvimento/teste")
    result = {"repaired": 0, "already_utc": 0, "not_matched": 0}
    if session.bind.dialect.name != "sqlite":
        return result  # PostgreSQL preserva/converte instantes com fuso.
    from app.services.organization_lock import lock_organization
    lock_organization(session, org.id)
    for source in data["availability_rules"]:
        row = session.get(AvailabilityRule, demo_id(source["id"]))
        if row is None or row.organization_id != org.id or row.employee_id != demo_id(source["employee_id"]) or row.reason != source["reason"] or row.type != source["type"]:
            result["not_matched"] += 1
            continue
        start, end = datetime.fromisoformat(source["start"]), datetime.fromisoformat(source["end"])
        correct = (start.astimezone(UTC), end.astimezone(UTC))
        legacy = (start.replace(tzinfo=UTC), end.replace(tzinfo=UTC))
        stored = (aware(row.start_at), aware(row.end_at))
        if stored == correct:
            result["already_utc"] += 1
        elif stored == legacy:
            row.start_at, row.end_at = correct
            result["repaired"] += 1
            audit(session, org.id, None, "demo.availability.utc_repair", "availability_rules", row.id, details={"fixture_id": source["id"], "repair": "confirmed_legacy_offset_loss"})
        else:
            result["not_matched"] += 1
    session.flush()
    return result
