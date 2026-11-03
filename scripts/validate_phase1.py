"""Chronos 1.0: consistência dos artefatos da Fase 1, sem dependências extras."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
prompt_path = ROOT / "docs/requirements/PROMPT_MESTRE_CHRONOS_1.0.md"
prompt = prompt_path.read_text(encoding="utf-8")
manifest = json.loads((ROOT / "docs/requirements/consolidation.json").read_text(encoding="utf-8"))
assert hashlib.sha256(prompt_path.read_bytes()).hexdigest() == manifest["consolidated_sha256"]
assert [int(n) for n in re.findall(r"^### (\d+)\.", prompt, re.M)] == list(range(1, 27))
for token in ["Chronos 1.0", "Hospital Horizonte", "350", "12x36", "OR-Tools", "n8n", "LaborRules", "Financeiro", "FASE 2", "Power BI"]:
    assert token in prompt, token
release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
assert release["display_name"] == "Chronos 1.0" and release["version"] == "1.0"
assert release["published"] is False and release["release_ready"] is False
for relative in ["README.md", ".env.example", "CHANGELOG.md", "frontend/package-lock.json", "backend/requirements-lock.txt", "docs/requirements/requirements.md", "docs/architecture/architecture.md", "docs/architecture/optimization.md", "docs/database/model.md", "docs/legal-rules/labor-rules.md", "docs/business-process/processes.md", "docs/roadmap.md", "docs/testing/acceptance.md"]:
    assert (ROOT / relative).is_file(), relative
print("Chronos 1.0: identidade, versão, prompt consolidado, hashes e documentos verificados.")
