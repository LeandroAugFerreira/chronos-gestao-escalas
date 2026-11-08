# Chronos — protocolo de navegador real, com banco temporário

**Execução aprovada:** [GitHub Actions #42512605602](https://github.com/LeandroAugFerreira/chronos-gestao-escalas/actions/runs/42512605602) em 08/11/2026.
**SHA do código executado:** 3d4719935b9d56ac17cdcc1f921ca2554b994622.

## O que realmente ocorreu

- Instalação das dependências Python declaradas e das dependências de desenvolvimento frontend.
- Aplicação de migrations Alembic sobre banco SQLite efêmero fora do projeto.
- Importação da fixture Hospital Horizonte **fictícia** (350 colaboradores) e criação de usuário QA efêmero com segredo aleatório.
- Inicialização da API real FastAPI em loopback (127.0.0.1:8017) e Vite React no loopback (127.0.0.1:5187).
- Chromium abriu a página de login, digitou a organização e credenciais fictícias, autenticou pelo backend real, confirmou visão geral com dados da fixture e abriu a página de Otimização.
- Capturas sintéticas da visão geral/otimização registradas como artifact temporário do CI.
- Os serviços foram encerrados e o banco apagado no cleanup.

**O que este smoke NÃO executou:** cálculo por worker via formulário, criação/submissão/aprovação completa de uma proposta, PostgreSQL, n8n ou teste de segurança ofensivo. Os testes pytest cobrem separadamente lógica de solver e governança.

## Resultado do conjunto de testes

No mesmo CI:
- Backend **184 pytest aprovados**, 1 ignorado por ausência de PostgreSQL descartável, 1 aviso de dependência de testes.
- Frontend **88 Vitest aprovados**, build aprovado.
- Smoke do navegador real **aprovado**.

O primeiro run da branch falhou por um seletor textual ambíguo no teste de UI, não por falha de login; ele foi corrigido para correspondência exata. A aprovação corresponde à execução #42512605602, posterior à correção.

## Segurança e restrições

- O runner usa Ubuntu 24.04, Python 3.13, Node 22, Playwright 1.56.0 e Chromium.
- Banco em TemporaryDirectory, secrets QA gerados em memória, sem tokens e senhas em capturas.
- Ambiente test, SQLite explicitamente autorizado e CORS limitado ao frontend de loopback.
- Nenhuma publicação de backend, conexão com serviços externos ou conta pessoal.
- O runtime n8n permanece bloqueado, sem instalação/execução neste workflow.
- Screenshots da fixture são disponibilizados por 7 dias nos artifacts de CI.

## Como reproduzir com segurança

Em checkout novo, sem copiar arquivos .env ou runtime de operação:

~~~bash
python -m pip install -r backend/requirements-lock.txt
python -m pip install playwright==1.56.0
python -m playwright install --with-deps chromium
npm --prefix frontend ci
python backend/scripts/browser_smoke_recruiting.py
~~~

O script só seleciona SQLite efêmero e valores sintéticos; ainda assim, examine os comandos antes de executar em equipamento pessoal.

## Demonstração web no portfólio

[Chronos — visualização interativa do benchmark](https://leandroaugferreira.github.io/chronos-demo.html) não usa o backend acima. O tour é uma apresentação estática de dados históricos do benchmark (3 versus 2 profissionais). Não confundir com o smoke Chromium ou com o solver CP-SAT executado no pytest.

[Auditoria](AUDITORIA.md) · [Evidências](EVIDENCIAS.md) · [Roteiro](ROTEIRO_DEMO.md).
