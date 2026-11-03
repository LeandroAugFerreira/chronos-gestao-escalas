# Chronos 1.0 — Cobertura e limites para revisão

Esta matriz liga o [escopo original](../requirements/requirements.md) a implementações e evidências. Não substitui o Prompt Mestre nem elimina exigências pendentes. “Implementado com limites” não significa aceite de produção ou validação integral por interface.

| Requisito | Entrega/evidência | Limite ou próxima verificação |
|---|---|---|
| RF01 Dashboard | Cadastros da API, filtros e indicadores por seleção em analytics; Fases 3/8/9 | Nem todas as séries/evoluções estão consolidadas em um painel; QA visual pendente |
| RF02 Estrutura configurável | Unidades, setores, cargos e vínculos persistidos; isolamento de organização/unidade testado | Onboarding/autosserviço completo de novas organizações não foi entregue; org demo é importada pela fixture |
| RF03 Pessoas | Cadastro/consulta, criação de contratos/qualificações/competências pela UI, ausências, exportação básica CSV autorizada por filtros e importador idempotente da fixture; homologações de 27/10 | Edição/exclusão ampla de vínculos, encerramento contratual, importação genérica de arquivos e exportação dos vínculos especializados ainda pendentes |
| RF04 Jornadas | Ciclos configuráveis, turnos, pausas, indisponibilidade e avaliação de calendário | Modalidades são hipóteses parametrizadas; não há validade jurídica automática pelo nome |
| RF05 Cenários | Versões congeladas, capacidade mensal, demanda e comparação | Capacidade não comprova cobertura; hipóteses 44/42/40/4x3 exigem entradas/revisão próprias, não são resultados pré-validados |
| RF06 Solver | CP-SAT, restrições, habilitações, contexto temporal, lacunas e verificador independente; testes reais | Não comprova cobertura de todos os 19 setores; objetivos e casos operacionais precisam de dimensionamento/revisão específicos |
| RF07 Financeiro | Centavos/Decimal, 12 meses, fontes, parcelas, comparação/sensibilidade e salários preservados | Projeções não são gastos observados; categorias ausentes são explícitas; ganhos não medidos ficam indisponíveis |
| RF08 Automações | A01–A07, outbox, consumidor/scheduler opcional, histórico e retentativas testados | Defaults desativados; notificações internas; sem envio externo automático |
| RF09 Governança | Proposta versionada, submissão, rejeição, aprovação por segundo responsável e substituição controlada | Publicação interna final não está concluída/liberada; não há publicação externa nem gravação automática de todos os turnos |
| RF10 Analytics/BI | Relatórios selecionados, CSV/XLSX, grãos, hashes, permissões; Excel e ferramenta de artefatos conferidos | Dataset Power BI é preparação local; Desktop/DAX nativos e painel BI final não validados |
| RF11 LaborRules | Cinco famílias tipadas, vigência/escopo, fontes/revisão e quatro estados de avaliação | Não implementa toda hipótese normativa possível; regras e instrumentos específicos dependem de revisão, sem certificação jurídica |
| RF12 Administração | JWT/refresh/CSRF, seis papéis, campos/unidades, auditoria e testes de isolamento | Operação de produção, gestão de segredos e revisão final não liberadas |
| RF13 Explicações | Fallback determinístico gratuito e baseado nas tabelas autorizadas | Sem adaptador LLM ativo; IA não decide cálculos ou aprovação |
| RF14 n8n | Quatro workflows e execução real histórica na Fase 7 | **Bloqueado atualmente** por auditoria de dependências; requer árvore corrigida e nova execução dos workflows |
| RNF01/02/05 | Stack/modelo modular, UTC/fuso, minutos inteiros, cálculos exatos e regras configuráveis | Validações por fase não equivalem a operação hospitalar real |
| RNF03/06 | Escopos, limite HTTP, erros, correlação, idempotência, workers e recuperação | Não é teste de intrusão/certificação de segurança |
| RNF04 | Fixture sem paciente/CPF, minimização e segredos fora do pacote | Política institucional completa de retenção/exclusão e automação de expurgo não foram entregues |
| RNF07 | Identidade temporal, temas e testes de componentes | Navegador real, contraste, teclado, responsividade e capturas ainda pendentes |
| RNF08/09 | Setup local, runtime fora do OneDrive, testes registrados, pacote verificável | Dependências precisam ser instaladas; ZIP não inclui runtime/banco; testes históricos conservam data/escopo |
| RNF10 | Nenhuma publicação, envio a terceiros ou mudança em outro projeto | Publicação futura exige autorização explícita após revisão |
| RNF11 | Paginação, filtros, OpenAPI no desenvolvimento, erros e logs operacionais | Retenção/configuração operacional completa de logs permanece revisão de produção |

Fontes de evidência: [exportação cadastral](../testing/people-export-2026-10-27-report.md), [homologação de 27/10](../testing/homologation-2026-10-27-report.md), [Fase 9](../testing/phase9-report.md), [Fase 8](../testing/phase8-report.md), [caso](case-study.md), código/testes e [estado da entrega](../release/status.json). Itens parciais exigem decisão de escopo/implementação antes de qualquer declaração de conformidade integral do produto.
