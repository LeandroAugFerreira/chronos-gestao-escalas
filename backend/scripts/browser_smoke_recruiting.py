"""Smoke real em Chromium do Chronos, apenas em SQLite isolado e dados fictícios.

Não usa credenciais, bancos, n8n ou contas externas do autor.
Executado pelo GitHub Actions em runner Ubuntu; não publica backend.
"""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
SITE = "http://127.0.0.1:5187"
API = "http://127.0.0.1:8017"
ARTIFACTS = ROOT / "artifacts" / "browser"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def ready(url: str, limit_seconds=65):
    deadline = time.monotonic() + limit_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, OSError, TimeoutError):
            pass
        time.sleep(.4)
    raise RuntimeError("Servidor não iniciou no loopback dentro do limite do teste")


def process(command, cwd, env, log_path):
    output = log_path.open("w", encoding="utf-8")
    child = subprocess.Popen(command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT)
    return child, output


def main():
    with tempfile.TemporaryDirectory(prefix="chronos-browser-qa-") as temp:
        env = os.environ.copy()
        # Não herdar configuração ou segredos de nenhuma instalação prévia.
        for key in tuple(env):
            if key.startswith(("CHRONOS_", "DATABASE_URL", "JWT_SECRET")):
                env.pop(key, None)
        password = secrets.token_urlsafe(30)
        jwt = secrets.token_urlsafe(50)
        env.update({
            "CHRONOS_ENVIRONMENT": "test",
            "CHRONOS_DATABASE_URL": "sqlite+pysqlite:///" + (Path(temp) / "qa-chronos.sqlite3").as_posix(),
            "CHRONOS_ALLOW_SQLITE": "true",
            "CHRONOS_JWT_SECRET": jwt,
            "CHRONOS_ALLOWED_ORIGINS": SITE,
            "CHRONOS_COOKIE_SECURE": "false",
            "CHRONOS_N8N_WEBHOOK_BASE_URL": "",
            "CHRONOS_N8N_OUTBOUND_TOKEN": "",
            "CHRONOS_BOOTSTRAP_PASSWORD": password,
            "CHRONOS_TEST_POSTGRES_URL": "",
            "PYTHONPATH": str(BACKEND),
        })
        # Operações locais explícitas: migrations, fixture sintética e usuário QA efêmero.
        cli = [sys.executable, "backend/scripts/manage.py"]
        for args in (["migrate"], ["seed-demo"], ["create-admin", "--username", "recrutamentoqa"]):
            subprocess.run(cli + args, cwd=ROOT, env=env, check=True, timeout=120,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        api, api_log = process([sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", "8017", "--no-access-log"],
            BACKEND, env, Path(temp) / "uvicorn.log")
        vite, vite_log = process(["npm", "run", "dev", "--", "--host", "127.0.0.1",
            "--port", "5187", "--strictPort"], FRONTEND, env, Path(temp) / "vite.log")
        try:
            ready(API + "/api/v1/health")
            ready(SITE)
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1365, "height": 900}, locale="pt-BR")
                page = context.new_page()
                page.set_default_timeout(18000)
                try:
                    page.goto(SITE + "/login", wait_until="domcontentloaded")
                    expect(page.get_by_role("heading", name="Bom ter você por aqui.")).to_be_visible(timeout=20000)
                    page.get_by_label("Organização").fill("horizonte")
                    page.get_by_label("Usuário").fill("recrutamentoqa")
                    page.get_by_label("Senha", exact=True).fill(password)
                    page.get_by_role("button", name="Entrar na plataforma").click()
                    expect(page.get_by_role("heading", name="O ritmo da sua operação.")).to_be_visible(timeout=30000)
                    expect(page.get_by_text("Colaboradores ativos", exact=True)).to_be_visible(timeout=30000)
                    expect(page.get_by_text("Dados do banco de demonstração")).to_be_visible()
                    page.screenshot(path=str(ARTIFACTS / "chronos-visao-geral-qa.png"), full_page=True)

                    page.goto(SITE + "/otimizacao", wait_until="domcontentloaded")
                    expect(page.locator("main")).to_be_visible(timeout=20000)
                    # Página protegida e renderizada com acesso administrativo legítimo.
                    expect(page.get_by_text("Otimização de escalas").first).to_be_visible(timeout=30000)
                    page.screenshot(path=str(ARTIFACTS / "chronos-otimizacao-qa.png"), full_page=True)
                    page.goto(SITE + "/transicao", wait_until="domcontentloaded")
                    expect(page.get_by_role("heading", name="Transição de jornadas", exact=True)).to_be_visible()
                    page.get_by_role("button", name="Comparar etapas", exact=True).click()
                    expect(page.get_by_text("Comparação pronta para revisão", exact=True)).to_be_visible()
                    expect(page.get_by_text("Divisor: 210 horas", exact=True)).to_be_visible()
                    page.screenshot(path=str(ARTIFACTS / "chronos-2.0-transicao-42h.png"), full_page=True)
                    page.get_by_label("Data de referência", exact=True).fill("2027-12-16")
                    expect(page.get_by_text("Comparação pronta para revisão", exact=True)).not_to_be_visible()
                    page.get_by_role("button", name="Comparar etapas", exact=True).click()
                    expect(page.get_by_text("Divisor: 200 horas", exact=True)).to_be_visible()
                    page.set_viewport_size({"width": 390, "height": 844})
                    expect(page.get_by_role("heading", name="Transição de jornadas", exact=True)).to_be_visible()
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                    page.screenshot(path=str(ARTIFACTS / "chronos-2.0-transicao-mobile.png"), full_page=True)
                    print("PASS: Chronos 2.0 comparou 42h/40h pela API real, invalidou resultado antigo e abriu em 390x844.")
                    print("PASS: Chromium fez login pelo formulário real, sem token mockado.")
                    print("PASS: carregou dados da fixture sintética no Dashboard e abriu a área de otimização.")
                    print("PASS: screenshots fictícios registrados para revisão no CI.")
                except Exception:
                    page.screenshot(path=str(ARTIFACTS / "chronos-failure-qa.png"), full_page=True)
                    raise
                finally:
                    context.close()
                    browser.close()
        finally:
            for child in (vite, api):
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
            api_log.close()
            vite_log.close()


if __name__ == "__main__":
    main()
