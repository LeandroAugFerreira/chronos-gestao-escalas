# Chronos 1.0 — Fase 7: automações e n8n

O núcleo executa A01–A07 sem n8n. A integração opcional transporta eventos em loopback para quatro workflows, com confirmação autenticada na API. Não há publicação externa, aprovação automática nem ativação de regras jurídicas. O cenário continua configurável por organização/unidade, independente dos setores do Hospital Horizonte.

## Eventos e efeitos

Alterações de negócio gravam auditoria e outbox na mesma transação. Rollback elimina ambos; criar o evento não faz HTTP. O envelope guarda referências, códigos de rotina e correlation_id, sem copiar nomes, salários, senhas ou justificativas pessoais. Operações de autenticação, seed e auditoria das próprias automações não geram recursão.

Cada unidade tem sete definições, inicialmente desativadas e sem responsável. Habilitar exige responsável ativo e permissões atuais para unidade e rotina. O consumidor revalida essas permissões em cada execução; revogar o usuário ou retirar a permissão impede novos efeitos. Um evento é processado segundo a configuração atual; desativar a rotina antes do consumo gera execução ignorada. A configuração não altera insumos do solver nem aprova premissas.

| Código | Comportamento implementado |
|---|---|
| A01 | Compara os insumos atuais com o snapshot e consulta a verificação armazenada de propostas; emite aviso para recálculo quando há mudança. Não executa nova certificação jurídica. |
| A02 | Lê resultados de cobertura por intervalo do otimizador e avisa sobre minutos-pessoa descobertos. Ausência de resultado não equivale a cobertura completa. |
| A03 | Notifica internamente aprovadores ativos com permissão na unidade, excluindo o autor do cálculo. A decisão continua no fluxo da Fase 6. |
| A04 | Gera CSV de indicadores do banco e referência persistente, com digest. Inclui projeção financeira somente quando o responsável está autorizado; o arquivo fica restrito a leitores financeiros. |
| A05 | Identifica contratos, habilitações, regras e jornadas pendentes ou com vigência vencida/próxima do fim. Nunca valida ou ativa registros. |
| A06 | A partir de nova indisponibilidade, identifica alocações sobrepostas e cria sugestões. O usuário prepara uma versão filha e confirma outro cálculo; a proposta atual permanece intacta. |
| A07 | Registra referências da alteração e correlation_id no histórico de execução, sem replicar dados pessoais da auditoria. |

Monitoramento é limitado por consulta (1–500 registros por fonte); A01 confere no máximo dez propostas por execução. `truncated=true` identifica consulta parcial. A05 usa antecedência configurável de 1–366 dias. Esses são limites de software/parâmetros de operação, sem caráter normativo. A02 mede resultados históricos armazenados; não apresenta sua cobertura como avaliação atual depois de alteração dos insumos. A01 identifica necessidade de recálculo.

Avisos têm chaves de deduplicação por unidade, recurso, conteúdo e destinatário, conforme a rotina. Repetir vigência inalterada ou confirmar outra vez o mesmo evento não duplica avisos. Registrar ciência não resolve automaticamente lacunas nem certifica conformidade. CSV usa indicadores agregados e neutraliza prefixos de fórmula; não exporta lista de salários individuais. Seu conteúdo é congelado por evento, mesmo após retentativa.

## Consumidor, scheduler e recuperação

`scripts/start-automations.ps1` consome a fila. `-Once` processa no máximo um item; `-Scheduler` habilita também o planejamento por intervalos em minutos. Não é criado serviço do Windows nem tarefa recorrente no Codex. Sem consumidor, eventos permanecem na fila. Sem a opção scheduler, definições com agenda não disparam por tempo, mas continuam recebendo eventos e solicitações manuais.

O scheduler reserva o vencimento sob lock de organização e usa uma chave única por definição/instante previsto. Após reinício, vencimentos acumulados são consolidados em uma execução, evitando tempestade de catch-up. A próxima ocorrência passa a ser o instante atual mais o intervalo configurado; não há sintaxe cron nem promessa de execução em um horário civil específico.

Outbox e entregas possuem lease de 60 segundos e token de posse. Um consumidor antigo não confirma resultado depois de recuperação/cancelamento. O processamento local mantém o lock da organização e confere o prazo antes de confirmar. Suas consultas são limitadas; não há garantia de interrupção física do processo exatamente no segundo 60. Falhas temporárias têm até três tentativas com backoff de 5/10 segundos, limitado a 300 segundos. Falhas permanentes ficam visíveis, sem loop de retentativa. Uma retentativa manual aumenta o orçamento em três, mantendo os números de tentativa e o histórico anterior.

Efeitos locais, execuções e confirmação do evento são atômicos. Se um handler falha, os efeitos daquela tentativa são revertidos e a falha é registrada; outros handlers do mesmo evento também precisam aguardar a correção/reprocessamento. Execuções com erro não são classificadas como concluídas. A rotina A07 não substitui a auditoria original já confirmada na transação de negócio.

HTTP ocorre depois de liberar os locks. Só há sucesso de entrega após resposta 2xx **e** recibo autenticado correspondente na API. Timeout, falha temporária e confirmação perdida podem repetir o transporte; o receptor usa identificador estável e digest do conteúdo para impedir efeitos duplicados. O objetivo é confirmação única dos efeitos, não alegar execução física única na rede.

## Integração local e segurança

O backend aceita somente base `http://127.0.0.1:<porta>/webhook/chronos` (ou loopback IPv6), em development/test, com token de saída de ao menos 32 caracteres. URLs remotas, redirects e proxies de ambiente não são usados. Produção não habilita esse adaptador local. Não foram implementados destinos Slack/email nem envio de dados a sistemas externos.

Credenciais de entrada são opacas, aleatórias e revogáveis, vinculadas a organização, unidade, responsável e ações. A API persiste somente SHA-256 do token e o devolve uma única vez. São chaves de serviço, não sessões JWT; permanecem válidas até revogação ou perda de autorização do responsável. Rotação consiste em criar outra chave e revogar a anterior. Nenhuma chave padrão é fornecida. A interface mantém o valor apenas em memória, sem localStorage.

O callback valida entrega, evento, rotina, unidade, responsável atual e configuração habilitada. Requisições novas exigem timestamp com fuso e diferença máxima de cinco minutos. Mesmo request_id com conteúdo diferente retorna conflito; repetição idêntica devolve o recibo anterior. O fingerprint HMAC usa o segredo da aplicação e exclui apenas o timestamp de transporte. Registrar disponibilidade exige ação específica e people:write, e não aceita profissional fora da unidade da credencial. O integration endpoint registra um novo intervalo; não apaga nem libera indisponibilidades existentes implicitamente.

Os callbacks guardam o identificador de execução informado pelo n8n para rastreabilidade. Esse metadado não substitui autenticação. Os quatro exports não contêm tokens, estão desativados e usam URLs fixas da API local, sem aceitar destino fornecido no payload. Credenciais são configuradas no runtime privado do n8n. O workflow A06 possui entrada adicional de disponibilidade; ela atualiza a API autenticada e produz evento de impacto, sem acionar solver automaticamente.

## Interface e persistência

`/automacoes` reúne definições, responsável/agenda/parâmetros, execução manual, avisos, histórico, fila/retentativas/cancelamento, entregas n8n, arquivos CSV e sugestões com link para preparar nova versão. `automation:read`, `automation:manage`, `automation:run` e `integration:manage` são verificadas no servidor por unidade. Arquivos financeiros exigem finance:read; avisos destinados a um aprovador não aparecem para outros usuários. O leitor agregado não gerencia credenciais nem inicia rotinas.

Migration 009 adiciona nove tabelas, totalizando 41: automation_definitions, outbox_events, automation_executions, automation_notices, automation_artifacts, automation_suggestions, integration_credentials, integration_receipts e webhook_deliveries. FKs de tenant e unicidade protegem referências e deduplicação. A restauração restrita da demonstração remove os novos dados em ordem de dependência e recria definições desativadas, preservando usuários/unidades/auditoria.

## Runtime e limites da entrega

n8n 2.44.6 exige Node >=24 no pacote consultado. Node 24.22.1 win-x64 foi preparado separadamente, com SHA-256 do arquivo oficial. O Node 22 do frontend permanece intacto. Dependências, banco n8n, caches e logs ficam no runtime externo; nada foi instalado globalmente. O núcleo Python/React não depende da presença do n8n. A árvore npm do n8n inclui dependências opcionais de terceiros; os perfis locais carregam somente Webhook/HTTP Request, desabilitam pacotes comunitários, telemetria e funcionalidades não necessárias.

Esta configuração usa HTTP em loopback e é destinada a demonstração/teste. Não equivale a uma implantação segura para produção. N8n, API e consumidores de teste são encerrados ao final da validação. Inspeção visual real permanece pendente pelo bloqueio já registrado; testes HTTP e JSDOM não são apresentados como revisão visual.

Fontes técnicas consultadas em 25/10/2026: [instalação n8n](https://docs.n8n.io/hosting/installation/npm/), [CLI](https://docs.n8n.io/hosting/cli-commands/), [Webhook](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/), metadados do pacote no registro npm oficial e código da versão instalada. Versões/hashes públicos estão em automation/n8n/runtime.json e package-lock.json. Evidências de execução ficam no relatório da Fase 7, distinguindo testes reais de mera presença de JSON.
