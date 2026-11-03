# Chronos 1.0 — Relatório da Fase 7

Data: 25/10/2026. Checkpoint local de desenvolvimento; dados sintéticos e nenhuma publicação externa.

## Entrega

Central de automações com rotinas A01–A07, definições inicialmente desativadas, responsável, agenda opcional, eventos/outbox transacionais, consumidor com leases/retentativas, avisos internos deduplicados, relatórios CSV e sugestões de nova otimização. As sugestões preservam a proposta e preparam uma versão filha para confirmação humana. Nenhuma rotina aprova propostas, ativa regras ou executa recálculo automaticamente.

Integração n8n opcional em loopback com quatro workflows exportáveis, autenticação nas duas direções, credenciais por unidade/ação, revogação, timestamps, recibos e replay protegido. O núcleo funciona sem n8n. Código e limites em [arquitetura da Fase 7](../architecture/phase7.md); operação em [README n8n](../../automation/n8n/README.md).

## Validação executada

| Verificação | Resultado final |
|---|---|
| Backend | 191 casos distintos aprovados, sem falha/erro pendente ou skip |
| Bancos | SQLite em arquivo e PostgreSQL 17.11 real, em schemas exclusivos de teste |
| Frontend | 53 testes aprovados em 7 arquivos; Vitest/Testing Library/JSDOM, 90,59 s na última rodada |
| Build | TypeScript e Vite aprovados; 2.344 módulos, 21,05 s no último build |
| Integração n8n | Quatro workflows realmente importados/ativados em teste local e executados por HTTP, com IDs de execução confirmados na API |
| Runtime opcional | n8n 2.44.6 e Node 24.22.1 portátil com SHA-256 oficial; sem instalação global |
| Migrations | Upgrade/downgrade e comparação de metadata nos dois bancos; head 009_automations, 41 tabelas |
| Banco local | Backup pré-009 e integridade verificados; zero violações de FK; 350 pessoas, 19 setores e 20 indisponibilidades preservados |
| Defaults locais | Sete definições desativadas, nenhuma chave de integração ou execução criada automaticamente |
| Identidade e fixture | Prompt Mestre/SHA-256, Chronos 1.0 e reprodução da fixture verificados |
| Dependências Python | `pip check` sem conflito; requisitos Python não receberam nova dependência nesta fase |
| Scripts Windows | Sintaxe dos três scripts novos validada; setup n8n reconheceu o runtime existente e o preservou |
| Inspeção visual real | Pendente; nenhum navegador automatizado ou screenshot foi usado |

A contagem de backend é a união por identificador dos XML da regressão e rechecagens, sem contar repetições como novos casos. A primeira rodada teve 112 aprovações e 73 erros de preparação no PostgreSQL por nomes duplicados em duas FKs da tabela de avisos. Os nomes de destinatário e ciência foram separados no modelo e migration. O perfil PostgreSQL reexecutado teve 74 aprovações e um erro isolado de conexão/preparo; o mesmo caso passou na rodada posterior de 34 testes, que também verificou os controles finais de acesso. Quatro testes adicionais confirmaram a fronteira de vigência no fuso da unidade e a deduplicação de avisos. Não ficou erro pendente.

No frontend, uma primeira asserção procurava texto que o DOM separa em elementos; foi corrigida para localizar a tabela acessível. A última suite completa passou com 53 testes. Os XML do backend e frontend ficam no runtime externo; `phase7-checks.json` consolida evidências públicas sem credenciais ou payloads privados.

## Casos relevantes

- Auditoria e outbox confirmados/revertidos juntos; envelope não copia nomes, salários, justificativas ou segredos.
- Seed idempotente com sete rotinas desativadas; execução não ocorre por GET ou abertura da central. Manual, evento e timer ficam identificados no histórico.
- Agenda vencida consolida uma ocorrência; não duplica tick após reinício. Lease recuperado troca o token e impede confirmação pelo consumidor antigo.
- Falha temporária mantém backoff e histórico; falha permanente aguarda ação. Retentativa manual preserva a sequência de tentativas. Cancelamento impede consumo da fila.
- Responsável inativo/revogado não produz efeitos. Unidade não autorizada não lê, cancela ou executa outro escopo. Metadados pessoais e de auditoria são restritos ao perfil correspondente.
- A01 aponta insumos alterados sem mudar a proposta; A02 informa lacuna armazenada; A03 notifica outro aprovador ativo e autorizado; A04 gera CSV protegido; A05 não valida regras; A06 sugere outra versão sem trocar a existente; A07 registra rastreabilidade.
- Datas de vigência sem horário usam o fuso da unidade. Avisos inalterados não se duplicam. Registrar ciência não declara o problema resolvido.
- Relatório financeiro não aparece para leitor sem finance:read. Nenhuma lista salarial individual é exportada.
- Credenciais não são recuperáveis por listagem; revogação é efetiva. Token inválido, timestamp antigo, entrega divergente e conteúdo diferente no mesmo request_id são recusados.
- Entrega com HTTP 503 é reprogramada. Sucesso exige recibo autenticado na API; replay não duplica artefato, aviso ou indisponibilidade.

## Execução real do n8n

O smoke criou banco Chronos separado, contas/chaves efêmeras e banco n8n privado no runtime. Importou os quatro exports e duas credenciais de cabeçalho somente no ambiente de teste. As credenciais em claro ficaram em arquivo temporário privado removido após a importação; valores não foram escritos nos exports ou logs públicos.

Os fluxos executados foram **A02, A03, A04 e A06**, com nove recibos de callback e nove identificadores de execução n8n registrados. Também foram exercitadas duas chamadas ao webhook de disponibilidade para testar replay. A chamada sem autenticação foi recusada. A mesma disponibilidade foi criada uma única vez.

Foram solicitadas explicitamente duas otimizações CP-SAT reais: uma proposta apta à submissão com premissas fictícias revisadas no banco de teste, e outra com demanda deliberadamente descoberta. O teste produziu um arquivo de indicadores, quatro avisos internos e duas sugestões de reotimização. O número de jobs automáticos permaneceu zero. A proposta submetida manteve seu conteúdo e estado; não houve aprovação ou publicação automática.

As revisões/limites do smoke são fixtures sintéticas, sem valor normativo. O banco principal não recebeu esses registros. Os workflows só foram habilitados na instância de teste em loopback; os JSON entregues continuam desativados. Os processos próprios foram encerrados e a chave de serviço de teste revogada no teardown. Não há dependência de API paga, Ollama ou envio a canais externos.

## Build e limites

Artefatos do último build, sem gzip: entrada 479,12 kB, central de automações 15,80 kB, otimização 23,78 kB e gráficos compartilhados 365,17 kB. A interface usa os mesmos componentes, sessão e guardas das fases anteriores. JSDOM/HTTP não substituem inspeção visual/responsiva no navegador, ainda pendente pelo bloqueio já registrado na sessão.

Avisos remanescentes: adaptador httpx/Starlette nos testes, comentários de tree-shaking Zod removidos pelo Rollup e avisos de dependências transitivas do n8n. A instalação opcional do n8n baixou 2.343 pacotes em aproximadamente 30 minutos neste host; não é requisito para rodar o núcleo. O perfil local carrega somente Webhook/HTTP Request. Não foi declarado pronto para produção.

## Preservação

Backup `chronos-before-phase7-009.sqlite3` no runtime externo, antes da migration 009. Integridade do backup/banco principal e FKs verificadas. Seed repetida não reimportou pessoas; usuários preservados. Continuam 350 colaboradores, 19 setores e 20 indisponibilidades, sem regras/plantões/cenários/jobs/propostas/revisões ativados automaticamente. Sete definições foram adicionadas, todas desativadas, sem chaves, eventos ou efeitos no banco principal. O adaptador n8n permanece sem configuração nesse banco.

Nenhum outro projeto foi modificado. Nenhum serviço do Windows foi criado. Versão e metadados permanecem **Chronos 1.0**, fase 7, `published=false` e `release_ready=false`.

Próxima fase: analytics, exportações CSV/XLSX ampliadas, dataset Power BI e explicações determinísticas/IA opcional, conforme roadmap da Fase 8. Nenhum desses módulos foi declarado concluído nesta etapa.
