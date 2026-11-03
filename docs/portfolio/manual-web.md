# Manual do Chronos 1.0

Um guia para conhecer o projeto, experimentar o aplicativo e entender as principais decisões de desenvolvimento.

## Comece por aqui

O Chronos ajuda a organizar equipes, jornadas e escalas. Ele reúne os dados das pessoas, as necessidades de cada setor e as regras de trabalho para apoiar o planejamento.

Para demonstrar essas funções, criei o **Hospital Horizonte**, uma instituição fictícia com **350 colaboradores e 19 setores**. O hospital é um exemplo de uso: a estrutura do sistema também permite configurar empresas de outros segmentos.

**Para recrutadores:** o roteiro de cinco minutos abaixo mostra a interface, a organização dos dados e o controle de acesso. Os tópicos seguintes explicam os módulos e as escolhas técnicas, sem exigir que você configure um ambiente de desenvolvimento.

## Baixe e abra o aplicativo

1. Na página do projeto, escolha **Baixar para Windows (.exe)**.
2. Salve o arquivo **Chronos.exe** em uma pasta do seu computador.
3. Abra o arquivo e aguarde a preparação da primeira execução. Não é necessário instalar Python ou Node.js para usar o executável.
4. Quando a janela do Chronos indicar que está pronto, o aplicativo abrirá no seu navegador. Se isso não acontecer, clique em **Abrir Chronos**.
5. Mantenha a janela do Chronos aberta enquanto utiliza o aplicativo.

Esta edição foi preparada para **Windows de 64 bits**. O aplicativo funciona no seu computador; o endereço exibido na janela é local e pode variar se a porta padrão estiver ocupada. A página do portfólio apresenta o projeto e oferece o download.

O executável não possui assinatura digital. Se o Windows ou a política da sua empresa impedir a abertura, confira a origem e as informações de integridade na página de download ou procure o responsável pelo computador. Não é necessário desativar proteções para ler o projeto e este manual.

## Entre com o acesso de demonstração

- **Organização:** `horizonte`
- **Usuário:** `demo`
- **Senha de demonstração:** `ChronosDemo@2026`

O executável cria essa conta na primeira abertura, junto com os dados fictícios. Ela permite consultar a visão geral, os setores, as unidades e os catálogos. Assim, o visitante conhece a organização da plataforma sem alterar os cadastros.

Essa conta não acessa salários, dados individuais dos colaboradores, administração de usuários ou aprovação de escalas. Por isso, o menu apresenta menos opções do que o menu de um administrador.

Para testar os recursos de edição e simulação, veja **Crie seu administrador local**. As credenciais de demonstração são públicas; não as utilize em outros serviços.

## Roteiro de cinco minutos

1. **Visão geral:** confira os colaboradores, setores e unidades cadastrados. Observe a distribuição das equipes e das jornadas contratuais.
2. **Filtro de unidade:** selecione uma unidade e acompanhe a atualização dos indicadores. Os números vêm da base local, conforme seu acesso.
3. **Setores:** veja como áreas assistenciais, administrativas e operacionais possuem estruturas próprias.
4. **Catálogos:** consulte funções, competências, qualificações e modalidades de jornada. Esses cadastros ajudam a distinguir quem pode exercer cada atividade.
5. **Tema e navegação:** alterne entre claro e escuro pelo botão de sol/lua e percorra o menu. No celular ou em uma janela estreita, use o botão de menu.

As contagens do dashboard descrevem os cadastros. Elas não comprovam que a cobertura de um setor está adequada. Cobertura, custos e conformidade são avaliados nos módulos específicos, com as premissas informadas pelo operador.

## Crie seu administrador local

1. Na janela de controle do aplicativo, clique em **Criar administrador local**.
2. Escolha seu usuário ou e-mail e uma senha entre **12 e 128 caracteres**. Confirme a senha e salve.
3. No navegador, saia da conta de demonstração, se estiver conectado.
4. Entre com organização **horizonte**, o usuário escolhido e sua senha.

Essa criação é permitida somente enquanto a instalação ainda não possui administrador. Depois, a gestão de novos acessos acontece no menu **Acessos**, com uma conta autorizada. Usar um e-mail como nome de usuário não envia mensagens nem conecta uma conta Google.

O administrador e os dados pertencem à sua instalação. Nenhuma conta pessoal do autor acompanha o download. Use apenas informações fictícias durante a avaliação.

## Pessoas, estrutura e jornadas

**Unidades, Setores e Catálogos:** organize os locais de trabalho, as áreas, os cargos, as competências e as qualificações. Confirme esses cadastros antes de adicionar pessoas.

**Colaboradores:** use a busca e os filtros para localizar uma pessoa fictícia. Clique no nome para consultar seus vínculos. O botão **Novo colaborador** permite informar nome, matrícula, unidade, setor e função. As opções de edição dependem do perfil e da unidade autorizada.

**Contratos e habilitações:** no detalhe do colaborador, registre o contrato, a jornada, as competências e as qualificações com suas datas de validade. Informe as fontes e evidências quando solicitadas. O acesso a contratos e salários também depende da permissão financeira.

**Indisponibilidades:** registre o período em que a pessoa não pode ser alocada. O planejamento usa essas informações para evitar atribuições incompatíveis.

**Calendário:** escolha a unidade e o período, consulte os plantões e cadastre turnos quando autorizado. Confira datas, horários e pausas antes de salvar. Os registros podem indicar pendências ou conflitos que precisam ser revistos.

**Jornadas e regras:** modalidades como 5x2, 12x36 ou 4x3 são configurações possíveis de cadastro ou simulação. A seleção de um nome não confirma sua validade para qualquer cargo. A avaliação depende de regras, contratos, acordos, fontes e vigências aplicáveis.

## Cenários, custos e otimização

**Cenários:** crie uma hipótese de planejamento. Defina unidade, setor, período, necessidades de cobertura e origem das informações. Gere novas versões para comparar mudanças sem perder o contexto anterior.

**Simulador financeiro:** selecione o cenário e informe as premissas da projeção. Compare os valores estimados para os 12 meses e revise os componentes usados no cálculo. Os resultados dependem dos dados informados; não representam economia comprovada ou redução automática de salários.

**Otimização de escalas:** selecione um cenário, defina o período e as opções de geração e solicite o cálculo. O aplicativo inclui um processador local para consumir a fila enquanto sua janela estiver aberta. O algoritmo considera disponibilidade, habilitações, descansos e requisitos cadastrados.

Uma execução pode encontrar uma proposta, apontar lacunas ou informar que não há solução para as condições escolhidas. Reveja os resultados e as pendências antes de seguir. O sistema preserva versões e exige revisão humana; quem criou uma proposta não aprova sua própria proposta no fluxo que exige outro responsável.

Os quantitativos do Hospital Horizonte são exemplos. O projeto não estabelece mínimos profissionais universais e não oferece certificação jurídica de escalas.

## Relatórios, acessos e automações

**Analytics e exportações:** consulte os resultados calculados e sua origem. Os arquivos CSV/XLSX dependem da permissão do usuário e do conjunto de dados selecionado. Há preparação de dados para Power BI; a apresentação no Power BI Desktop continua como etapa de avaliação separada.

**Exportação de colaboradores:** ajuste os filtros e escolha **Exportar CSV**. A seleção inclui todas as páginas permitidas. Se o limite de exportação for excedido, refine os filtros. O cadastro básico exportado não inclui salários, contratos ou ausências.

**Acessos e Auditoria:** o administrador pode gerenciar contas e consultar registros das ações. As permissões são aplicadas também na API, além do que aparece na interface.

**Central de automações:** reúne definições e eventos locais. A edição de demonstração mantém o agendamento automático desativado. A integração com n8n permanece bloqueada pela revisão de dependências; ela não é necessária para abrir o aplicativo nem para testar o núcleo de planejamento.

## Salve seu progresso e encerre

As alterações confirmadas são gravadas na base local. Na próxima abertura, o Chronos reutiliza os dados da mesma instalação; não recria os 350 colaboradores por cima das suas alterações.

1. Use **Sair da plataforma** para encerrar a sessão.
2. Feche a janela de controle do Chronos ou clique em **Encerrar**. Isso desliga os serviços locais iniciados pelo aplicativo.
3. Para continuar depois, abra **Chronos.exe** novamente.

O botão **Pasta de dados** abre o local usado pela demonstração: `%LOCALAPPDATA%\Chronos\1.0-demo`. Antes de fazer uma cópia de segurança, encerre o aplicativo e copie a pasta completa. Ela inclui o banco e a configuração da sua instalação. Não publique essa pasta nem a envie como código-fonte.

## Se algo não funcionar

- **O navegador não abriu:** use **Abrir Chronos** na janela do aplicativo e confira o endereço mostrado nela. Não use o endereço de outra instalação ou do ambiente do autor.
- **O menu parece incompleto:** confira se entrou com `demo` ou com seu administrador. O perfil de demonstração possui acesso de consulta limitado.
- **Não consegui entrar:** confirme organização, usuário e senha. O botão de olho permite conferir a senha digitada. Após uma falha, ela é limpa.
- **Uma alteração foi recusada:** confira os campos, o perfil e possíveis conflitos. Se outro registro foi atualizado, recarregue a página antes de tentar de novo.
- **O cálculo não termina:** mantenha a janela do Chronos aberta. Consulte o estado da execução e os avisos. A duração depende das condições do cenário e do computador.
- **Preciso analisar um erro:** o arquivo `chronos.log` fica na pasta de dados. Informe a mensagem e a correlação da operação, quando exibida. Evite compartilhar senhas ou o banco completo.

## Para quem avalia a implementação

O frontend usa **React e TypeScript**; a API, **Python e FastAPI**. A persistência utiliza **SQLAlchemy e migrações Alembic**. O projeto prevê PostgreSQL, enquanto o executável de demonstração utiliza SQLite local. A otimização de escalas usa **OR-Tools**.

As decisões que podem ser avaliadas incluem controle de acesso por perfil e unidade, cálculo financeiro com precisão decimal, verificação de elegibilidade para atividades, processamento separado do otimizador, versionamento dos cenários e rastreabilidade das operações.

A interface possui identidade própria — azul profundo, cobre, tons de papel e grafismos de tempo — com assinatura de **Leandro Augusto Ferreira**. Ela oferece temas claro e escuro e componentes compartilhados entre os módulos.

Esta é uma demonstração para avaliação. Não utiliza dados de pacientes ou colaboradores reais e não é apresentada como sistema liberado para uma operação hospitalar de produção. O código-fonte e as informações de integridade ficam disponíveis na página do projeto para uma avaliação mais aprofundada.
