# Chronos 1.0

Manual de instruções - uso local

Gestão Inteligente de Jornadas e Escalas

Edição de 27/10/2026. Cenário de demonstração: Hospital Horizonte.

## 1. Acesse e conheça a plataforma

Abra **http://127.0.0.1:5187** no computador em que o projeto está rodando. Preencha os três campos e clique em **Entrar na plataforma**:

- **Organização:** horizonte.
- **Usuário:** o e-mail configurado como administrador. Também são aceitos identificadores de usuário cadastrados.
- **Senha:** a senha escolhida pelo titular. Ela não está incluída neste manual.

O uso de e-mail como usuário não ativa login Google nem envia mensagens. Nesta instalação, o arquivo privado de acesso fica no runtime, fora do projeto. Se você já estava conectado antes da configuração do administrador, entre novamente.

Em **Visão geral**, confira os dados iniciais: **350 colaboradores e 19 setores**, de uma instituição fictícia. São contagens de cadastro; cobertura e custos dependem dos cálculos que você solicitar. A base inicial não contém cenários ou escalas prontas para operação real.

Use o menu lateral para mudar de módulo. Em tela estreita, use **Abrir menu**. O botão de sol/lua alterna os temas claro e escuro. **Sair da plataforma** encerra sua sessão; fechar a aba não desliga os servidores.

### Primeiro roteiro, em aproximadamente 15 minutos

1. Abra **Visão geral** e confira os totais.
2. Em **Colaboradores**, busque uma matrícula e abra o nome da pessoa.
3. Confira competências, qualificações, indisponibilidades e contratos autorizados.
4. Volte à lista, escolha um setor e use **Exportar CSV**.
5. Consulte **Jornadas e regras** e **Calendário** antes de criar um cenário.
6. Siga as páginas 4 a 7 para simular capacidade, custos e cobertura.

Os módulos e botões variam conforme o perfil e a unidade autorizada. O administrador tem acesso amplo, mas continua sujeito aos controles de revisão e à exigência de outro responsável para aprovar uma proposta própria.

<!-- page -->

## 2. Estrutura, colaboradores e CSV

### Organize a estrutura

Em **Unidades**, **Setores** e **Catálogos**, confira unidade, fuso, setores, funções, competências e qualificações. Os registros são configuráveis para outros segmentos. Hospital Horizonte é a demonstração, não uma limitação da marca Chronos.

Antes de cadastrar uma pessoa, confirme que seu setor pertence à unidade escolhida e que a função existe no catálogo. O fuso da unidade será usado nos registros de horários.

### Cadastre ou consulte uma pessoa

1. Abra **Colaboradores**. Use busca por nome/matrícula, unidade, setor e situação.
2. Para incluir uma pessoa fictícia, clique em **Novo colaborador**.
3. Preencha nome, matrícula única, unidade, setor e função. Salve e confira a mensagem de confirmação.
4. Para consultar vínculos, clique no nome da pessoa. Para editar os campos básicos, use o ícone de lápis, quando autorizado.

Use nomes e identificadores fictícios, por exemplo **Pessoa de demonstração** e uma matrícula ainda não utilizada. Não use CPF, dados de pacientes ou documentos profissionais reais nesta demonstração.

Se outra operação alterar o registro, o sistema pode recusar o salvamento por conflito. Recarregue a lista e reveja os valores antes de tentar de novo. Não há importação genérica de planilhas concluída neste checkpoint.

### Exporte o cadastro básico

1. Ajuste os filtros e a ordenação na lista.
2. Clique em **Exportar CSV** e aguarde a confirmação de arquivo verificado.
3. O arquivo inclui **todas as páginas** da seleção, dentro do seu escopo de acesso.

O limite é **20.000 registros e 8 MiB**. Se exceder, refine os filtros; não há truncamento silencioso. Uma seleção vazia gera somente o cabeçalho.

O CSV contém IDs, nome, matrícula, situação, marcação sintética e revisão. Não inclui salários, contratos, evidências ou ausências. Unidade, setor e função são IDs para relacionamento com seus catálogos.

Ao importar, escolha **UTF-8**, separador **vírgula** e tipo **texto** para matrícula e IDs. Campos que poderiam iniciar fórmulas recebem apóstrofo de proteção. Proteja a pasta do download: o arquivo salvo não mantém as permissões do Chronos.

<!-- page -->

## 3. Contratos, habilitações e indisponibilidade

Abra o detalhe do colaborador pelo seu nome na lista. Os botões dependem das permissões da unidade e dos catálogos. Contratos e salários também exigem acesso financeiro.

### Adicione um contrato

1. Clique em **Adicionar contrato** e selecione a jornada de referência.
2. Informe carga semanal em minutos, salário-base, tipo de vínculo e vigência.
3. Registre a fonte do contrato e salve. Confira o novo item na lista.

**Exemplos de preenchimento, sem validade jurídica automática:** 40 horas semanais correspondem a **2400 minutos**; salário de R$ 1.500,01 deve ser digitado como **1500,01** ou **1500.01**, sem separador de milhar.

O fim da vigência é **exclusivo**: um vínculo com fim em 02/11/2026 não cobre esse dia. O fim pode ficar vazio quando não houver data definida. O cadastro recusa sobreposição com contrato existente e não encerra o anterior automaticamente. Crie um colaborador fictício sem contrato para experimentar esse fluxo sem conflito.

Novos contratos ficam **pendentes de revisão**. Reduzir a carga de um cenário não reduz automaticamente o salário do contrato.

### Registre qualificação ou competência

- **Adicionar qualificação:** escolha o catálogo, início, fim exclusivo e evidência fictícia. O registro fica pendente de verificação.
- **Adicionar competência:** escolha uma competência disponível e salve. Esse vínculo não substitui habilitação profissional.

Uma validade cadastrada não equivale a credencial conferida. A tela mostra o estado retornado pela API; registros sintéticos continuam identificados. Edição/exclusão ampla de vínculos e encerramento contratual ainda não estão disponíveis nessa tela.

### Informe indisponibilidade

No painel correspondente, informe **Início da indisponibilidade**, **Fim da indisponibilidade** e, se necessário, um motivo operacional genérico. Confirme e confira os horários exibidos. Os horários de entrada seguem o fuso da unidade.

Use indisponibilidade para registrar quando a pessoa não pode ser alocada. Não escreva diagnóstico ou motivo médico. Alterar a disponibilidade não recalcula nem aprova uma proposta automaticamente; os cenários já congelados preservam seu histórico.

<!-- page -->

## 4. Jornadas, regras e calendário

### Consulte as jornadas e as regras

Em **Jornadas e regras**, examine os regimes cadastrados, sua configuração e estado de revisão. Modalidades como 5x2, 4x3, 12x36 e plantões são configurações de jornada. O nome, por si só, não prova que uma modalidade é válida para determinada função.

Para cadastrar uma hipótese de jornada, informe nome, descrição, dias de trabalho/descanso e duração do plantão. Não atribua validade jurídica apenas para facilitar a simulação.

Ao registrar uma regra, defina critério, limite, fonte, condições de aplicação, vigência e escopo. Confira unidade, função, contrato ou instrumento coletivo, quando aplicável. A vigência do formulário de regras é informada em **UTC**, conforme o rótulo da tela.

Uma regra alterada exige nova versão e revisão; o histórico não deve ser sobrescrito. Falta de regra aplicável ou de evidência deve permanecer visível.

### Crie um plantão no calendário

1. Abra **Calendário** e selecione unidade, setor/pessoa e data de referência.
2. Escolha o colaborador e o setor de atuação. Preencha título, início e fim.
3. Acrescente pausas e sua condição de remuneração, conforme os campos disponíveis.
4. Solicite a **prévia** e leia a avaliação antes de confirmar o salvamento.
5. Se mudar qualquer dado, faça uma nova prévia. Confira o registro e sua situação no calendário.

Para plantão que cruza a meia-noite, informe o fim no dia seguinte. Confira sempre o fuso e o intervalo entre início e fim. Um rascunho não equivale a escala aprovada.

### Como interpretar a avaliação

Leia o resultado junto da fonte e das regras avaliadas. Pendência não deve ser interpretada como aprovação. As avaliações cobrem os critérios configurados e o planejamento conhecido, inclusive bordas temporais aplicáveis; não certificam todo o enquadramento jurídico ou profissional.

Indisponibilidade e falta de habilitação devem ser resolvidas na origem. Não remova uma restrição apenas para eliminar uma mensagem. Cadastros de regras e quantitativos hospitalares precisam das fontes e das condições do caso concreto; o sistema não fornece mínimos universais.

<!-- page -->

## 5. Crie e compare cenários

Um cenário congela a população, os dados e as hipóteses de um mês. Ele permite comparar capacidade e demanda; não monta, sozinho, uma escala viável por posto.

### Exemplo guiado de capacidade

1. Em **Cenários**, clique em **Novo cenário**.
2. Use um nome como **Demonstração administrativa - novembro** e o grupo **demo-adm-2026-11**. O grupo aceita letras minúsculas, números, ponto, hífen e sublinhado.
3. Escolha a unidade, um setor administrativo e o mês **11/2026**.
4. Em **Origem da capacidade**, escolha **Hipótese de ciclo** para testar um regime estruturado. A opção **Plantões já cadastrados** depende do que existir no calendário.
5. Selecione o **Regime estruturado**, a **Âncora comum do ciclo**, o início local e o intervalo não remunerado em minutos. A âncora é o primeiro dia do ciclo escolhido.
6. Para testar uma meta de 40 horas semanais, informe **40** em **Meta semanal em horas**. Isso é uma hipótese de cálculo, não uma autorização de jornada.
7. Para explorar a fixture, escolha habilitações sintéticas como **hipótese**. Em uso com comprovação, mantenha somente habilitações comprovadas e vigentes.
8. Descreva em **Fonte e condições da hipótese** que se trata de um exercício fictício e salve o cenário.

Sem plantões no calendário, a capacidade baseada em plantões pode ficar vazia ou gerar avisos. Isso não indica que todos os colaboradores estejam livres ou que a demanda esteja coberta.

### Declare a demanda para otimizar

Adicione atividades e informe setor, horário de início, duração em minutos, dias da semana, pessoas exigidas, competências/habilitações e fonte. **1440 minutos** representam 24 horas.

Para testar o fluxo, você pode declarar uma atividade administrativa com uma pessoa como **hipótese didática**, sem tratá-la como dimensionamento real. Cobertura hospitalar deve ser definida por atividade, turno e norma aplicável, com sua fonte própria.

### Compare versões

Selecione **Cenário base** e **Cenário alternativo** e use **Comparar capacidade**. Para mudar uma hipótese, use **Criar próxima versão**. Preserve população e período compatíveis ao interpretar as diferenças. Déficit agregado em horas não determina, sozinho, quantas pessoas contratar ou se uma escala é viável.

<!-- page -->

## 6. Use o simulador financeiro

O simulador calcula uma projeção de **12 meses**, com valores exatos em centavos e premissas identificadas. Projeção não é despesa realizada nem comprovação de economia.

### Gere uma projeção

1. Abra **Simulador financeiro** e selecione o **Cenário de origem**.
2. Inicie uma nova projeção, dê um nome e descreva a **Fonte e escopo financeiro**.
3. Preencha as parcelas aplicáveis: categoria, base de incidência, valor ou percentual, recorrência e fonte.
4. Declare contratações hipotéticas, treinamento ou transição somente quando fizerem parte do estudo.
5. Revise os meses de incidência e as categorias ainda não informadas. Solicite o cálculo e selecione a projeção gerada para consultar.

Os nomes dos botões e os campos adicionais acompanham a modalidade da parcela escolhida. Não preencha valores normativos ou pisos profissionais por suposição; registre a fonte pertinente.

### Leia o resultado

- **Total em 12 meses:** soma da projeção configurada.
- **Salários-base:** origem contratual congelada e contratações hipotéticas, conforme a seleção.
- **Média mensal:** total dividido pelo período; não significa que todos os meses tenham o mesmo custo.
- **Categorias pendentes:** parcelas sem informação suficiente; não devem ser tratadas como custo zero comprovado.

Confira a tabela mensal e expanda as parcelas para reconciliar salários existentes, contratações e componentes. Observe avisos de falta de contrato, cobertura de período, remuneração de intervalos e arredondamento.

### Compare e teste sensibilidade

Selecione uma projeção base e uma alternativa compatível. Para sensibilidade, escolha a premissa, informe a variação permitida na tela e leia o novo resultado como uma hipótese adicional.

Alterar a meta semanal do cenário **não reduz salários automaticamente**. Uma contratação inserida no financeiro **não cria um colaborador habilitado** no cadastro ou no otimizador. Esses efeitos precisam ser modelados separadamente e revisados.

Salários e projeções dependem de permissão financeira na unidade. Se o módulo ou um valor não aparecer, confira o perfil e o escopo do acesso antes de tentar repetir a operação.

<!-- page -->

## 7. Otimize e revise propostas

O worker de otimização precisa estar ativo. Nesta execução local, ele foi iniciado junto da API e da interface. O cálculo usa OR-Tools e as entradas da versão selecionada.

### Envie um cálculo

1. Em **Otimização de escalas**, escolha o **Cenário de origem**. Ele precisa ter demanda definida.
2. Informe o nome do cálculo e o início/fim do horizonte. O **fim é exclusivo**.
3. Escolha cobertura **Estrita** para exigir toda a demanda ou **Diagnóstico** para quantificar lacunas sem esconder o déficit.
4. Escolha a política de habilitações. Registros sintéticos só devem ser aceitos como hipótese de demonstração.
5. Defina plantões candidatos: início, duração, pausa, posição da pausa, dias da semana e remuneração do intervalo.
6. Revise limites, fontes, descanso, histórico anterior/posterior, cargos autorizados por atividade e datas iniciais dos ciclos contratuais. Custos são opcionais e exigem permissão/fonte.
7. Clique em **Enviar para cálculo** e acompanhe o processamento selecionado.

Não aceite limites predefinidos como regra jurídica universal. Não marque revisão como concluída sem a evidência correspondente.

### Leia o processamento

- **Na fila / queued:** aguarda o worker.
- **Em execução / running:** cálculo em andamento.
- **OPTIMAL ou FEASIBLE:** resultado numérico do modelo configurado. Confira verificação independente, cobertura, lacunas e pendências.
- **Inviável / INFEASIBLE:** não foi encontrada solução que cumpra o conjunto de restrições. Reveja demanda, períodos e dados; não relaxe habilitação ou descanso apenas para obter resultado.
- **Falha ou cancelamento:** consulte o motivo e corrija a origem antes de reenviar.

### Revise e decida

Use **Registrar revisão individual de premissas** para contratos, jornadas, habilitações ou cenário, com fonte e evidência. Gere novo cálculo para incorporar alterações.

Submeta uma proposta elegível com justificativa. **Outro usuário autorizado** deve aprovar ou rejeitar; o autor não aprova sua própria execução. Se houver mudança de insumos, crie nova versão e revise novamente. Aprovação não grava automaticamente todos os turnos no calendário. A publicação final interna e a publicação externa não estão liberadas neste checkpoint.

<!-- page -->

## 8. Automações, analytics e acessos

### Automações internas

Em **Central de automações**, selecione a unidade e consulte rotinas A01-A07, execuções, avisos e sugestões. As definições começam **desativadas**.

Para um teste autorizado, configure a rotina, informe responsável e parâmetros e habilite somente o necessário. O botão **Executar** depende da rotina habilitada e das permissões do responsável. A agenda depende do scheduler, que não foi iniciado nesta sessão. O consumidor de eventos locais está ativo.

Dar ciência a um aviso não resolve sua causa. Sugestão de recálculo não aprova ou substitui uma escala. Nenhuma rotina valida regras ou aprova propostas automaticamente. **n8n permanece bloqueado** pela auditoria de dependências; não o inicie para seguir este manual.

### Analytics e relatórios

1. Abra **Analytics e exportações** e escolha unidade, mês opcional e versão de cenário.
2. Acrescente otimização e projeção da mesma versão, se disponíveis e autorizadas.
3. Confira origem, período, metodologia e os dados das tabelas.
4. Use **CSV e Power BI** para baixar um ZIP de tabelas, manifest e preparação de importação; ou **Exportar XLSX** para uma planilha com resumo e fontes.

Atribuições individuais são opcionais e exigem leitura de pessoas. Os limites são 20.000 registros e 8 MiB. O download é conferido por hash/tamanho. O pacote de CSV não é um painel Power BI publicado nem um PBIX validado.

Capacidade é mensal; cobertura corresponde ao horizonte do solver; financeiro cobre seus 12 meses. Não some versões alternativas como se fossem operações adicionais. Dado ausente não é zero. As explicações gratuitas são determinísticas e não enviam dados a IA externa.

### Gerencie acessos e auditoria

Em **Acessos**, use **Novo acesso**, informe usuário ou e-mail, senha inicial, perfil e escopo da unidade e clique em **Criar acesso**. São aceitos identificadores de 3 a 80 caracteres; a senha tem de 12 a 128. O identificador é normalizado para minúsculas. Usar e-mail não verifica titularidade nem envia convite.

Para aprovação por outra pessoa, crie uma conta própria para esse responsável. Não compartilhe a conta administrativa. Em **Auditoria**, consulte data, evento e referência da operação. O sistema ainda não oferece troca de senha/edição de perfil pela tela de acessos; isso depende de manutenção administrativa.

<!-- page -->

## 9. Iniciar, encerrar e resolver problemas

### Operação nesta máquina

O projeto está em **C:\Users\leand\OneDrive\Projetos\Chronos**. API e interface usam somente o próprio computador. Para definir o runtime no PowerShell:

```powershell
$baseChronos = Join-Path $env:USERPROFILE '.codex\visualizations'
$baseChronos = Join-Path $baseChronos '2026\10\24'
$pastaChronos = '01a16f80-a854-7dd2-abbc-ed567dc8b313'
$env:CHRONOS_RUNTIME_DIR = Join-Path `
  (Join-Path $baseChronos $pastaChronos) 'chronos-runtime'
```

Para encerrar os processos registrados desta sessão, sem apagar o banco:

```powershell
& (Join-Path $env:CHRONOS_RUNTIME_DIR 'stop-live-session.ps1')
```

Para iniciar novamente nesta máquina, depois de encerrar:

```powershell
& (Join-Path $env:CHRONOS_RUNTIME_DIR 'start-live-session.ps1')
```

Esses dois auxiliares estão no runtime local e não acompanham os pacotes anteriores. Após reiniciar o Windows, execute o auxiliar de encerramento para arquivar o registro anterior antes de iniciar novamente. Eles não configuram execução automática no login do Windows.

Para iniciar manualmente em outra instalação, siga **docs/release/handover.md**: backend, frontend e worker em terminais separados, com o mesmo runtime. Nesses terminais, **Ctrl+C** encerra o processo. Não execute restauração ou seed para apenas abrir uma instalação já preparada.

### Diagnóstico rápido

- **Página não abre:** confirme os servidores e o endereço http://127.0.0.1:5187. Fechar a aba não encerra o ambiente.
- **Login inválido / 401:** use organização horizonte, o identificador exato e a senha definida; entre novamente se a sessão expirou.
- **403/404:** confira perfil, unidade e referência. **409:** recarregue e reveja conflito, sobreposição ou insumos alterados.
- **Cálculo na fila:** confirme que o worker está ativo. **CSV recusado:** refine os filtros ou confira tamanho/hash conforme a mensagem.
- **503/500:** confira a prontidão em http://127.0.0.1:8017/api/v1/health/ready e informe a correlação ao suporte. Não compartilhe segredos ou dumps.

Use **Sair da plataforma** ao terminar. Faça backup antes de intervenções no banco, conforme **docs/operations/recovery.md**. QA visual, Power BI Desktop e liberação de produção continuam pendentes. Este ambiente é uma demonstração local, sem publicação.
