# Chronos 1.0 — Relatório da Fase 1

Data: 24/10/2026. Pasta exclusiva: `C:\Users\leand\OneDrive\Projetos\Chronos`.

**Entrega: planejamento e arquitetura documentados, com checkpoint local de backend/frontend e fixture reproduzível.** A aplicação completa continua em desenvolvimento. Nenhuma fase posterior está declarada concluída.

## Efetivamente criado

- Prompt Mestre consolidado com 25 seções de origem, controle adicional da atualização e hashes. Identidade Chronos 1.0 e cenário Hospital Horizonte aplicados; o anexo original foi lido e seu hash permanece igual.
- Requisitos funcionais/não funcionais, arquitetura modular e decisões, modelo relacional/ER, integridade e isolamento entre organizações, contrato inicial da API, LaborRules e modelo CP-SAT especificados.
- Jornadas parametrizáveis, competências/qualificações, dimensionamento por atividade/fonte, cobertura 24x7, substituições, pausas, continuidade e diagnóstico de inviabilidade descritos sem mínimos hospitalares universais.
- Processos financeiros, aprovações, catálogo A01–A07 e quatro workflows n8n preservados na especificação. Cronograma incremental e plano de implementação/aceite da Fase 2.
- Fixture sintética: 350 pessoas, 19 setores, 38 funções, competências, qualificações, contratos, indisponibilidades, templates de turnos/demanda e jornadas. Seed fixa 1042; sem dados reais ou números de conselho.
- FastAPI de leitura com `/api/v1/health`, `/api/v1/demo/summary`, Swagger e OpenAPI. Resumo calculado a partir da fixture; sem API de pessoas desprotegida.
- React/TypeScript/Vite/Router/Query com visão geral, setores, filtros/busca e temas. Interface temporal corporativa sem logotipo hospitalar; estados de erro/carregamento e avisos sobre o checkpoint.
- Scripts de setup, inicialização, verificação e regeneração da fixture; dependências travadas, `.env.example`, metadados de desenvolvimento e Git local sem remote, commit, push ou publicação.

Lista completa dos artefatos autorais: [manifesto de arquivos](file-manifest.md). Diretórios `.gitkeep` são reservados; não são módulos implementados.

## Verificações executadas

| Verificação | Resultado observado |
|---|---|
| Inspeção de ambiente | Python 3.13.0, Node 22.14.0, npm 10.9.2, Git 2.52.0.windows.1; Docker não encontrado |
| Fixture `generate_demo.py --check` | Integridade/reprodução aprovadas: 350 pessoas e 19 setores |
| Identidade, versão, hash e estrutura do prompt | Validados por `scripts/validate_phase1.py`; anexo original preservado por SHA-256 |
| Sintaxe dos quatro scripts PowerShell | Aprovada pelo parser PowerShell |
| Backend `pytest -q` | **12 passed, 1 warning in 1.34s** |
| Frontend `npm run build` | TypeScript + Vite aprovados; 86 módulos; build Vite em 1.84s |
| HTTP direto | `/api/v1/health`: 200, produto Chronos e versão 1.0 |
| HTTP do Vite e proxy API | Página: 200; `/api/v1/demo/summary` pelo proxy retornou 350 pessoas, 19 setores, 38 funções |
| Isolamento de dependências | Venv e caches fora do OneDrive; `node_modules`, `dist` e caches ignorados pelo Git |
| Navegação real/inspeção visual | **Não executada**: aquisição da aba bloqueada pela política de segurança da ferramenta de navegador; não houve tentativa de contornar |

Os 12 testes verificam integridade/IDs dos dados, reprodutibilidade, totais derivados da entrada, vínculos de funções/competências, contrato HTTP, erro seguro de fixture ausente, CORS, OpenAPI, ausência de exposição de pessoas e rejeição de organização cruzada, qualificação ausente e contrato pertencente a outra pessoa. Não testam um motor jurídico/solver ainda inexistente.

## Falhas de ambiente e limitações

1. Venv com ensurepip falhou inicialmente no sandbox. Contorno: `venv --without-pip` + pip base com `--python` direcionado ao venv. Não houve instalação global.
2. Downloads não resolveram DNS dentro do sandbox; as dependências foram instaladas com execução de rede autorizada.
3. TestClient/Uvicorn ficaram bloqueados no socket interno do asyncio no sandbox Windows. Testes e backend passaram em execução local fora dessa restrição; processos bloqueados foram encerrados.
4. Porta Vite padrão 5173 ocupada. Foram adotadas 5187/8017 para o Chronos; nenhum serviço de outro projeto foi encerrado. O servidor Vite também precisou do contexto de rede local para o teste HTTP.
5. Há **um aviso de depreciação** do Starlette TestClient por uso de httpx na versão instalada. Não causou falha nos testes; avaliar migração do cliente de teste na manutenção das dependências da Fase 2.
6. Docker/PostgreSQL, migrations, autenticação/RBAC, UI em navegador, acessibilidade visual e responsividade real não foram validados nesta fase. Memória/disco não foram estimados a partir de dados indisponíveis no sandbox.
7. Fixture é JSON, não persistência de banco. Qualificações e demandas são sintéticas, não habilitações reais nem dimensionamento normativo. Nenhuma escala, cálculo de cobertura/custo, validação jurídica, aprovação ou automação é alegada como executada.

## Decisões relevantes

Monólito modular; PostgreSQL como referência e SQLite leve condicionado a testes; entidades configuráveis para outros segmentos; worker somente ao implementar otimização; n8n/IA opcionais; cenários/regras imutáveis por versão; custos em centavos e tempo em minutos/instantes com fuso.

A divergência de data no prompt de origem foi registrada em [LaborRules](../legal-rules/labor-rules.md): conservar o prazo literal da fonte oficial e validar a contagem/aplicabilidade antes de ativação. Nenhuma regra legal foi codificada/ativada neste checkpoint.

## Reprodução

Instalação e execução detalhadas no [README](../../README.md). A partir da raiz do Chronos:

```powershell
$env:CHRONOS_RUNTIME_DIR = Join-Path $env:LOCALAPPDATA 'Chronos\1.0'
.\scripts\setup.ps1
.\scripts\check.ps1
# Terminais separados:
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
```

Nesta sessão foi utilizado o runtime isolado abaixo, sem gravar ambientes em outros projetos:

```powershell
$env:CHRONOS_RUNTIME_DIR = 'C:\Users\leand\.codex\visualizations\2026\10\24\01a16f80-a854-7dd2-abbc-ed567dc8b313\chronos-runtime'
```

URLs locais: `http://127.0.0.1:5187` e `http://127.0.0.1:8017/docs`. Servidores usados na verificação foram encerrados ao terminar. A revisão visual/funcional pelo navegador permanece pendente.

## Próxima fase recomendada

**Fase 2 — Backend e persistência:** configuração, PostgreSQL/SQLite leve, SQLAlchemy/Alembic, autenticação/RBAC, entidades principais, endpoints protegidos e importação idempotente da fixture. Ordem, critérios e testes em [plano da Fase 2](../roadmap.md). Nenhum deploy, envio externo de negócio ou alteração em outro projeto foi realizado.
