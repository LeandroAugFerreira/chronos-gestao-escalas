# Chronos 1.0 — Manual de uso local

Para o passo a passo inicial, consulte o [manual de instruções detalhado](manual-de-uso.md) e o [PDF para leitura/impressão](../output/pdf/Chronos-1.0-Manual-de-Uso.pdf). O acesso administrativo desta instalação usa o e-mail autorizado pelo titular; a senha não é distribuída nos manuais.

Chronos — Gestão Inteligente de Jornadas e Escalas. Hospital Horizonte é o cliente fictício de demonstração: 350 colaboradores em 19 setores, com operação hospitalar 24 horas. Setores, atividades, competências e regras são configuráveis; o nome da plataforma e sua marca temporal não são exclusivos de hospitais.

## Acesso e preparação

Siga o [guia de instalação e entrega](release/handover.md). A organização demonstrativa usa o identificador **horizonte**. O administrador é criado pelo operador, com senha escolhida por ele. Não há senha pública ou conta padrão no pacote.

O menu depende das permissões do usuário e da unidade. Ausência de menu não substitui autorização: a API também confere cada operação. RH, gestão, financeiro, analista, demonstração e administrador possuem acessos diferentes. Salários e projeções exigem permissão financeira; atribuições individuais exigem leitura de pessoas.

## Estrutura e pessoas

1. Em **Visão geral**, confira a origem dos dados, população, unidades, setores e jornada contratual média. Os números representam o cadastro e não atestam cobertura hospitalar.
2. Em **Unidades**, **Setores** e **Catálogos**, consulte ou mantenha os registros permitidos pelo seu papel. Preserve o fuso correto da unidade; ele afeta cálculos civis e períodos de relatórios.
3. Em **Colaboradores**, use busca/filtros e abra o detalhe para consultar qualificações, disponibilidade e contratos autorizados. Use **Adicionar contrato**, **Adicionar qualificação** ou **Adicionar competência**, conforme as permissões na unidade e a leitura de catálogos. Contratos também exigem leitura financeira; salários ficam restritos a essa permissão. Informe valores sem separador de milhar e até duas casas decimais; o fim da vigência é exclusivo. Novos contratos não podem sobrepor vínculos existentes. Contratos e qualificações permanecem pendentes de revisão; cadastrar competência não substitui habilitação. Indisponibilidades usam o fuso da unidade. Os endpoints continuam documentados na [API](api/api.md). Edição/exclusão ampla e encerramento contratual ainda não estão disponíveis nesta tela.
4. Se houver conflito de revisão, recarregue o registro e confira os dados atuais antes de tentar salvar novamente. Não force alteração no banco para contornar o conflito.

A fixture usa nomes, registros, vínculos e evidências fictícios. Não introduza CPF, dados de paciente, motivo médico ou credenciais profissionais reais para realizar a demonstração. O importador disponível é o da fixture transacional; importação genérica de arquivos de pessoas não está concluída.

## Exportação cadastral

Em **Colaboradores**, ajuste busca, unidade, setor, situação e ordem e use **Exportar CSV**. O arquivo reúne todas as páginas da seleção dentro do seu escopo de leitura de pessoas. O limite é 20.000 linhas e 8 MiB; acima dele, refine os filtros. Nenhuma linha é truncada silenciosamente. Resultado vazio contém apenas o cabeçalho.

O CSV contém os campos básicos do cadastro, com IDs de organização, unidade, setor e função. Não inclui salários, contratos, preferências, evidências ou ausências. Importe IDs e matrícula como texto; o formato é UTF-8 com BOM, separado por vírgula. Textos com início de fórmula recebem apóstrofo de proteção. O Chronos confere tamanho/hash antes de preparar o download e registra a preparação na auditoria. Proteja o arquivo baixado, pois ele não mantém as permissões da aplicação. O cadastro de vínculos especializados não é exportado por essa ação.

## Calendário e LaborRules

Em **Jornadas e regras**, configure hipóteses de jornada/ciclo e regras com fonte, vigência e escopo. Os nomes 5x2, 4x3, 12x36 e plantão não validam juridicamente uma configuração. Revisões humanas precisam de origem e evidência aplicáveis ao caso.

Em **Calendário**, selecione unidade, período e profissional; informe turno e pausas. Faça a prévia antes de salvar. Alterar os dados invalida uma prévia anterior. Rascunhos, cancelamentos e avaliações ficam identificados; ausência de regra ou de evidência não gera aprovação automática. As avaliações só cobrem os critérios configurados e o planejamento conhecido.

## Cenários e projeção financeira

Em **Cenários**, escolha unidade/setor/mês, população e modo calendário ou ciclo. Declare jornada-alvo, âncora, pausas, demanda por atividade, competências/habilitações e fontes. Salve versões independentes para comparar hipóteses compatíveis. O orçamento agregado de horas não monta uma escala viável por posto.

O **Simulador financeiro** usa o cenário congelado e suas premissas. Confira parcelas, fontes, bases de incidência, meses de recorrência, contratações e exclusões. Valores são calculados em centavos/Decimal por 12 meses. Reduzir jornada-alvo não reduz salários automaticamente. Categorias ausentes e dias sem contrato válido permanecem visíveis; não representam economia comprovada.

Comparações e sensibilidade são projeções. Contratação financeira não acrescenta automaticamente uma pessoa habilitada à capacidade ou ao solver.

## Otimização e decisão

1. Em **Otimização de escalas**, selecione uma versão de cenário, horizonte, atividades, templates e parâmetros explícitos. O worker local precisa estar em execução.
2. Confira fila, execução, resultado do solver, lacunas, bloqueios e verificação independente. `OPTIMAL` descreve o modelo numérico configurado; não é certificação jurídica.
3. Se o resultado tiver lacunas, premissas pendentes ou insumos obsoletos, revise a origem e gere nova execução/versão. Não relaxe habilitação ou descanso apenas para ocultar um déficit.
4. Submeta a proposta elegível com justificativa. O autor da execução não aprova sua própria proposta; outro usuário autorizado decide.
5. Se os insumos mudarem, a versão anterior continua histórica e uma nova versão precisa ser calculada/revisada. Uma proposta filha não substitui a aprovada apenas por existir.

Os estados disponíveis incluem rascunho, submetida, aprovada, rejeitada e substituída. Publicação externa e um fluxo de publicação interna final não estão liberados neste checkpoint. A aprovação não escreve automaticamente todos os turnos no calendário.

## Automações e analytics

A **Central de automações** mostra definições A01–A07, responsável, agenda, execuções, avisos e sugestões. As rotinas começam desativadas. Habilite somente o que será exercitado no ambiente fictício. Uma ciência de aviso não resolve o problema automaticamente; uma sugestão de reotimização não aprova ou troca uma escala.

O consumidor local funciona sem n8n. **A partida n8n está bloqueada por auditoria de dependências.** Preserve esse bloqueio; veja os [achados](security/phase9-findings.md).

Em **Analytics e exportações**, escolha unidade, mês opcional e uma versão de cenário. Acrescente uma otimização e uma projeção da mesma versão, se autorizado. Capacidade é mensal; cobertura tem o horizonte da execução; financeiro tem seus 12 meses. Versões alternativas não devem ser somadas. Resultados ausentes aparecem indisponíveis, sem zero inventado.

CSV baixa um ZIP de tabelas, manifest e preparação Power BI. XLSX contém resumo com fórmulas e fontes tipadas. Atribuições individuais são opcionais. O cliente confere o hash/tamanho do download; o limite é 20.000 registros e 8 MiB. Depois de salvo, o arquivo não consulta o RBAC do Chronos: proteja sua pasta. A explicação gratuita é determinística e não envia dados a IA externa.

## Erros e encerramento

- **401:** entre novamente; a sessão pode ter expirado ou sido revogada.
- **403/404:** confira papel, unidade e referência; não use IDs de outra organização para tentar contornar o acesso.
- **409:** reveja revisão/digest/insumos ou reconciliação da origem, conforme a mensagem.
- **413/408:** corpo ou tempo de recebimento excedido. Reduza o pedido; não desative limites para ocultar um problema.
- **503/500:** informe o identificador de correlação ao operador. Não compartilhe `.env`, cookies, tokens ou dumps de banco.

Use **Sair** para revogar a sessão no servidor. Em falha de rede, a tela não confirma uma saída que não foi efetivada. Para backup e recuperação, use o [procedimento operacional](operations/recovery.md); não substitua o banco ativo por um arquivo antigo durante a demonstração.
