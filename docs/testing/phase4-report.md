# Chronos 1.0 — Relatório da Fase 4

Data: 24/10/2026. Entrega local, limitada ao projeto Chronos e ao runtime isolado da tarefa. Nenhuma publicação ou integração externa de negócio foi realizada.

Calendário semanal/mensal, cadastro de plantões/intervalos, indisponibilidades e critérios LaborRules implementados e verificados por testes e HTTP. **Inspeção visual real em navegador continua pendente**, conforme bloqueio de automação registrado na Fase 1. Não foi tentado contorno por outra ferramenta de navegação.

## Entrega

- Calendário com filtros de unidade/setor/pessoa, semana/mês e datas no fuso da unidade. Horários civis inexistentes ou ambíguos são recusados.
- Plantões manuais e pausas remuneradas/não remuneradas; prévia obrigatória, confirmação explícita de rascunho com alertas, idempotência, revisão, edição e cancelamento preservando histórico.
- Consulta/cadastro de indisponibilidade pela pessoa selecionada, com permissão de RH adequada. Não há edição/exclusão dessas declarações nesta fase.
- Cinco critérios de regra tipados, escopo por organização/unidade/função/contrato/instrumento, vigência, fonte, evidência e versão. Sucessão explícita de regras imutáveis, sem escolher automaticamente a maior versão nem alterar avaliações já salvas.
- Cálculos de trabalho e base remunerável, divisão por dia local, semana civil, histórico anterior/posterior, descansos e intervalos. Contratos, situação ativa, sobreposição, indisponibilidade, competências e validade/comprovação de habilitações da função geram achados próprios.
- Quatro resultados previstos com evidências individuais. Violação conhecida continua visível mesmo com regras ausentes, pendências ou conflitos.
- Configuração de hipóteses de ciclos/jornadas; não gera plantões nem autoriza juridicamente um regime pelo nome.
- Sexta migration Alembic; 26 tabelas, FKs por organização, novas permissões e auditoria transacional. Restauração da demonstração contempla calendário e cadeias de versões.

Detalhes e limites por avaliador: [arquitetura da Fase 4](../architecture/phase4.md). Fontes oficiais consultadas e condições de revisão: [fontes](../legal-rules/phase4-sources.md). O Prompt Mestre e a fixture original foram preservados e seus validadores executados novamente.

## Validação

| Verificação | Resultado final |
|---|---|
| Backend SQLite + PostgreSQL real | 92 passed, 0 failed, 0 skipped, 1 warning; 182,29 s |
| Frontend Vitest/JSDOM | 29 passed, quatro arquivos; 37,55 s |
| TypeScript/Vite | Aprovado; 2.337 módulos; 20,65 s |
| Integridade do Prompt Mestre e fixture | Aprovada; 350 colaboradores e 19 setores |
| HTTP real via proxy Vite/FastAPI | Aprovado; servidores próprios encerrados |
| Prontidão com banco local migrado | HTTP 200; esquema 006; conferência por TestClient |
| Inspeção visual no navegador | Pendente pelo bloqueio já registrado |

Resultados consolidados em [phase4-checks.json](phase4-checks.json). Arquivos alterados em [manifesto](phase4-file-manifest.md). O backend foi executado nos perfis SQLite e PostgreSQL 17.11 real, com schemas de teste separados; frontend em Vitest/Testing Library/JSDOM, além do build TypeScript/Vite.

Casos adicionais: quatro estados de conformidade; fronteiras de vigência; virada de dia local; intervalo contíguo e remuneração de pausa; histórico antes/depois; carga semanal; indisponibilidade; limites de escopo; revisão obrigatória; prévia expirada; idempotência; avaliações preservadas após novas regras; sucessão explícita; configuração de ciclo; restauração de versões com FKs. As regressões anteriores de autenticação/RBAC/cadastros permanecem incluídas.

Na interface, testes verificam avaliação antes de gravar, digest recebido, invalidação ao editar campo, erro de prévia expirada sem perder formulário, pausas dinâmicas, edição com pessoa/revisão preservadas, evidência obrigatória de revisão e consulta mensal no fuso da unidade. Conversões de horário verificam também transições de horário de verão e fevereiro bissexto.

Integração HTTP real (`backend/scripts/smoke_phase4.py`) usa FastAPI e proxy Vite próprios em loopback, banco sintético separado e conta/segredo efêmeros. Login e cookies, alteração de dashboard 350→351, regra 201, prévia 200, prévia antiga 409, rascunho 201, consulta mensal com um plantão, cancelamento 200, dois snapshots, refresh 200, logout 204 e acesso antigo 401. Servidores encerrados no `finally`. Esse teste não usa navegador nem altera o banco principal.

Avisos conhecidos: depreciação Starlette/httpx no backend e comentários de tree-shaking de Zod removidos pelo Rollup; não impediram os testes/builds. A tentativa de redirecionar toda a execução do PostgreSQL portátil para arquivo reteve seu pipe e não chegou aos testes. O comando próprio foi interrompido, a instância encerrada e a execução repetida sem esse redirecionamento.

## Banco local e execução

Banco principal migrado de 005 para `006_calendar_rules`, sem restauração de dados. Seed repetida confirmou preservação dos registros. Conferência posterior: **350 colaboradores, 19 setores, zero plantões e zero regras**. Prontidão da aplicação conferida com TestClient no banco local: HTTP 200, fase 4, SQLite, esquema 006. Não foi criada conta/senha padrão.

A tentativa de backup anterior à migration falhou por tratar um campo protegido de configuração como texto; a migration subsequente foi aplicada. Não existe backup pré-migração produzido por essa etapa. Após conferência, foi salvo `chronos-after-phase4-006.sqlite3` no runtime fora do OneDrive. Trata-se explicitamente de backup **posterior** à migration.

Executar pelos scripts existentes no README. O menu Calendário começa vazio; escolha uma data/unidade e cadastre um plantão para avaliar. Jornadas e regras permite hipóteses e versões com fontes. Não ativar supostos limites universais para demonstrar o hospital.

## Pendências e próxima fase

QA visual/responsividade em navegador permanece pendente. Aprovação/publicação de escala, demanda por atividade e dimensionamento de cobertura 24x7, geração de escalas, OR-Tools e n8n continuam nas fases correspondentes. Não há folha ou conformidade jurídica completa, interpretação automática de instrumentos coletivos, regras completas de domingos/feriados ou banco de horas.

A próxima etapa é a Fase 5: cenários, capacidade e simulador financeiro, com premissas versionadas, cálculos monetários exatos e permissões financeiras. Plano em [roadmap](../roadmap.md). Este checkpoint continua sem prontidão de produção.
