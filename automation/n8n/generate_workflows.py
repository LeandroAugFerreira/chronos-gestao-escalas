"""Chronos 1.0 — deterministic exports; contains no credential values."""
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parent
API = "http://127.0.0.1:8017/api/v1/integration"


def ident(name):
    return str(uuid5(NAMESPACE_URL, "chronos/1.0/n8n/" + name))


def trigger(code, suffix="", y=0):
    return {"id": ident(code + "trigger" + suffix), "name": "Indisponibilidade autenticada" if suffix else "Evento autenticado",
        "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, y], "webhookId": ident(code + "webhook" + suffix),
        "parameters": {"httpMethod": "POST", "path": "chronos/availability" if suffix else "chronos/" + code.lower(),
            "authentication": "headerAuth", "responseMode": "lastNode", "options": {}},
        "credentials": {"httpHeaderAuth": {"id": ident("webhook-auth"), "name": "Chronos 1.0 — Webhook local"}}}


def request(code, suffix="", y=0):
    return {"id": ident(code + "request" + suffix), "name": "Registrar indisponibilidade" if suffix else "Confirmar evento no Chronos",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [300, y],
        "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 1000,
        "parameters": {"method": "POST", "url": API + ("/availability" if suffix else "/automation-events"),
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth", "sendBody": True,
            "sendHeaders": True, "headerParameters": {"parameters": [{"name": "X-Chronos-Workflow-Execution", "value": "={{ $execution.id }}"}]},
            "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}", "options": {"timeout": 5000}},
        "credentials": {"httpHeaderAuth": {"id": ident("callback-auth"), "name": "Chronos 1.0 — Callback autorizado"}}}


def exports():
    for code, label, filename in [("A03", "Escala pendente", "A03-escala-pendente"), ("A02", "Alerta de cobertura", "A02-alerta-cobertura"),
        ("A04", "Relatório programado", "A04-relatorio-programado"), ("A06", "Disponibilidade e impacto", "A06-disponibilidade")]:
        first, second = trigger(code), request(code)
        nodes = [first, second]
        connections = {first["name"]: {"main": [[{"node": second["name"], "type": "main", "index": 0}]]}}
        if code == "A06":
            incoming, update = trigger(code, "availability", 240), request(code, "availability", 240)
            nodes += [incoming, update]
            connections[incoming["name"]] = {"main": [[{"node": update["name"], "type": "main", "index": 0}]]}
        workflow = {"id": ident(code), "name": f"Chronos 1.0 — {code} — {label}", "active": False, "nodes": nodes,
            "connections": connections, "settings": {"executionOrder": "v1", "timezone": "America/Sao_Paulo", "saveDataErrorExecution": "none",
                "saveDataSuccessExecution": "none", "saveExecutionProgress": False, "saveManualExecutions": False},
            "meta": {"templateCredsSetupCompleted": False}, "pinData": {}, "tags": []}
        workflow["versionId"] = ident(json.dumps(workflow, sort_keys=True))
        yield filename, workflow


if __name__ == "__main__":
    for filename, workflow in exports():
        (ROOT / (filename + ".json")).write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Chronos 1.0: quatro workflows desativados gerados, sem segredos.")
