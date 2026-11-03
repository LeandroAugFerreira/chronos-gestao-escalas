"""Bounded export of the basic people directory; no financial/professional joins."""
import base64
from datetime import UTC, datetime
import hashlib
from uuid import uuid4

from app.api.dependencies import fail
from app.repositories.people import employee_query
from app.services.audit import audit
from app.services.csv_export import csv_bytes

MAX_ROWS = 20000
MAX_BYTES = 8 * 1024 * 1024
COLUMNS = ("id", "organization_id", "unit_id", "department_id", "job_role_id",
           "name", "registration", "status", "synthetic", "revision")


def export_people(session, principal, selection, correlation):
    extracted_at = datetime.now(UTC).isoformat()
    records = session.scalars(employee_query(principal, **selection.model_dump()).limit(MAX_ROWS + 1)).all()
    if len(records) > MAX_ROWS:
        fail(422, "PEOPLE_EXPORT_LIMIT", "A seleção excede 20.000 colaboradores. Refine os filtros; nenhum arquivo foi gerado.")
    content = csv_bytes(COLUMNS, [{c: getattr(r, c) for c in COLUMNS} for r in records])
    if len(content) > MAX_BYTES:
        fail(422, "PEOPLE_EXPORT_LIMIT", "O arquivo excede 8 MiB. Refine os filtros; nenhum arquivo foi gerado.")
    digest = hashlib.sha256(content).hexdigest()
    export_id = str(uuid4())
    # No search text, names, registrations, salaries, evidence or full payload in audit.
    audit(session, principal.user.organization_id, principal.user.id, "people.export", "people_exports", export_id,
          correlation=correlation, details={"row_count": len(records), "byte_length": len(content), "sha256": digest,
          "unit_id": selection.unit_id, "department_id": selection.department_id, "status": selection.status,
          "sort": selection.sort, "descending": selection.descending, "search_used": bool(selection.search)})
    session.commit()
    return {"product": "Chronos 1.0", "export_id": export_id, "extracted_at": extracted_at,
            "filename": f"chronos-1.0-colaboradores-{digest[:12]}.csv", "content_type": "text/csv;charset=utf-8",
            "encoding": "base64", "content": base64.b64encode(content).decode(), "sha256": digest,
            "byte_length": len(content), "row_count": len(records), "columns": COLUMNS,
            "notice": "Todas as linhas autorizadas da seleção, sem salários, contratos, evidências ou ausências. "
                      "Texto com início de fórmula recebe apóstrofo de proteção. Importe IDs e matrícula como texto. "
                      "O arquivo baixado não mantém o controle de acesso do Chronos; proteja seu armazenamento."}
