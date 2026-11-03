# Chronos 1.0 — Segurança na Fase 9

Revisão em 2026-10-26. O resultado é um checkpoint de desenvolvimento, não uma certificação de segurança ou autorização de publicação.

## Corrigido e coberto por testes

| Achado | Correção |
|---|---|
| Avisos nas ferramentas de teste do frontend: 2 itens críticos e 1 moderado no npm audit | Vitest 3.2.7 → 5.0.5 e árvore associada; auditoria final sem avisos conhecidos; suíte e build repetidos |
| API sem limite geral do corpo antes do parsing | Limite padrão de 1 MiB e prazo de 10 s; rejeição de tamanho declarado/incremental excessivo, framing divergente e compressão não suportada |
| Proteções de resposta incompletas | nosniff, DENY, no-referrer, Permissions-Policy e erros no-store correlacionados; falha inesperada não devolve traceback ao cliente |
| Configuração aceita origens inválidas | Origens HTTP(S) explícitas, sem curingas/caminhos/credenciais; produção exige HTTPS, cookie Secure e fecha docs/OpenAPI públicos |
| Revisão de jornada provoca erro 500 | WorkPattern usava revision sem coluna correspondente; migration 010_pattern_revision adiciona/preserva a revisão. Digest e trava de organização continuam ativos; revisão baseada em digest antigo é recusada |
| Recuperar um banco antigo pode reativar sessões, chaves e efeitos pendentes | Restauração somente em diretório novo, com integridade/hash; revoga sessões, desabilita chaves/rotinas e cancela jobs/entregas pendentes, preservando dados e decisões históricas |

A alteração inicialmente considerada de remover o incremento de revisão foi rejeitada pela revisão automática. Ela não foi executada. A solução adotada mantém o incremento e cria a coluna persistente, com migration e testes nos dois bancos.

## Bloqueio do n8n opcional

O `npm audit` do lockfile n8n 2.44.6 encontrou 175 itens: 3 baixos, 78 moderados, 82 altos e 12 críticos. A versão mais recente consultada, 2.44.7, foi resolvida **somente como lockfile em pasta de teste**, sem instalação/partida, e manteve a mesma contagem. Há avisos transitivos e itens propagados pela árvore; essa quantidade não representa 175 CVEs distintas nem comprova exploração no conjunto restrito de nós usado pelo Chronos.

O downgrade para 1.17.0 sugerido pelo resolvedor não foi aplicado. Overrides em massa também não foram aplicados: poderiam quebrar dependências e não demonstrariam segurança dos workflows.

`automation/n8n/security-status.json` registra o bloqueio. Setup, partida gerenciada e o smoke histórico n8n recusam execução. A configuração `development` rejeita integração n8n enquanto o bloqueio permanecer. O modo `test` permite testar contratos/retentativas com receptores sintéticos e mocks; isso não aprova nem inicia o runtime n8n. Produção continua recusando esta integração local.

O runtime instalado, seus dados e os quatro workflows foram preservados. A evidência real da Fase 7 continua histórica, não é apresentada como uma nova execução aprovada. O consumidor local A01–A07 permanece disponível e foi usado no fluxo integrado. Nenhum envio externo ou ativação no banco principal foi feito.

Para liberar n8n, revisar uma árvore corrigida, verificar todos os avisos aplicáveis e repetir importação/execução dos quatro workflows em ambiente isolado. O campo de liberação não deve ser alterado apenas para contornar o bloqueio. O release de produção permanece bloqueado enquanto isso e os demais controles obrigatórios não forem concluídos.

## Limites da revisão

`pip-audit` consultou as 47 versões Python fixadas, sem avisos conhecidos e sem instalar dependências no venv da aplicação. O scanner fica num venv separado. Auditoria de versões não é teste de intrusão nem prova ausência de vulnerabilidades. Os relatórios brutos ficam no runtime privado; evidências públicas contêm contagens, versões e hashes.

Foi executada matriz dos seis papéis, testes de tenant/unidade/campo, sessões/CSRF/reuso/revogação, worker/outbox/retentativas e exportações. Testes anteriores permanecem parte da regressão. A migração de revisão não revalida jornadas, salários ou regras; snapshots e decisões históricas não são reescritos. Revisões antigas podem exigir nova conferência porque o digest atual passa a incluir revision.

QA real de navegador continua pendente por bloqueio anterior de automação visual, sem tentativa de contorno. Excel foi usado em instância invisível nova, com arquivo sintético somente leitura, macros desativadas e sem salvar o original; o recálculo de indicadores de população e financeiro foi conferido. Power BI Desktop não foi executado.

Referências dos avisos corrigidos: [Vitest/mock registration](https://github.com/advisories/GHSA-qxg6-89mg-rqv8), [Tinypool](https://github.com/advisories/GHSA-85c8-ppgw-ccpr) e [migração Vitest](https://vitest.dev/guide/migration/). Implementação de middleware: [FastAPI](https://fastapi.tiangolo.com/tutorial/middleware/).

## Acompanhamento em 27/10/2026

A nova candidata 2.45.4 foi auditada sem instalação ou partida: 8 itens críticos e 81 altos, com bloqueio preservado. Contagens e hashes em [evidência da homologação](homologation-2026-10-27.json). Os resultados acima conservam sua data e escopo históricos.
