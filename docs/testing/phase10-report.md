# Chronos 1.0 — Preparação da Fase 10

Data de referência: 2026-10-26. **Pacote local de revisão preparado; release final não aprovado.** Não houve publicação, deploy ou alteração de outro projeto. Screenshots da aplicação permanecem pendentes; não foram fabricados ou substituídos por mockups/renders.

## Materiais preparados

- [Índice da entrega](../release/README.md), [instalação/handover](../release/handover.md) e [manual de uso](../user-guide.md).
- [Roteiro](../portfolio/demo-script.md), [estudo de caso fictício](../portfolio/case-study.md) e [matriz de cobertura](../portfolio/coverage.md), com requisitos parciais e bloqueados identificados.
- [Microensaio medido](../portfolio/benchmark.json) e fixture própria, reproduzível pelo script de benchmark. Mesmos insumos/verificador para first-fit e solver; três repetições, seed 1042, um worker, populações de 3 e 2 profissionais, uma atividade/um dia.
- [Estado do release](../release/status.json) e [plano de screenshots](../release/screenshots.json): zero capturas atuais, com telas/temas e critérios de QA a executar quando permitido.
- Empacotador/verificador `scripts/package_release.py`, pacote ZIP local com fontes/build/fixture/documentos, inventário interno e recibo SHA-256 externo.

O nome oficial em `release.json` apresentava texto UTF-8 interpretado incorretamente. Foi corrigido para **Chronos — Gestão Inteligente de Jornadas e Escalas**. Versão continua 1.0, com phase=10 indicando a preparação documental. A API health mantém a indicação do núcleo validado na Fase 9.

## Verificações da preparação

Os testes novos verificam reprodutibilidade, exclusão de segredos/bancos/caches, integridade, identidade, estados de liberação, limites, proteção contra sobrescrita/race e caminhos inválidos/links em ZIP, além de coerência do microensaio. O XML executado e sua contagem exata estão em [phase10-checks.json](phase10-checks.json).

Um teste inicialmente esperava uma mensagem específica para barras invertidas. O escritor ZIP do Windows normalizou esse nome, e a verificação rejeitou o membro extra por inventário divergente. A asserção foi ajustada para conferir a rejeição efetiva; não houve liberação do caminho ou mudança no controle de segurança.

O build frontend foi executado novamente para o pacote. Identidade, fixture Hospital Horizonte e hashes dos arquivos registrados na Fase 9 foram conferidos: entre os arquivos daquele inventário, somente `release.json` mudou, intencionalmente. Não foram alterados módulos de negócio, schema, dados ou configuração local do banco nesta etapa. Os resultados de **253 testes backend e 62 frontend da Fase 9 são históricos**, não uma nova regressão completa da Fase 10.

O pacote é verificado por inventário completo e hash de cada arquivo; o recibo externo identifica os bytes do ZIP. A conferência após empacotar usa extração em pasta nova e um banco sintético novo para migrations, seed idempotente, autenticação e leitura. Usa as dependências do runtime já instalado nesta máquina; não equivale a teste de instalação limpa de todos os pacotes numa máquina nova. O resultado dessa etapa fica no recibo externo, evitando autorreferência do ZIP.

Não entram no arquivo `.env`, contas locais, credenciais, bancos SQLite, dumps/backups, logs, caches, node_modules, venv ou Git. O banco demonstrativo é recriado com fixture e migrations. O manifest/recibo assegura integridade dos bytes conferidos, sem assinatura digital de autoria ou aprovação de produção.

## Medições e limites do case

Com três profissionais, as duas políticas cobriram 1.440 postos-minuto, usando três atribuições e custo imputado de 144.000 centavos. Com dois, ambas cobriram 960, deixando 480 descobertos e custo imputado de 96.000 centavos. Esse custo parcial não representa economia de uma solução completa. Zero categorias de erro de restrição não apaga a lacuna.

Tempos mínimo/mediana/máximo são medidos no JSON e dizem respeito aos algoritmos nesta máquina. Não há tempo humano, ganho de produtividade ou economia real medidos. O microensaio não representa a operação dos 350 colaboradores e não prova dimensionamento profissional ou validade jurídica.

## Aceites ainda pendentes

1. Remediar a árvore n8n e repetir os quatro workflows antes de liberar sua partida. O bloqueio da Fase 9 permanece, com runtime/workflows preservados.
2. Concluir QA de navegador real, teclado, contraste, temas, responsividade e screenshots. O bloqueio anterior não foi contornado por ferramenta alternativa.
3. Validar Power BI Desktop/importação/DAX nativos. Excel e recálculo de planilhas já têm evidências das fases anteriores.
4. Revisar/concluir os itens funcionais parciais da matriz, além da operação, infraestrutura e segurança de produção.
5. Obter autorização explícita para conteúdo/destino antes de qualquer publicação, depois da revisão. Preparar o ZIP não presume esse aceite.

`release_ready=false`, `published=false`, `package_kind=local-review-package`. O próximo trabalho é resolver os aceites pendentes; não existe uma declaração de produto integralmente concluído ou de publicação aprovada neste checkpoint.
