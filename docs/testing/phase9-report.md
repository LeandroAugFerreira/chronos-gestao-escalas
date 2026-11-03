# Chronos 1.0 — Relatório da Fase 9

Data de referência: 2026-10-26. **Checkpoint técnico entregue; aceite final de produção pendente.** A partida do n8n segue bloqueada por avisos de segurança, e a inspeção de navegador e Power BI Desktop não foi concluída. Nenhuma publicação foi realizada.

## Resultado

A fase acrescentou limites HTTP, configurações e respostas mais restritas, correção da revisão persistente de jornadas, recuperação isolada e validação do fluxo entre módulos. [Arquitetura](../architecture/phase9.md), [achados](../security/phase9-findings.md) e [recuperação](../operations/recovery.md) detalham decisões e limites.

O teste integrado revelou erro real no endpoint de revisão: `WorkPattern.revision` era incrementado sem existir no modelo. A solução mantém esse controle e adiciona a coluna com migration. Uma proposta inicial de remover o incremento foi rejeitada pela revisão automática e não foi executada. O teste final verifica revisão nova, incremento persistente e recusa de digest obsoleto, inclusive quando a jornada já estava validada.

## Validações executadas

| Controle | Evidência |
|---|---|
| Backend completo | **253 testes aprovados**, SQLite e PostgreSQL reais; zero falhas e zero skips |
| Casos da Fase 9 | 35 testes aprovados nos dois bancos; matriz de seis papéis, limites/framing/timeout, perfil de produção, falhas, revisão, fluxo integrado e recuperação |
| Frontend | **62 testes aprovados** com Vitest 5.0.5, em 8 arquivos |
| Build | TypeScript + Vite aprovados; 2.345 módulos, 10,00 s; mesmos chunks da aplicação |
| HTTP real | Proxy Vite → FastAPI, cookies/CSRF/refresh/logout, cadastros, calendário, cenário, financeiro, CLI do worker, analytics, CSV/XLSX e hashes aprovados |
| Aprovação e persistência | Teste ASGI/API com OR-Tools real, autoaprovação recusada, aprovação por segundo usuário, automação local e leitura após nova instância da aplicação |
| SQLite | Backup consistente, hash/manifest, restauração em destino novo, integridade/FKs e suspensão de efeitos verificados |
| PostgreSQL | `pg_dump`/`pg_restore` nativos para banco novo descartável; contagens/digest, revogação de sessões/chaves e preservação da origem conferidos; limpeza apenas da base criada pelo teste |
| Recuperação final | Dois casos SQLite/PostgreSQL repetidos pelo script portátil, que agora configura automaticamente os binários nativos |
| Banco principal | Backup pré-010, restauração e migration da cópia antes de migrar o principal; head **010_pattern_revision**, 41 tabelas, integridade ok |
| Preservação de dados | Hashes de **todas as colunas anteriores de todas as 41 tabelas** iguais antes/depois; 350 pessoas, 19 setores, 20 indisponibilidades; sete rotinas desativadas |
| Excel nativo | Arquivo sintético aberto em nova instância invisível, somente leitura, macros desativadas e links não atualizados; recálculo completo e indicadores de população/financeiro conferidos; original não salvo |
| Identidade/fixture | Chronos 1.0, Prompt Mestre/SHA-256 e fixture reproduzível verificados; sem instalação global |

O smoke HTTP cria uma pessoa extra **somente no banco sintético isolado**, por isso mede 351 pessoas nesse cenário de transporte. O banco principal permanece com 350. O smoke conserva premissas pendentes e comprova bloqueio de submissão. A aprovação bem-sucedida é demonstrada separadamente pelo fluxo integrado com revisões explícitas em fixtures de teste. Nenhum desses resultados comprova validade jurídica ou dimensionamento profissional universal.

Os XML e relatórios operacionais ficam no runtime externo ao OneDrive. [phase9-checks.json](phase9-checks.json) reúne evidências públicas, contagens e hashes sem credenciais ou dados pessoais. Retentativas e casos repetidos não aumentam a contagem de 253.

## Auditoria de dependências e mitigação

- Frontend inicial: 3 itens no npm audit, sendo 2 críticos e 1 moderado. Vitest atualizado de 3.2.7 para 5.0.5; auditoria final: **zero itens conhecidos**. Testes e build repetidos.
- Python: `pip-audit` consultou as **47 versões fixadas**, sem itens conhecidos e sem pacotes ignorados. O scanner foi instalado em venv separado, sem alterar dependências da aplicação; `pip check` passou.
- n8n: árvore 2.44.6 com **175 itens** (3 baixos, 78 moderados, 82 altos, 12 críticos). Candidata mais recente consultada, 2.44.7, manteve a mesma contagem no lockfile de teste. Ela não foi instalada ou executada. Contagens incluem propagação pela árvore e não equivalem a CVEs distintas ou exploração demonstrada.

Setup, partida gerenciada, smoke histórico e configuração development do n8n foram bloqueados. A checagem do script confirmou recusa antes de iniciar qualquer processo. Runtime e workflows existentes foram preservados. O consumidor local A01–A07 permanece funcional e foi usado na validação integrada. Nenhum downgrade automático ou override em massa foi aplicado. A auditoria e o bloqueio constam de `automation/n8n/security-status.json`.

## Correções durante os testes

As primeiras tentativas do teste integrado expuseram campos obrigatórios não preenchidos na fixture e, depois, o erro real de revisão de jornadas. Os dados sintéticos foram corrigidos e a coluna persistente adicionada; a suíte completa passou. Migrations foram testadas em ida/volta e comparadas ao modelo nos dois bancos. Os scripts PowerShell alterados tiveram sintaxe validada.

Na recuperação, sessões antigas da cópia deixam de autenticar, chaves/rotinas ativas são desabilitadas e efeitos pendentes são cancelados. A origem permanece ativa/intacta no teste, demonstrando que a política foi aplicada somente à restauração. Nenhum processo de teste ficou deliberadamente ativo após as verificações.

## Bloqueios e próximo aceite

1. **n8n:** exige remediação/revisão da árvore e repetição dos quatro workflows antes de nova liberação. Evidências reais da Fase 7 continuam históricas; não foram reutilizadas como aprovação atual.
2. **Navegador:** automação visual continua bloqueada pelo controle anterior; não houve tentativa de contorno por outro navegador, CDP ou Playwright. JSDOM/HTTP/build não substituem inspeção de teclado, temas e responsividade em navegador real.
3. **Power BI Desktop:** não executado. Dataset/consultas/medidas permanecem preparação local; não há PBIX, conta, gateway ou publicação.
4. **Produção:** TLS/proxy, distribuição, infraestrutura, recuperação operacional e revisão final precisam de aceite próprio. Os testes de backup são cópias isoladas; não houve troca de banco operacional por uma restauração.

`release_ready=false`, `published=false` e `acceptance=pending_security_and_visual_gates`. A Fase 10 e a publicação não ficam liberadas por este checkpoint.
