"""Deterministic A01–A07 handlers. Effects commit together with their execution."""
import csv
import hashlib
import io
from datetime import timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import or_, select, func
from app.api.dependencies import aware, principal_for_user
from app.models import entities as m
from app.services.automation_events import CODE_PERMISSIONS
from app.services.optimization_snapshot import capture, signed


class AutomationError(Exception):
    def __init__(self, code, transient=False):
        super().__init__(code)
        self.code, self.transient = code, transient


def owner_principal(session, definition):
    user = session.get(m.User, definition.owner_id) if definition.owner_id else None
    if not user or not user.active or user.organization_id != definition.organization_id:
        raise AutomationError("OWNER_UNAVAILABLE")
    principal = principal_for_user(session, user)
    if not all(principal.permits(p, definition.unit_id) for p in ["automation:run", CODE_PERMISSIONS[definition.code]]):
        raise AutomationError("OWNER_PERMISSION_REVOKED")
    return principal


def rows(session, query, limit):
    found = session.scalars(query.limit(limit + 1)).all()
    return found[:limit], len(found) > limit


def notice(session, definition, key, title, body, entity_type, entity_id, recipient=None, severity="warning"):
    key = hashlib.sha256((definition.unit_id + ":" + key).encode()).hexdigest()
    existing = session.scalar(select(m.AutomationNotice).where(m.AutomationNotice.organization_id == definition.organization_id, m.AutomationNotice.dedupe_key == key))
    if existing:
        return existing
    row = m.AutomationNotice(organization_id=definition.organization_id, unit_id=definition.unit_id, definition_id=definition.id,
        recipient_id=recipient, code=definition.code, dedupe_key=key, severity=severity, title=title, body=body, entity_type=entity_type, entity_id=entity_id)
    session.add(row); session.flush()
    return row


def unit_runs(session, definition, limit):
    return rows(session, select(m.OptimizationRun).where(m.OptimizationRun.organization_id == definition.organization_id,
        m.OptimizationRun.unit_id == definition.unit_id).order_by(m.OptimizationRun.created_at.desc(), m.OptimizationRun.id), limit)


def apply(session, definition, event, settings):
    principal = owner_principal(session, definition)
    org, unit = definition.organization_id, definition.unit_id
    limit = definition.parameters.get("monitor_limit", 100)
    code = definition.code
    if code == "A01":
        query = select(m.ScheduleVersion).where(m.ScheduleVersion.organization_id == org, m.ScheduleVersion.unit_id == unit,
            m.ScheduleVersion.state.in_(["draft", "submitted", "approved"])).order_by(m.ScheduleVersion.created_at.desc(), m.ScheduleVersion.id)
        schedules, truncated = rows(session, query, min(limit, 10))
        checks = []
        for schedule in schedules:
            run = session.get(m.OptimizationRun, schedule.run_id)
            scenario = session.get(m.ScenarioVersion, run.scenario_id)
            current = signed(capture(session, scenario, run.inputs), settings.jwt_secret.get_secret_value())
            # A newly approved version itself becomes a commitment. Check with its pre-approval commitment set.
            if schedule.state == "approved":
                snapshot = capture(session, scenario, run.inputs)
                snapshot["facts"]["approved_schedules"] = [s for s in snapshot["facts"]["approved_schedules"] if s["id"] != schedule.id]
                if schedule.parent_id:
                    old = session.get(m.ScheduleVersion, schedule.parent_id)
                    prior = next((s for s in run.snapshot["facts"]["approved_schedules"] if s["id"] == schedule.parent_id), None)
                    if prior and old and old.state == "superseded":
                        snapshot["facts"]["approved_schedules"].append(prior)
                        snapshot["facts"]["approved_schedules"].sort(key=lambda s: s["id"])
                current = signed(snapshot, settings.jwt_secret.get_secret_value())
            stale = current != run.input_digest
            checks.append({"schedule_id": schedule.id, "state": schedule.state, "inputs_changed": stale,
                "stored_verification_valid": bool(schedule.verification.get("valid")), "pending": schedule.verification.get("approval_blockers", [])})
            if stale:
                notice(session, definition, "A01:" + schedule.id + ":" + current, "Proposta requer nova avaliação",
                    "Há alterações nos insumos desde o cálculo. A automação não certifica conformidade nem altera a proposta.", "schedule_versions", schedule.id)
        return {"checks": checks, "truncated": truncated, "scope": "Monitoramento de atualidade e verificação armazenada; sem nova certificação jurídica."}
    if code == "A02":
        runs, truncated = unit_runs(session, definition, limit)
        if event.entity_type == "optimization_runs":
            runs = [r for r in runs if r.id == event.entity_id]
        alerts, measured = [], 0
        for run in runs:
            verification = run.result.get("verification", {})
            gap = verification.get("uncovered_staff_minutes")
            if gap is None:
                continue
            measured += 1
            if gap:
                alert = notice(session, definition, "A02:" + run.id + ":" + run.input_digest, "Lacunas de cobertura identificadas",
                    f"Foram identificados {gap} minutos-pessoa descobertos no cálculo. Revise os intervalos e competências exigidas.", "optimization_runs", run.id, severity="error")
                alerts.append({"notice_id": alert.id, "run_id": run.id, "uncovered_staff_minutes": gap,
                    "gap_intervals": len(verification.get("gaps", []))})
        return {"measured_runs": measured, "alerts": alerts, "truncated": truncated, "no_result": measured == 0}
    if code == "A03":
        query = select(m.ScheduleVersion).where(m.ScheduleVersion.organization_id == org, m.ScheduleVersion.unit_id == unit, m.ScheduleVersion.state == "submitted")
        if event.entity_type == "schedule_versions":
            query = query.where(m.ScheduleVersion.id == event.entity_id)
        schedules, truncated = rows(session, query.order_by(m.ScheduleVersion.created_at, m.ScheduleVersion.id), limit)
        recipients = session.scalars(select(m.User.id).join(m.UserRole, m.UserRole.user_id == m.User.id)
            .join(m.RolePermission, m.RolePermission.role_id == m.UserRole.role_id).join(m.Permission, m.Permission.id == m.RolePermission.permission_id)
            .where(m.User.organization_id == org, m.UserRole.organization_id == org, m.User.active.is_(True), m.Permission.code == "schedule:approve",
                or_(m.UserRole.unit_id.is_(None), m.UserRole.unit_id == unit)).distinct()).all()
        ids, without_reviewer = [], 0
        for schedule in schedules:
            author = session.get(m.OptimizationRun, schedule.run_id).actor_id
            allowed = [ident for ident in recipients if ident != author]
            without_reviewer += int(not allowed)
            for recipient in allowed:
                ids.append(notice(session, definition, f"A03:{schedule.id}:{schedule.digest}:{recipient}", "Proposta aguardando sua revisão",
                    "Uma proposta foi submetida. Confira insumos, cobertura e justificativa antes de decidir.", "schedule_versions", schedule.id, recipient, "info").id)
        return {"notice_ids": ids, "schedules_without_reviewer": without_reviewer, "truncated": truncated}
    if code == "A04":
        artifact = session.scalar(select(m.AutomationArtifact).where(m.AutomationArtifact.organization_id == org,
            m.AutomationArtifact.definition_id == definition.id, m.AutomationArtifact.event_id == event.id))
        if artifact:
            return {"artifact_id": artifact.id, "digest": artifact.digest, "reused": True}
        count = lambda model, *conditions: session.scalar(select(func.count()).select_from(model).where(model.organization_id == org, *conditions))
        values = [["produto", "Chronos 1.0"], ["unidade_id", unit], ["gerado_em_utc", m.now().isoformat()],
            ["colaboradores", count(m.Employee, m.Employee.unit_id == unit)],
            ["colaboradores_ativos", count(m.Employee, m.Employee.unit_id == unit, m.Employee.status == "active")],
            ["setores", count(m.Department, m.Department.unit_id == unit)],
            ["propostas_aprovadas_internamente", count(m.ScheduleVersion, m.ScheduleVersion.unit_id == unit, m.ScheduleVersion.state == "approved")]]
        latest = session.scalar(select(m.OptimizationRun).where(m.OptimizationRun.organization_id == org, m.OptimizationRun.unit_id == unit,
            m.OptimizationRun.state == "succeeded").order_by(m.OptimizationRun.created_at.desc(), m.OptimizationRun.id).limit(1))
        if latest:
            verification = latest.result.get("verification", {})
            values += [["ultimo_calculo_id", latest.id], ["ultimo_calculo_status", latest.result.get("solver_status", "sem_resultado")],
                ["demanda_minutos_pessoa", verification.get("required_staff_minutes", "nao_avaliada")],
                ["lacuna_minutos_pessoa", verification.get("uncovered_staff_minutes", "nao_avaliada")]]
        financial = None
        if principal.permits("finance:read", unit):
            financial = session.scalar(select(m.FinancialRun).where(m.FinancialRun.organization_id == org, m.FinancialRun.unit_id == unit)
                .order_by(m.FinancialRun.created_at.desc(), m.FinancialRun.id).limit(1))
        if financial:
            values += [["projecao_financeira_id", financial.id], ["total_anual_estimado_centavos", financial.result["annual_total_cents"]]]
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, delimiter=";", lineterminator="\r\n")
        writer.writerow(["indicador", "valor"])
        for pair in values:
            writer.writerow(["'" + str(v) if str(v).startswith(("=", "+", "-", "@", "\t", "\r")) else str(v) for v in pair])
        content = stream.getvalue()
        artifact = m.AutomationArtifact(organization_id=org, unit_id=unit, definition_id=definition.id, event_id=event.id,
            filename=f"Chronos-1.0-indicadores-{event.id}.csv", content=content, digest=hashlib.sha256(content.encode()).hexdigest(), finance_required=financial is not None)
        session.add(artifact); session.flush()
        return {"artifact_id": artifact.id, "digest": artifact.digest, "finance_required": artifact.finance_required}
    if code == "A05":
        deadline = m.now() + timedelta(days=definition.parameters.get("lookahead_days", 30))
        local_deadline_date = deadline.astimezone(ZoneInfo(session.get(m.Unit, unit).timezone)).date()
        notices, inspected, truncated = [], 0, False
        employee_ids = select(m.Employee.id).where(m.Employee.organization_id == org, m.Employee.unit_id == unit)
        sources = [(m.Contract, m.Contract.employee_id.in_(employee_ids)), (m.EmployeeQualification, m.EmployeeQualification.employee_id.in_(employee_ids)),
            (m.LaborRule, or_(m.LaborRule.unit_id.is_(None), m.LaborRule.unit_id == unit)), (m.WorkPattern, True)]
        for model, condition in sources:
            found, more = rows(session, select(model).where(model.organization_id == org, condition).order_by(model.id), limit)
            truncated |= more
            for row in found:
                inspected += 1
                status = getattr(row, "validation_status", getattr(row, "verification_status", getattr(row, "status", getattr(row, "legal_status", "pending_review"))))
                expiry = getattr(row, "valid_until", None)
                due = expiry is not None and (aware(expiry) <= deadline if hasattr(expiry, "hour") else expiry <= local_deadline_date)
                if status != "validated" or due:
                    stamp = f"{status}:{expiry}"
                    ident = notice(session, definition, f"A05:{model.__tablename__}:{row.id}:{stamp}", "Premissa requer revisão de vigência",
                        "Há uma premissa pendente, vencida ou próxima do fim da vigência. Nenhuma regra foi ativada ou validada automaticamente.", model.__tablename__, row.id).id
                    notices.append(ident)
        return {"notice_ids": notices, "inspected_records": inspected, "truncated": truncated, "lookahead_days": definition.parameters.get("lookahead_days", 30)}
    if code == "A06":
        availability = session.get(m.AvailabilityRule, event.entity_id) if event.entity_type == "availability_rules" else None
        if availability is None or availability.organization_id != org or availability.type != "unavailable":
            return {"suggestion_ids": [], "scope": "A rotina precisa de um evento de indisponibilidade; não altera escalas."}
        from datetime import datetime
        query = select(m.ScheduleVersion).where(m.ScheduleVersion.organization_id == org, m.ScheduleVersion.unit_id == unit,
            m.ScheduleVersion.state.in_(["draft", "submitted", "approved"])).order_by(m.ScheduleVersion.created_at.desc(), m.ScheduleVersion.id)
        schedules, truncated = rows(session, query, limit)
        ids = []
        for schedule in schedules:
            affected = [a for a in schedule.payload["assignments"] if a["employee_id"] == availability.employee_id and
                datetime.fromisoformat(a["start_at"]) < aware(availability.end_at) and datetime.fromisoformat(a["end_at"]) > aware(availability.start_at)]
            if not affected:
                continue
            suggestion = session.scalar(select(m.AutomationSuggestion).where(m.AutomationSuggestion.organization_id == org,
                m.AutomationSuggestion.event_id == event.id, m.AutomationSuggestion.schedule_id == schedule.id))
            if suggestion is None:
                suggestion = m.AutomationSuggestion(organization_id=org, unit_id=unit, event_id=event.id, schedule_id=schedule.id, source_run_id=schedule.run_id,
                    reason="Indisponibilidade alcança uma alocação existente. Revise a nova disponibilidade antes de solicitar outra versão.", details={"affected_assignments": len(affected), "availability_id": availability.id})
                session.add(suggestion); session.flush()
            ids.append(suggestion.id)
            notice(session, definition, f"A06:{suggestion.id}", "Reotimização sugerida", "Uma indisponibilidade afeta a proposta. Um responsável precisa solicitar o novo cálculo; a versão atual foi preservada.", "schedule_versions", schedule.id)
        return {"suggestion_ids": ids, "truncated": truncated, "automatic_jobs": 0}
    if code == "A07":
        return {"event_id": event.id, "kind": event.kind, "entity_type": event.entity_type, "entity_id": event.entity_id,
            "correlation_id": event.correlation_id, "scope": "Metadados rastreáveis; sem replicar dados pessoais, salários ou credenciais."}
    raise AutomationError("UNKNOWN_AUTOMATION")
