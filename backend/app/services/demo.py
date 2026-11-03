"""Consulta de fixture sintética, sem simular persistência ou escala aprovada."""

import json
from collections import Counter
from pathlib import Path

from app.core.config import DEMO_FILE, PRODUCT_NAME, PRODUCT_VERSION
from app.schemas.demo import DemoSummary


def load_demo(path: Path = DEMO_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_demo(data: dict) -> DemoSummary:
    counts = Counter(employee["department_id"] for employee in data["employees"])
    roles = {role["id"]: role for role in data["job_roles"]}
    skills = {skill["id"]: skill["name"] for skill in data["skills"]}
    departments = []
    for department in data["departments"]:
        department_roles = [role for role in roles.values() if department["id"] in role["department_ids"]]
        skill_ids = sorted({skill for role in department_roles for skill in role["required_skill_ids"]})
        departments.append({
            "id": department["id"], "name": department["name"],
            "group": department["group"], "operation": department["operation"],
            "employee_count": counts[department["id"]],
            "job_roles": [role["name"] for role in department_roles],
            "skills": [skills[skill] for skill in skill_ids],
        })
    return DemoSummary(
        product=PRODUCT_NAME, version=PRODUCT_VERSION, phase=1,
        organization=data["organization"]["name"], synthetic=True,
        employee_count=len(data["employees"]), department_count=len(data["departments"]),
        unit_count=len(data["units"]), role_count=len(roles), operation=data["organization"]["operation"],
        seed=data["seed"], departments=departments, regimes=data["work_patterns"],
        notices=[
            "Dados inteiramente sintéticos. Distribuição de pessoal ilustrativa, sem dimensionamento normativo.",
            "Fase 1: planejamento e execução mínima; persistência e autenticação previstas na Fase 2.",
            "Jornadas são hipóteses de configuração. Aplicabilidade depende de validação jurídica e contratual.",
            "Cobertura, custo e conformidade ainda não calculados; otimizador e automações previstos nas próximas fases.",
        ],
    )
