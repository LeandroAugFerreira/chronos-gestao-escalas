# Chronos 1.0 — Fase 8: analytics e exportações

O relatório combina **uma versão de cenário**, **uma execução de otimização opcional** e **uma projeção financeira opcional** da mesma versão. Não soma alternativas nem escolhe implicitamente uma execução como resultado oficial. Comparações entre cenários e entre projeções continuam nos módulos da Fase 5.

## Consulta e períodos

- `GET /api/v1/analytics/history?unit_id=...&reference_month=2026-11-01`: histórico paginado por unidade e mês opcional, com chave, versão, digest e criação. O mês deve começar no dia 1.
- `GET /api/v1/analytics/options/{scenario_id}`: até 100 execuções recentes de cada tipo, conforme permissão. A API de relatório também aceita IDs anteriores autorizados.
- `POST /api/v1/analytics/report`: seleção `{scenario_id, optimization_id?, financial_id?, include_people:false}`. Retorna tabelas, manifest e explicação. Não altera dados.
- `POST /api/v1/analytics/export`: mesma seleção e `format:csv|xlsx`. Retorna conteúdo base64, MIME, nome seguro, quantidade de bytes, SHA-256 do arquivo e SHA-256 dos dados. O frontend usa o transporte autenticado existente e verifica integridade antes do download. A auditoria registra a preparação do arquivo, sem copiar valores financeiros ou pessoas; não prova que o cliente salvou o download.

O mês civil usa o **fuso congelado no cenário**, com início inclusivo e fim exclusivo convertidos para UTC. Uma mudança posterior no cadastro da unidade não move essa janela. A capacidade é mensal, enquanto cobertura usa o horizonte completo da execução. A projeção contém seus 12 meses, inclusive os posteriores ao mês de referência. Os períodos estão identificados nas tabelas e no manifest; não se aplicam cortes parciais silenciosos.

Minutos de cobertura são postos-minuto calculados pelo verificador. Minutos reais e remuneráveis são somas das atribuições inteiras, descontando pausas conforme sua natureza, inclusive trechos fora do horizonte. Essas medidas não são intercambiáveis. Quantidade de tentativas de automação não é quantidade de eventos únicos nem comprovação de entrega externa.

## Autorização e limites

`scenario:read` controla a versão base. `optimization:read`, `finance:read`, `schedule:read`, `automation:read` e `people:read` resolvem seus próprios escopos na mesma unidade. Uma permissão ampla não amplia outra. Sem permissão financeira, o solicitante não seleciona projeção. Atribuições individuais exigem opção explícita, otimização e leitura de pessoas. Sem `audit:read`, tentativas A07 são excluídas. Nenhum relatório inclui salários por pessoa, snapshots privados, credenciais, atores ou resultados internos das automações.

Não há permissões novas nem alteração de schema: as nove migrations e 41 tabelas da Fase 7 continuam válidas. O endpoint rejeita referências de outros tenants/unidades e combinações de versões diferentes. Formatos usam a mesma projeção autorizada do JSON.

Limite de 20.000 linhas no conjunto e 8 MiB para dados/arquivo. Excesso produz `REPORT_LIMIT`, sem truncamento de exportação. A tela mostra até 100 linhas por tabela. Custos indisponíveis e execução sem verificação ficam nulos; não são convertidos em zero. Financeiro deve reconciliar parcelas, totais mensais e anual; cobertura deve reconciliar demanda = coberto + descoberto. Divergência produz `REPORT_RECONCILIATION`.

## Arquivos e rastreabilidade

CSV é um ZIP com uma tabela por arquivo UTF-8/BOM, cabeçalhos estáveis inclusive em tabelas vazias, `manifest.json`, consultas M, medidas DAX e instruções. Textos com prefixos perigosos recebem apóstrofo; números negativos permanecem números. O manifest declara essa transformação, portanto o texto protegido pode diferir da fonte. O SHA-256 dos dados identifica JSON canônico da seleção e tabelas anteriores à proteção CSV. O SHA-256 do arquivo cobre os bytes efetivamente recebidos.

XLSX é gerado no servidor por XlsxWriter 3.2.9, sem Excel instalado. Células de origem são tipadas, textos não viram fórmulas/URLs, datas são datas e instantes são exibidos em UTC. Fórmulas de resumo usam referências simples e caches reconciliados. Valores inteiros acima da precisão segura adotada para Excel são recusados; CSV preserva os inteiros. Não há macros, links externos ou fórmulas obtidas de dados do usuário.

O resumo precede as tabelas de origem. Filtros, cabeçalhos congelados, unidades nas colunas e notas de grão ajudam a interpretar os dados. O resumo não é um novo simulador financeiro: editar uma célula de origem recalcula os resumos, mas não executa regras, solver ou projeções do Chronos.

Resultados calculados apontam IDs e digests de origem. Estado da proposta, nome atual da unidade e histórico de automações refletem o instante da extração e podem mudar depois. Guarde o pacote para reproduzir esse estado. Não se promete que consultar novamente um banco alterado recriará o mesmo relatório. Extrações iguais, sem alteração dos dados selecionados, têm o mesmo digest de dados; o horário da extração não entra nesse digest.

## Explicações

O fallback gratuito `explanation-1.0` é determinístico e usa apenas as tabelas autorizadas, com fontes estruturadas. Não aceita prompt livre, não importa clientes de IA, não envia dados à rede e não decide validade jurídica, cálculos ou aprovações. Não há dependência de Ollama ou serviço pago. `AI_ENABLED` continua reservado; nenhum adaptador externo foi ativado nesta fase. Uma integração futura deverá receber apenas a projeção autorizada e preservar o fallback.

## Validação e próximos controles

Testes cobrem reconciliação com OR-Tools real, autorizações, isolamento, bordas UTC/fuso congelado, nulos, versões, arquivos, proteção de fórmulas, limites e integridade do download. O XLSX de teste foi reaberto, recalculado e renderizado pela biblioteca de artefatos do ambiente, separadamente do gerador do servidor. Isso não equivale à inspeção no Excel ou Power BI Desktop. QA da interface em navegador e revisão integrada permanecem na Fase 9. Sem publicação externa.
