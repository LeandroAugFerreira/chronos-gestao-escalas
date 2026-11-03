"""Chronos 1.0: fixtures reproduzíveis. Nenhum quantitativo representa norma clínica."""

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "data" / "synthetic" / "hospital_horizonte.json"
SEED = 1042

# Contagens são escolhas narrativas; não representam suficiência de cobertura.
SECTORS = [
    ("management", "Direção e gestão", "Administrativo", "business", 8, [("director", "Diretor", "Gestão hospitalar"), ("manager", "Gestor de operações", "Planejamento operacional")]),
    ("hr", "Recursos Humanos", "Administrativo", "business", 8, [("hr_analyst", "Analista de RH", "Gestão de pessoas")]),
    ("finance", "Financeiro e faturamento", "Administrativo", "business", 12, [("finance_analyst", "Analista financeiro", "Controles financeiros"), ("billing", "Faturista", "Faturamento hospitalar")]),
    ("reception", "Recepção e atendimento", "Operacional", "24x7", 20, [("receptionist", "Recepcionista", "Atendimento e admissão")]),
    ("emergency", "Pronto-socorro", "Assistencial", "24x7", 36, [("emergency_doctor", "Médico emergencista", "Atendimento de urgência"), ("emergency_nurse", "Enfermeiro de urgência", "Enfermagem de urgência"), ("emergency_technician", "Técnico de enfermagem de urgência", "Cuidados de urgência supervisionados")]),
    ("icu", "Unidade de Terapia Intensiva", "Assistencial", "24x7", 36, [("intensivist", "Médico intensivista", "Medicina intensiva"), ("icu_nurse", "Enfermeiro de terapia intensiva", "Enfermagem em terapia intensiva"), ("icu_technician", "Técnico de enfermagem de UTI", "Cuidados intensivos supervisionados")]),
    ("inpatient", "Internação", "Assistencial", "24x7", 42, [("hospitalist", "Médico hospitalista", "Clínica hospitalar"), ("ward_nurse", "Enfermeiro de internação", "Cuidados de internação"), ("ward_technician", "Técnico de enfermagem de internação", "Cuidados de internação supervisionados")]),
    ("surgery", "Centro cirúrgico", "Assistencial", "24x7", 28, [("surgeon", "Cirurgião", "Procedimentos cirúrgicos"), ("anesthetist", "Anestesiologista", "Anestesiologia"), ("surgical_nurse", "Enfermeiro de centro cirúrgico", "Enfermagem perioperatória"), ("surgical_technician", "Técnico de enfermagem de centro cirúrgico", "Apoio perioperatório")]),
    ("nursing", "Enfermagem", "Assistencial", "24x7", 30, [("nurse", "Enfermeiro de equipe de apoio", "Enfermagem geral"), ("nursing_technician", "Técnico de enfermagem de apoio", "Cuidados gerais supervisionados")]),
    ("pharmacy", "Farmácia hospitalar", "Assistencial", "24x7", 12, [("pharmacist", "Farmacêutico", "Farmácia clínica"), ("pharmacy_assistant", "Auxiliar de farmácia", "Dispensação supervisionada")]),
    ("laboratory", "Laboratório", "Assistencial", "24x7", 14, [("biomedical", "Biomédico", "Análises clínicas"), ("lab_technician", "Técnico de laboratório", "Processamento de amostras")]),
    ("imaging", "Diagnóstico por imagem", "Assistencial", "24x7", 12, [("radiologist", "Médico radiologista", "Interpretação de exames de imagem"), ("radiology_technician", "Técnico em radiologia", "Operação de equipamentos de imagem")]),
    ("physiotherapy", "Fisioterapia", "Assistencial", "24x7", 10, [("physiotherapist", "Fisioterapeuta", "Fisioterapia hospitalar")]),
    ("nutrition", "Nutrição e cozinha", "Operacional", "24x7", 18, [("nutritionist", "Nutricionista", "Nutrição clínica"), ("cook", "Cozinheiro", "Produção segura de refeições"), ("kitchen_assistant", "Auxiliar de cozinha", "Boas práticas de manipulação")]),
    ("cleaning", "Higienização e limpeza", "Operacional", "24x7", 26, [("cleaner", "Agente de higienização", "Higienização de áreas assistenciais")]),
    ("laundry", "Lavanderia", "Operacional", "extended", 10, [("laundry_operator", "Operador de lavanderia", "Processamento de enxoval")]),
    ("maintenance", "Manutenção", "Operacional", "24x7", 10, [("maintenance_technician", "Técnico de manutenção", "Manutenção predial"), ("electrician", "Eletricista", "Segurança em instalações elétricas")]),
    ("security", "Segurança", "Operacional", "24x7", 10, [("security_officer", "Vigilante", "Segurança patrimonial")]),
    ("logistics", "Logística e almoxarifado", "Operacional", "24x7", 8, [("stock_clerk", "Almoxarife", "Gestão de estoque"), ("logistics_assistant", "Auxiliar de logística", "Logística interna")]),
]


def build_dataset() -> dict:
    rng = random.Random(SEED)
    data = {
        "product": "Chronos 1.0", "schema_version": "1.0", "seed": SEED,
        "reference_date": "2026-10-24", "synthetic": True,
        "organization": {"id": "horizonte", "name": "Hospital Horizonte", "segment": "hospital", "operation": "24x7", "timezone": "America/Sao_Paulo", "synthetic": True},
        "units": [{"id": "horizonte-main", "organization_id": "horizonte", "name": "Unidade principal", "operation": "24x7"}],
        "departments": [], "job_roles": [], "skills": [], "employees": [], "contracts": [],
        "employee_qualifications": [], "availability_rules": [], "staffing_requirements": [],
        "shift_templates": [
            {"id": "day-12", "start": "07:00", "end": "19:00", "end_day_offset": 0, "break_minutes": 60, "legal_status": "pending_review"},
            {"id": "night-12", "start": "19:00", "end": "07:00", "end_day_offset": 1, "break_minutes": 60, "legal_status": "pending_review"},
            {"id": "admin-8", "start": "08:00", "end": "17:00", "end_day_offset": 0, "break_minutes": 60, "legal_status": "pending_review"},
            {"id": "duty-6", "start": "07:00", "end": "13:00", "end_day_offset": 0, "break_minutes": 15, "legal_status": "pending_review"},
        ],
        "work_patterns": [
            {"id": "5x2", "name": "5x2", "description": "Jornada administrativa ou operacional, conforme contrato e regras aplicáveis."},
            {"id": "4x3", "name": "4x3", "description": "Hipótese de simulação; validade depende das condições aplicáveis."},
            {"id": "12x36", "name": "12x36", "description": "Doze horas de plantão e trinta e seis de descanso, condicionadas à validação aplicável."},
            {"id": "duty", "name": "Plantões", "description": "Durações e horários parametrizáveis, incluindo diurnos e noturnos."},
            {"id": "special", "name": "Regimes especiais", "description": "Somente com escopo, fonte e justificativa cadastrados."},
            {"id": "custom", "name": "Personalizadas", "description": "Ciclos, descansos e limites configuráveis."},
            {"id": "6x1-historical", "name": "6x1 histórica", "description": "Referência histórica ou exceção fundamentada, sem ativação automática."},
        ],
    }
    for pattern in data["work_patterns"]:
        pattern["legal_status"] = "pending_review"
    number = 0
    for sector_id, name, group, operation, count, definitions in SECTORS:
        department = {"id": sector_id, "organization_id": "horizonte", "unit_id": "horizonte-main", "name": name, "group": group, "operation": operation, "cost_center": f"CC-{sector_id}"}
        data["departments"].append(department)
        for role_id, role_name, skill in definitions:
            skill_id = f"skill-{role_id}"
            qualification_id = f"qualification-{role_id}"
            data["skills"].append({"id": skill_id, "organization_id": "horizonte", "name": skill, "qualification_id": qualification_id})
            data["job_roles"].append({"id": role_id, "organization_id": "horizonte", "name": role_name, "department_ids": [sector_id], "required_skill_ids": [skill_id], "required_qualification_ids": [qualification_id]})
        for index in range(count):
            number += 1
            role_id = definitions[index % len(definitions)][0]
            employee_id = f"hh-{number:04d}"
            pattern = "5x2" if operation == "business" else ["12x36", "duty", "custom"][index % 3]
            data["employees"].append({
                "id": employee_id, "organization_id": "horizonte", "unit_id": "horizonte-main", "department_id": sector_id,
                "job_role_id": role_id, "name": f"Pessoa Sintética {number:03d}", "registration": f"HH{number:04d}",
                "skill_ids": [f"skill-{role_id}"], "contract_id": f"contract-{employee_id}",
                "status": "active", "synthetic": True, "legal_status": "pending_review",
                "preferred_shift": "day" if index % 2 == 0 else "night", "preferred_days_off": [rng.randrange(7)],
            })
            data["contracts"].append({"id": f"contract-{employee_id}", "organization_id": "horizonte", "employee_id": employee_id,
                "work_pattern_id": pattern, "weekly_minutes": rng.choice([1800, 2160, 2400]), "base_salary_cents": rng.randrange(220000, 1200001, 10000),
                "currency": "BRL", "employment_type": "simulated", "valid_from": "2026-01-01", "validation_status": "pending_review", "assumption_source": "Premissa sintética; não representa piso, vínculo ou jornada legal."})
            data["employee_qualifications"].append({"id": f"eq-{employee_id}", "organization_id": "horizonte", "employee_id": employee_id,
                "qualification_id": f"qualification-{role_id}", "valid_from": "2026-01-01", "valid_until": "2027-12-31", "verification_status": "synthetic_only", "evidence": "Credencial fictícia; sem número de conselho real."})
            if number % 17 == 0:
                data["availability_rules"].append({"id": f"absence-{employee_id}", "organization_id": "horizonte", "employee_id": employee_id,
                    "start": "2026-11-03T07:00:00-03:00", "end": "2026-11-04T07:00:00-03:00", "type": "unavailable", "reason": "Indisponibilidade sintética"})
        # Exemplo de demanda operacional, não mínimo legal. Pausas e habilidades
        # serão expandidas por intervalo pelo solver; o total de pessoas não prova cobertura.
        for role_id, _, _ in definitions:
            shift_ids = ["admin-8"] if operation == "business" else ["day-12", "night-12"]
            for shift_id in shift_ids:
                data["staffing_requirements"].append({"id": f"req-{sector_id}-{role_id}-{shift_id}", "organization_id": "horizonte",
                    "department_id": sector_id, "job_role_id": role_id, "shift_template_id": shift_id,
                    "required_skill_ids": [f"skill-{role_id}"], "required_qualification_ids": [f"qualification-{role_id}"],
                    "minimum_people": 1, "source_type": "synthetic_assumption", "validation_status": "pending_review",
                    "source": "Parâmetro fictício para testes; não é dimensionamento assistencial nem mínimo normativo.", "hard_in_strict_mode": True})
    data["qualifications"] = [{"id": f"qualification-{r['id']}", "organization_id": "horizonte", "name": f"Qualificação simulada: {r['name']}", "synthetic": True} for r in data["job_roles"]]
    validate_dataset(data)
    return data


def validate_dataset(data: dict) -> None:
    assert len(data["employees"]) == 350
    assert len(data["departments"]) == 19
    for key in ["employees", "departments", "job_roles", "skills", "contracts", "qualifications", "employee_qualifications", "staffing_requirements"]:
        assert len({row["id"] for row in data[key]}) == len(data[key]), key
    roles = {r["id"]: r for r in data["job_roles"]}
    departments = {d["id"] for d in data["departments"]}
    skills = {s["id"] for s in data["skills"]}
    qualifications = {q["id"] for q in data["qualifications"]}
    employees = {e["id"]: e for e in data["employees"]}
    contracts = {c["id"]: c for c in data["contracts"]}
    patterns = {p["id"] for p in data["work_patterns"]}
    shifts = {s["id"] for s in data["shift_templates"]}
    for key in ["departments", "job_roles", "skills", "employees", "contracts", "qualifications", "employee_qualifications", "availability_rules", "staffing_requirements"]:
        assert all(row["organization_id"] == data["organization"]["id"] for row in data[key]), "Organização inconsistente"
    for role in roles.values():
        assert set(role["required_skill_ids"]) <= skills
        assert set(role["required_qualification_ids"]) <= qualifications
    for qualification in data["employee_qualifications"]:
        assert qualification["employee_id"] in employees
        assert qualification["qualification_id"] in qualifications
        assert qualification["valid_from"] < qualification["valid_until"]
    for employee in data["employees"]:
        assert employee["department_id"] in departments
        assert employee["job_role_id"] in roles
        assert set(employee["skill_ids"]) <= skills
        assert set(roles[employee["job_role_id"]]["required_skill_ids"]) <= set(employee["skill_ids"])
        assert employee["department_id"] in roles[employee["job_role_id"]]["department_ids"]
        assert employee["contract_id"] in contracts
        assert contracts[employee["contract_id"]]["employee_id"] == employee["id"]
        held = {q["qualification_id"] for q in data["employee_qualifications"] if q["employee_id"] == employee["id"]}
        assert set(roles[employee["job_role_id"]]["required_qualification_ids"]) <= held
    for contract in contracts.values():
        assert contract["employee_id"] in employees and contract["work_pattern_id"] in patterns
        assert contract["base_salary_cents"] >= 0 and contract["weekly_minutes"] > 0
    for requirement in data["staffing_requirements"]:
        assert requirement["department_id"] in departments and requirement["job_role_id"] in roles
        assert requirement["shift_template_id"] in shifts
        assert set(requirement["required_skill_ids"]) <= skills
        assert set(requirement["required_qualification_ids"]) <= qualifications
        assert requirement["minimum_people"] >= 0
        assert requirement["source_type"] == "synthetic_assumption"
    for availability in data["availability_rules"]:
        assert availability["employee_id"] in employees
        assert availability["start"] < availability["end"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chronos 1.0: gerar fixture sintética reproduzível")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Verificar a fixture existente sem gravar")
    args = parser.parse_args()
    dataset = build_dataset()
    if args.check:
        assert json.loads(args.output.read_text(encoding="utf-8")) == dataset, "Fixture desatualizada"
        print("Chronos 1.0: fixture reproduzível e íntegra (350 colaboradores, 19 setores).")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Chronos 1.0: dados sintéticos gravados em {args.output}")
