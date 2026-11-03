# Chronos 1.0 — Relatório da Fase 2

Data: 24/10/2026. Projeto exclusivo: `C:\Users\leand\OneDrive\Projetos\Chronos`.

**Backend e persistência implementados e validados em SQLite e PostgreSQL real.** A entrega continua como checkpoint de desenvolvimento Chronos 1.0. O frontend operacional é a próxima fase; regras trabalhistas, calendário, financeiro, OR-Tools e automações permanecem nas fases previstas.

## Entrega efetiva

- Configuração Pydantic Settings com segredos mascarados, leitura de `.env`, validação de ambiente, segredo JWT sem fallback e SQLite explicitamente habilitado somente em desenvolvimento/teste.
- SQLAlchemy 2, psycopg e quatro migrations Alembic, com 23 tabelas: organização/identidade, RBAC, sessões e limite de login, estrutura/catálogos, pessoas/contratos/habilidades/qualificações/disponibilidade, auditoria e idempotência.
- FKs compostas por organização; vínculo pessoa/setor/unidade validado também pelo banco. Consultas recebem o tenant do principal autenticado e escopo por permissão/unidade.
- Argon2id; access JWT com algoritmo/issuer/audience/claims fixos; refresh opaco com hash persistido, rotação e detecção de reutilização. Logout e reutilização de refresh revogam a família e os tokens de acesso associados.
- Seis perfis implementados. Salários fora da listagem de pessoas e protegidos por permissão financeira; usuários com leitura agregada não recebem dados individuais.
- Endpoints protegidos de estrutura, catálogos, pessoas, contratos, competências, qualificações, disponibilidade, usuários, papéis e auditoria. Paginação, busca, filtros, ordenação controlada e edição de nome/status com revisão otimista.
- Criações auditadas na mesma transação, idempotência por tenant/ator/rota/chave, erro padronizado sem eco de senha/SQL e correlação por requisição.
- Seed idempotente e transacional: 350 pessoas, 19 setores, 38 funções e relacionamentos. Restauração explícita somente para a organização demo esperada, preservando acessos, unidades e auditoria.
- CLI de configuração/migration/seed/admin/restauração, scripts PowerShell, Compose PostgreSQL opcional e documentação OpenAPI/execução. `health/ready` verifica o schema esperado.
- Frontend anterior preservado e compilado. Ele ainda lê a fixture pública da Fase 1; não recebe a alegação de ser um dashboard conectado ao banco.

Arquivos e áreas alterados estão no [manifesto desta fase](phase2-file-manifest.md). O anexo do usuário e o Prompt Mestre consolidado permaneceram intactos.

## Verificações executadas

| Verificação | Resultado observado |
|---|---|
| Suite final pelo script portátil | **52 passed, 1 warning in 45.09s**, sem skipped |
| Perfis da suite | SQLite em arquivo e PostgreSQL **17.11 real**, com schema exclusivo por teste |
| Migrations | Upgrade até `004_idempotency`, comparação schema/modelo, downgrade completo e novo upgrade, nos dois bancos |
| Persistência | Nova engine mantém registros; seed repetida não duplica; importação inválida faz rollback |
| Segurança | JWT inválido/vencido/claims, refresh/replay/logout, usuário inativo, limite persistente, RBAC e escopos, salários, tenant/FKs, entradas e erros seguros |
| Operações | Criação, edição/revisão concorrente, paginação/filtros, auditoria atômica, idempotência e validações temporais/contratuais |
| CLI local | `init-local`, `migrate`, `seed-demo` e segunda execução idempotente concluídos no banco local |
| HTTP real Uvicorn | `health/ready`: 200, SQLite, revisão 004; `/employees` sem Bearer: **401**; fixture: 350 pessoas; OpenAPI: versão 1.0 |
| Frontend | TypeScript/Vite aprovados, 86 módulos; build Vite em 4.05s |
| Dependências | `pip check`: No broken requirements found; lock atualizado |
| Scripts | Sintaxe PowerShell validada; script portátil efetivamente iniciou PostgreSQL, executou testes e encerrou o servidor |
| Preservação | Hash do prompt consolidado validado; `.env`, dependências e builds ignorados; nenhum remote/push/publicação |

O aviso restante é a depreciação do uso de httpx no Starlette TestClient. Não produziu falha e permanece uma tarefa de manutenção de dependências. O aviso Alembic de `path_separator` da primeira rodada foi corrigido.

## PostgreSQL sem instalação global

Docker/psql não estavam disponíveis no PATH nem havia instalação PostgreSQL detectada. Para não tratar SQLite como prova de PostgreSQL, foi utilizado o ZIP oficial **PostgreSQL 17.11**, distribuído pela EDB e referenciado por PostgreSQL.org. Somente bin/lib/share foram extraídos no runtime do Chronos; nenhum serviço Windows, PATH global, outro projeto ou servidor existente foi alterado.

Origem: [EDB — binários PostgreSQL](https://www.enterprisedb.com/download-postgresql-binaries), pacote `postgresql-17.11-5-windows-x64-binaries.zip` (381.531.864 bytes). SHA-256 observado do download: `80379b2c04d51c30225532e0ae04509899141e9957ed096fe749d7fd9df8f82f`. Esse hash registra o artefato utilizado, sem alegar comparação com checksum independente publicado pelo fornecedor.

Cluster exclusivo `chronos_test`, bind `127.0.0.1:5547`, SCRAM-SHA-256, shared_buffers 32 MB, até 20 conexões. A suite aceita somente banco terminado em `_test` e cria/remove schemas próprios `chronos_test_<uuid>`. O servidor foi encerrado ao finalizar. A credencial de teste fica somente no arquivo de ambiente do runtime, sem ser exibida ou versionada; o `.env` principal conserva apenas o perfil local normal.

## Limites e pendências explícitas

- Docker Compose foi preparado, mas **não foi executado**, pois Docker não está instalado. A validação PostgreSQL real foi feita com o servidor portátil.
- Não houve navegação/inspeção visual nesta fase. A ferramenta havia bloqueado a aquisição da aba na Fase 1; não se tentou contornar. O frontend não foi promovido a uma interface de login/CRUD nesta entrega.
- Primeiro administrador do banco local deve ser criado com senha escolhida pelo usuário. Não existe senha padrão ou credencial pessoal inventada. Login/criação de usuários foram testados com contas sintéticas isoladas; as senhas desses testes não são acessos do banco local.
- Não há RLS, endurecimento de produção, teste de carga/concorrência distribuída, retenção automática, revisão visual de acessibilidade ou deploy. Essas verificações seguem no plano de segurança/qualidade.
- A edição de pessoas nesta fase cobre nome/status; edição de unidades/setores, transferência de lotação e telas administrativas serão completadas conforme exigência da Fase 3. Organizações não são criadas por cadastro público.
- A avaliação temporal impede registros inconsistentes/sobrepostos, mas **não avalia validade jurídica de jornadas**. Credenciais e quantitativos são sintéticos, sem comprovação de dimensionamento, habilitação real ou cobertura assistencial.
- Custos, calendário, LaborRules executável, OR-Tools, aprovações e workflows n8n não foram implementados nem apresentados como funcionando.

## Como executar

O runtime já preparado nesta sessão é:

```powershell
$env:CHRONOS_RUNTIME_DIR = 'C:\Users\leand\.codex\visualizations\2026\10\24\01a16f80-a854-7dd2-abbc-ed567dc8b313\chronos-runtime'
# Criar seu acesso, escolhendo a senha no terminal:
.\scripts\create-admin.ps1
# Em terminais separados:
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
```

Para reprodução em outro runtime: [README](../../README.md). Para repetir a suite completa com PostgreSQL portátil já preparado:

```powershell
.\scripts\test-portable-postgres.ps1
```

Esse script inicia e encerra o servidor quando ele não estava ativo. O check normal sem perfil PostgreSQL executa SQLite e registra a sentinela PostgreSQL como skipped, em vez de afirmar equivalência. Detalhes em [execução e testes](phase2.md).

## Próxima fase

**Fase 3 — Frontend:** login/sessão segura, layout/componentes, gestão de colaboradores/unidades/setores, formulários e dashboard conectado ao banco. O [plano concreto](../roadmap.md) preserva os limites desta fase e os critérios de validação. Nada foi publicado e nenhum outro projeto foi modificado.
