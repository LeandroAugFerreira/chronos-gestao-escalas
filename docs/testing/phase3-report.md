# Chronos 1.0 — Relatório da Fase 3

Data: 24/10/2026. Trabalho restrito ao projeto Chronos e ao runtime isolado da própria tarefa. A entrega permanece local, sem publicação.

**Frontend integrado implementado e testado em componentes/HTTP. A validação visual em navegador permanece pendente.** As funções de calendário, LaborRules executável, simulação financeira, OR-Tools e n8n não foram iniciadas nesta fase.

## Entrega efetiva

- Login visual, restauração de sessão, logout, guardas de rota e mensagens de expiração/permissão/rede.
- Refresh em cookie HttpOnly com SameSite=Strict, CSRF assinado ligado à família, verificação de origem e exigência de Secure/HTTPS em produção. Access token somente em memória.
- Sidebar, breadcrumb, identidade temporal corporativa neutra, tema dark/light, preferências persistidas, navegação móvel e tratamento de carregamento/erro/vazio.
- Dashboard consultando o banco: ativos/inativos, setores, unidades, média de jornada contratual, gráficos por setor/grupo e distribuição de jornadas vigentes, com origem/data e filtro por unidade.
- Gestão de colaboradores com busca, filtros, ordenação, paginação, criação, edição, ativação/inativação e transferência de lotação autorizada. Detalhes de qualificação, disponibilidade e contratos com dados salariais restritos.
- Gestão de unidades/setores com criação/edição e revisão; catálogos de funções/competências/qualificações; jornadas de referência somente leitura.
- Listagem/criação de acessos autorizados e consulta de auditoria. Não há exclusão pública, redefinição de senha ou edição de perfis existentes nesta entrega.
- Formulários RHF/Zod, erros associados aos campos, idempotência de criação, revisão otimista e bloqueio de alteração enquanto salva. Modal com foco/teclado.
- Migration 005 aplicada no banco local sem restauração dos dados: revisão nos catálogos. Modelo permanece com 23 tabelas e cinco migrations.

Os módulos futuros aparecem como não calculados/não avaliados, sem resultados simulados apresentados como cálculo real. O frontend deixou de consultar a fixture pública nas telas operacionais.

Lista de arquivos adicionados/atualizados e remoção do cliente antigo de fixture: [manifesto da Fase 3](phase3-file-manifest.md). Os arquivos privados do ambiente e bancos de teste estão excluídos.

## Validações executadas

| Validação | Resultado |
|---|---|
| Backend completo, SQLite e PostgreSQL 17.11 real | **68 passed, 1 warning in 95.58s**, sem skipped |
| Novos testes da API da Fase 3 | Cookie/CSRF, origem, Secure, rotação/logout, sessão substituída, dashboard reconciliado, escopos e revisão; executados nos dois bancos na suite completa |
| Frontend Vitest/Testing Library/JSDOM | **21 passed**, três arquivos; execução final em 16.89s |
| TypeScript/Vite | Build aprovado; 2.334 módulos; build final registrado em 13.39s |
| Pacotes de saída | Entrada ~464,64 kB; dashboard/gráficos em chunk separado ~371,60 kB; CSS ~24,43 kB, antes de gzip |
| HTTP real via proxy Vite → FastAPI | Login 200, criação 201, dashboard passou de 350 para 351, refresh 200, logout 204 e acesso após logout 401 |
| Cookie no teste HTTP | HttpOnly confirmado; refresh ausente no JSON web; cookie removido após logout |
| Banco usado pelo smoke HTTP | Arquivo SQLite sintético independente; banco principal não foi modificado pelo smoke |
| Ambiente local principal | Migration 004 → 005 aplicada; frontend HTTP 200; prontidão via proxy confirmou fase 3 e schema 005_catalog_revisions |
| Preservação | Prompt/fixture mantidos; outros projetos intactos; sem deploy ou integração externa de negócio |

Os testes de frontend exercitam login inválido, rotas anônimas, validação/criação/edição, conflito de revisão, bloqueio durante salvamento, falha de rede, filtros/paginação, menus/permissões, tema, sessão em memória, single-flight, troca de identidade e logout. Os gráficos são mockados nos testes de página; esses testes não são screenshots nem inspeção visual.

O script `backend/scripts/smoke_phase3.py` cria banco/conta sintéticos separados, inicia seus próprios servidores em loopback e os encerra em `finally`. Senha de teste e chaves ficam em memória, sem impressão ou arquivo de credenciais. O teste usa HTTP, sem controlar navegador.

## Ajustes observados durante a validação

A tipagem do Web Locks foi corrigida para achatar a promessa; uma asserção de teste foi ajustada porque a organização aparece no sidebar e no card. A divisão do dashboard em importação dinâmica eliminou o aviso de chunk de entrada acima de 500 kB. Foram acrescentados labels/erros associados e bloqueio dos campos durante o salvamento, com teste específico.

Restam avisos de dependências: Starlette TestClient/httpx no backend e duas anotações de comentários do Zod removidas pelo Rollup durante build. Nenhum desses avisos causou falha. Não foram ocultados para simular um resultado limpo.

Durante alterações com o servidor de desenvolvimento ativo, Vite invalidou o Fast Refresh de módulos que também exportam helpers (`dateTime`/`roleLabels`), recarregando os importadores. É uma limitação da atualização durante edição, sem falha no build de produção. Os servidores de prévia e PostgreSQL de teste foram encerrados ao finalizar a entrega.

## Limites explícitos

- **Não houve navegação nem revisão visual real.** A ferramenta de navegador havia recusado a aquisição da aba na Fase 1. Não se tentou contornar o bloqueio; a prévia foi apenas disponibilizada pelo painel, sem alegar que foi observada. Responsividade, contraste, gráficos renderizados e comportamento em dispositivos precisam de revisão visual futura.
- O primeiro acesso no banco principal exige criar um administrador com senha escolhida pelo usuário, via script existente. Não foi inventada senha padrão. Contas usadas nos testes são isoladas.
- Web Locks/BroadcastChannel têm fallback quando ausentes; comportamento de múltiplas abas em navegadores reais não foi validado visualmente. Identidade e revogação continuam verificadas no servidor.
- O dashboard apresenta cadastro/vínculos, não cobertura, custo projetado ou conformidade. Quantitativos e salários são fictícios; não estabelecem mínimos profissionais.
- Administração de acessos nesta fase cria/lista contas; redefinição de senha, edição de perfis, upload/importação pela interface e relatórios exportáveis permanecem incrementos posteriores. Dados sensíveis reais não são necessários.
- A avaliação de jornada e a manutenção de escalas aprovadas não existem ainda. Transferência cadastral não certifica habilitação ou validade trabalhista.
- Docker/deploy, teste de carga, auditoria completa de produção e recuperação operacional não foram executados nesta fase.

## Execução local

Na raiz do Chronos, usando o runtime já preparado:

```powershell
$env:CHRONOS_RUNTIME_DIR = 'C:\Users\leand\.codex\visualizations\2026\10\24\01a16f80-a854-7dd2-abbc-ed567dc8b313\chronos-runtime'
# Se ainda não criou seu acesso:
.\scripts\create-admin.ps1
# Em dois terminais:
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
```

Abra `http://127.0.0.1:5187`. Organização: `horizonte`; usuário inicial: `admin`; senha: a escolhida no terminal. Instalação nova e verificações no [README](../../README.md).

Para reproduzir o backend nos dois bancos: `scripts/test-portable-postgres.ps1`. Frontend: `npm test` e `npm run build` dentro de `frontend`. Smoke HTTP: executar `backend/scripts/smoke_phase3.py --runtime <pasta-fora-do-OneDrive>` com Python do venv; requer portas 8017/5187 livres e encerra somente seus processos.

## Próxima fase

**Fase 4 — Jornadas, calendário e LaborRules:** regras versionadas e aplicáveis por contrato/categoria/vigência, validação de descansos, calendário de jornadas e alertas. O plano está em [roadmap](../roadmap.md). O release continua identificado como Chronos 1.0 em desenvolvimento; nada foi publicado.
