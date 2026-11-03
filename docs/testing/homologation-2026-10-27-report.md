# Chronos 1.0 — Homologação local de 27/10/2026

Esta rodada continua a revisão da Fase 10. Hospital Horizonte permanece o cenário fictício de demonstração, com 350 colaboradores e 19 setores. Não constitui aceite de produção ou publicação.

## Cadastro de vínculos

O detalhe do colaborador permite adicionar contratos, qualificações e competências pelos endpoints existentes. O formulário de indisponibilidade é reutilizado com o fuso da unidade. Contratos exigem escrita de pessoas e leitura financeira na mesma unidade; qualificações e competências exigem escrita de pessoas. Os seletores também exigem leitura de catálogos. Salários não são consultados por usuários sem autorização financeira na unidade.

Os formulários preservam centavos sem multiplicação em ponto flutuante, conferem datas e fim exclusivo, impedem submissões concorrentes e reutilizam a chave de idempotência após falha de rede com o mesmo conteúdo. Alterar o conteúdo gera uma nova chave. Conflitos da API preservam os campos para correção. Contratos e qualificações continuam pendentes de revisão; os indicadores exibem o estado retornado pela API, sem atribuir uma revisão fixa a todos os registros. Não há aprovação jurídica ou profissional implícita.

Não foram alterados a API, o schema ou o banco principal. Edição/exclusão ampla de vínculos, encerramento contratual e importação cadastral genérica continuam fora desta rodada. RF03 avança, mas permanece parcial.

## Verificações executadas

- Frontend completo: **81 testes aprovados**, incluindo 19 novos testes dos formulários, permissões, estados e integração da página. Execução em JSDOM; não equivale a QA em navegador real.
- API: **4 testes aprovados**, cobrindo os dois casos novos em SQLite e PostgreSQL: gravação/leitura, idempotência, conflito de vigência, revisão pendente, tentativa de promoção indevida e isolamento de permissões/unidades.
- TypeScript e build Vite aprovados; 2.346 módulos, build em 27,49 s. Rollup informou remoção de duas anotações de comentários do Zod, sem falha do build.
- Empacotador: **18 testes aprovados**. A primeira tentativa encontrou erro ao criar a pasta temporária padrão do sandbox; a repetição usou uma pasta nova e isolada no runtime.
- Hash do banco principal confere com o checkpoint da Fase 9. Nenhuma migration ou gravação no banco principal foi necessária.

Resultados estruturados e hashes das evidências em [checks](homologation-2026-10-27-checks.json). Testes históricos do núcleo continuam nos relatórios anteriores e não são contados como novas execuções completas nesta rodada. Verificações posteriores ao empacotamento ficam no recibo externo, ao lado do ZIP.

## n8n e aceites pendentes

A candidata **n8n 2.45.4** foi resolvida apenas em lockfile privado com Node 24.22.1 e scripts de instalação desativados. Não foi instalada ou iniciada. A auditoria retornou 167 itens: 3 baixos, 75 moderados, **81 altos e 8 críticos**. As contagens incluem dependências transitivas e avisos propagados; não representam CVEs distintas ou exploração comprovada. [Evidência resumida](../security/homologation-2026-10-27.json).

O runtime 2.44.6 permanece preservado e bloqueado. Não se aplicou o downgrade sugerido pelo npm. A partida só poderá ser reconsiderada após árvore corrigida, nova auditoria e reexecução dos quatro workflows; o consumidor próprio do Chronos permanece disponível.

QA visual, teclado, contraste, responsividade e capturas reais permanecem pendentes pelo bloqueio anterior da automação de navegador. Power BI Desktop não foi encontrado nos caminhos padrão/PATH consultados; importação e medidas no aplicativo continuam sem validação nativa. Permanecem ainda revisão das lacunas funcionais, infraestrutura/operação e aceite final. `release_ready=false`, `published=false`.

## Entrega

Pacote local: `releases/chronos-1.0-homologacao-2026-10-27.zip`, com fontes, documentação, fixture, testes e build. Manifest interno e recibo externo permitem verificar os hashes. O pacote anterior da Fase 10 foi preservado. Bancos, contas, credenciais e runtimes não são distribuídos. Nenhum outro projeto foi modificado e nada foi publicado.
