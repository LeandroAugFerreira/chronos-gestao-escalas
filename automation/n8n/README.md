# Chronos 1.0 — n8n

**27/10/2026: execução bloqueada.** A candidata 2.45.4, resolvida apenas em lockfile e não instalada/iniciada, ainda apresenta 8 itens críticos e 81 altos (167 itens totais, incluindo avisos transitivos/propagados). [Evidência desta revisão](../../docs/security/homologation-2026-10-27.json). O runtime instalado permanece 2.44.6. A auditoria histórica da Fase 9 avaliou também a candidata 2.44.7. Setup, partida e smoke n8n estão suspensos; runtime e workflows foram preservados. Use o consumidor local e consulte [achados de segurança](../../docs/security/phase9-findings.md). As instruções abaixo e evidências da Fase 7 permanecem históricas até nova liberação.

Quatro workflows importados e executados em teste local na Fase 7. Os exports estão **desativados**, sem valores de credenciais. O Chronos processa suas rotinas sem n8n; essa integração é opcional e não publica nada externamente.

| Arquivo | Entrada e resultado |
|---|---|
| A03-escala-pendente.json | Evento de submissão → API autenticada → aviso para outro aprovador autorizado |
| A02-alerta-cobertura.json | Evento de cobertura → API → alerta de lacuna deduplicado |
| A04-relatorio-programado.json | Evento do scheduler/manual → API → referência do CSV de indicadores persistido |
| A06-disponibilidade.json | Webhook de disponibilidade → API autenticada → registro e evento de impacto; segundo webhook confirma a sugestão, sem executar solver automaticamente |

O scheduler principal fica no Chronos, evitando duas agendas concorrentes para a mesma rotina. O n8n confirma os casos de uso na API; a mesma chave de evento não duplica efeitos se houver timeout/replay. O relatório não é recalculado ou sobrescrito no callback do mesmo evento. A06 propõe nova versão, cuja solicitação e aprovação continuam humanas.

## Preparar e iniciar

Use o mesmo CHRONOS_RUNTIME_DIR dos demais componentes, fora do projeto e OneDrive:

```powershell
.\scripts\setup-n8n.ps1
.\scripts\start-n8n.ps1
```

O setup opcional usa Node 24.22.1 win-x64 com SHA-256 verificado e n8n 2.44.6 fixado pelo lock. Não altera o Node 22 do frontend nem instala pacote global. Um runtime já instalado na versão fixada é preservado. O servidor local abre em [n8n local](http://127.0.0.1:5687), vinculado somente a loopback. Ctrl+C encerra o processo. Escolha as próprias credenciais de proprietário no primeiro acesso; não há senha padrão.

Os perfis fornecidos carregam apenas Webhook/HTTP Request, com pacotes comunitários, telemetria e recursos não necessários desativados. São destinados a demonstração local, sem túnel ou implantação de produção. A árvore npm pode emitir avisos de dependências transitivas; ela fica isolada no runtime. O núcleo Python/React continua independente.

## Configuração explícita

1. No Chronos, crie uma credencial de integração para a unidade na Central de automações. A ação `workflow_callback` permite confirmação; acrescente `availability` somente quando a entrada de disponibilidade for desejada. O responsável precisa manter permissões atuais. Guarde o token mostrado uma única vez, sem colocá-lo em código/JSON versionado.
2. No n8n, crie uma credencial **Header Auth** chamada `Chronos 1.0 — Callback autorizado`: nome do header `Authorization`, valor `Bearer ` seguido do token de integração do Chronos.
3. Gere outro token aleatório de ao menos 32 caracteres para o sentido Chronos → n8n. Configure no ambiente privado do backend `CHRONOS_N8N_WEBHOOK_BASE_URL=http://127.0.0.1:5687/webhook/chronos` e `CHRONOS_N8N_OUTBOUND_TOKEN` com esse valor; reinicie o backend e consumidor para incorporar as variáveis. Não exiba nem versionе o token.
4. No n8n, crie Header Auth `Chronos 1.0 — Webhook local`: header `X-Chronos-Token`, valor igual ao token de saída. Importe os quatro JSON e selecione as credenciais correspondentes nos nós; os IDs exportados são referências, não segredos. As URLs da API estão fixadas em loopback/porta 8017.
5. Habilite somente os workflows desejados no n8n **local** e as rotinas correspondentes no Chronos, marcando seu encaminhamento explícito. Os exports não ativam fluxos por conta própria. Inicie `scripts/start-automations.ps1 -Scheduler` para consumir eventos e agendas; o núcleo segue funcional com o encaminhamento desativado.

Nomes de headers e URLs não são fornecidos pelo payload recebido. A API valida timestamp, escopo, evento/entrega, permissões atuais e digest de replay. Disponibilidade requer profissional da unidade da chave e people:write. Repetição idêntica retorna o recibo; conteúdo diferente com o mesmo identificador retorna conflito. Nenhum envio a email, Slack ou outra aplicação foi configurado.

## Validação reproduzível

```powershell
& $pythonPath .\backend\scripts\smoke_phase7.py --runtime $env:CHRONOS_RUNTIME_DIR
```

O smoke cria bancos/contas/chaves efêmeros, importa credenciais apenas no runtime privado, ativa os workflows de teste em loopback, executa duas otimizações reais e os quatro fluxos, verifica o retorno com IDs de execução do n8n e encerra seus processos. A entrada de disponibilidade sem autenticação é recusada; replay não cria outra indisponibilidade. O banco principal não é usado; a chave de serviço do teste é revogada ao final. O arquivo temporário de credenciais em claro é removido logo após a importação.

`generate_workflows.py` reconstrói os exports deterministicamente. IDs de versão derivam do conteúdo, evitando reaproveitar uma versão do n8n para nós alterados. package.json/package-lock.json/runtime.json permitem reproduzir o runtime opcional. [Arquitetura](../../docs/architecture/phase7.md) e [relatório de execução](../../docs/testing/phase7-report.md) registram limites e resultados reais.
