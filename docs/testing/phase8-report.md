# Chronos 1.0 — Relatório da Fase 8

Data: 2026-10-25. Checkpoint de desenvolvimento local, sem publicação. Escopo: analytics por versão, CSV/XLSX, preparação de dataset Power BI e explicações determinísticas gratuitas. [Arquitetura](../architecture/phase8.md) e [instruções Power BI](../integrations/power-bi.md).

## Entrega

A nova área **Analytics e exportações** permite escolher unidade, mês opcional e versão de cenário, acrescentando uma otimização e uma projeção financeira autorizadas da mesma versão. Indicadores distinguem orçamento simulado, cobertura calculada, projeção de 12 meses e tentativas observadas de automações. Tabelas, fontes, grãos, períodos e hashes acompanham a seleção. Comparações existentes entre cenários/projeções permanecem nos simuladores.

CSV gera um pacote local de tabelas, manifest, consultas M, medidas DAX e instruções. XLSX contém resumo com fórmulas, fontes tipadas, filtros e cabeçalhos congelados. Downloads usam autenticação existente, verificação de bytes/SHA-256 no cliente e auditoria de preparação correlacionada à requisição. Atribuições individuais exigem opção explícita e permissão de pessoas. O fallback explicativo usa somente as tabelas autorizadas e não altera cálculos ou decisões.

## Evidências

| Verificação | Resultado |
|---|---|
| Regressão backend | 214 testes aprovados, SQLite e PostgreSQL reais |
| Rechecagem final da Fase 8 | 27 testes aprovados, incluindo casos adicionais de precisão e divergência |
| Backend, casos distintos | 218 aprovados na união dos identificadores; nenhuma falha ou skip pendente |
| Frontend | 62 testes aprovados em 8 arquivos; 7 testes de analytics repetidos após ajuste de importação do teste |
| Build | TypeScript + Vite aprovados; 2.345 módulos, 15,03 s; chunk analytics 8,14 kB |
| Arquivos | CSV/ZIP e XLSX gerados e abertos; contagens, chaves, totais, hashes e proteção de texto conferidos |
| Recálculo XLSX | Ferramenta independente do gerador reabriu e recalculou os cinco indicadores; alteração de um valor de origem atualizou o resumo, e o valor foi restaurado |
| Inspeção das planilhas | Oito abas renderizadas e inspecionadas; alturas/larguras ajustadas; busca final sem erros de fórmula |
| Banco principal | Leitura em modo somente leitura: integridade ok, zero violações de FK, 41 tabelas e head 009_automations |
| Dados principais | 350 pessoas, 19 setores e 20 indisponibilidades preservados; sete rotinas desativadas; nenhuma execução, proposta, cenário ou chave criada por esta fase |
| Dependências | XlsxWriter 3.2.9 instalado somente no venv do Chronos; `pip check` sem conflitos |
| Identidade/fixture | Prompt Mestre e SHA-256, Chronos 1.0, versão e fixture reproduzível verificados |

Os XML completos ficam no runtime externo ao OneDrive. [phase8-checks.json](phase8-checks.json) reúne as evidências públicas sem credenciais ou payloads pessoais. A contagem de 218 é a união da regressão de 214 com os quatro casos novos SQLite/PostgreSQL da rechecagem, sem contar repetições como casos adicionais. A rechecagem usa a versão final da auditoria e dos formatos.

## Casos relevantes

- Solução real do OR-Tools e projeção de 12 meses: demanda = coberto + descoberto; parcelas + base = total mensal; soma mensal = anual. Minutos das atribuições reconciliam com os agregados correspondentes, sem confundir pessoas-minuto com postos-minuto.
- A mesma seleção sem mudança nos dados produz o mesmo hash de dados. Explicações mantêm snapshots e decisões intactos. Não aceitam prompt livre nem usam serviço de IA externo.
- Tenant, unidade e permissões independentes: perfil sem leitura financeira não seleciona projeção; sem leitura de pessoas não exporta atribuições; A07 fica fora do relatório sem leitura de auditoria.
- Janela mensal inclusiva/exclusiva nas bordas UTC e no fuso congelado do cenário. Alteração posterior da unidade não desloca o período histórico.
- Histórico paginado mantém versões separadas. Referências de versões diferentes são rejeitadas. Otimização pendente retorna cobertura nula, não zero fictício.
- Divergência financeira ou de cobertura produz erro explícito. Limites de linhas/bytes recusam a extração; não truncam silenciosamente.
- CSV protege textos com prefixos de fórmula e preserva números negativos. XLSX grava textos como texto, desativa URLs automáticas e não contém macros/links externos. Precisão excessiva e caracteres incompatíveis geram erro, com alternativa CSV.
- Os pacotes mantêm chaves únicas e referências válidas nos relacionamentos declarados. As consultas M têm tipos explícitos, UTF-8 e cabeçalhos estáveis inclusive em tabelas vazias.
- Interface testa seleção explícita, troca de período, opção de pessoas, restrição de rota/menu, campos financeiros, estados vazios/erros, falha de exportação e rejeição de download com hash/tamanho divergentes.

Durante a validação, uma asserção antiga do dashboard ainda esperava o texto “Não avaliada”; foi atualizada para a orientação atual de consultar as regras. O primeiro build também identificou a falta de tipos de Node numa importação usada apenas pelo teste de criptografia. A importação do teste foi ajustada; os testes afetados e o build passaram novamente. Não houve alteração de dependências do frontend para resolver isso.

## Limites e próxima fase

O recálculo e a inspeção das planilhas foram realizados pela ferramenta de artefatos; **Excel e Power BI Desktop não foram executados**. M/DAX e relacionamentos são uma preparação local, sem PBIX ou conta/cloud configurada. O arquivo exportado deixa de consultar o RBAC do Chronos; as instruções orientam proteger a pasta e revisar segurança antes de compartilhar.

A inspeção da **interface em navegador permanece pendente**, preservando o bloqueio de automação visual registrado nas fases anteriores. Testes JSDOM e build não substituem esse controle. A revisão integrada de segurança, recuperação, fluxo completo e QA visual é o escopo da **Fase 9**, ainda não iniciada.

Não houve migração nova, alteração de outros projetos, ativação de serviços externos, instalação global ou publicação. O banco principal foi apenas inspecionado; as gerações usadas na validação ocorreram em bancos isolados. `release_ready=false` e `published=false` permanecem nos metadados.
