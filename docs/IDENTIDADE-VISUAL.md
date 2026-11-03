# Chronos 1.0 — identidade da interface

Direção aplicada em 1 de novembro de 2026. Autoria: Leandro Augusto Ferreira.

A identidade parte de pessoas e tempo em equilíbrio. A referência ao Ateliê Verde está na atenção à marca, na entrada com personalidade e na continuidade entre os módulos. O Chronos usa seus próprios elementos, adequados a empresas de diferentes segmentos.

## Elementos

- **Símbolo:** dois arcos abertos formando um C, ponteiros e marcações de um mostrador. A mesma construção aparece no login, na navegação, no carregamento e no favicon.
- **Cores:** azul de tinta `#101f2a`, cobre claro `#e9b98c`, cobre escuro `#91552d`, papel `#f5f1e9` e verde petróleo para destaques secundários. O cobre escuro serve aos fundos claros; o cobre claro, aos escuros.
- **Tipografia:** Georgia para marca e títulos principais; Segoe UI/system-ui para controles e dados. Fontes locais mantêm a identidade disponível sem conexão externa.
- **Assinatura:** monograma `lf.` e nome Leandro Augusto Ferreira no login e no rodapé. No celular, a assinatura acompanha o formulário.
- **Grafismos:** mostrador vetorial na entrada e barras de ritmo na visão geral. São elementos decorativos, ocultos de tecnologias assistivas. Não representam plantões ou cobertura calculada.

## Aplicação

O login tem composição editorial, formulário com rótulos, mensagens de validação e botão para mostrar/ocultar a senha. Após erro de acesso, o campo é limpo e volta a ocultar a senha.

A área autenticada mantém a preferência de tema existente. A navegação é agrupada em Planejamento, Estrutura & operação e Administração. Grupos sem destinos autorizados são omitidos. O menu possui rolagem própria em telas baixas; no celular, mantém a abertura pelo botão de menu.

O dashboard mantém indicadores, filtros e gráficos ligados à API. A aparência dos componentes compartilhados se estende aos cadastros, tabelas, formulários, modais, calendário e demais módulos. Cadastro, permissões e regras de cálculo não foram alterados nesta revisão.

## Manutenção

`frontend/src/styles/app.css` contém a estrutura de base. `frontend/src/styles/identity.css`, importado em seguida, centraliza as cores, os elementos de marca, a apresentação dos controles e os ajustes de responsividade desta direção. Os elementos vetoriais compartilhados ficam em `frontend/src/components/identity.tsx`; o layout autenticado fica em `frontend/src/layouts/app-shell.tsx`.

A interface não depende de imagens, fontes ou serviços externos para apresentar a marca. Nenhum arquivo do Ateliê Verde foi modificado. Esta revisão é local; não atualiza automaticamente o portfólio, os vídeos, o manual público ou um executável distribuído anteriormente.

## Verificação desta revisão

- Build de produção concluído com TypeScript e Vite.
- Suíte do frontend: 88 testes aprovados. Após concluir a revisão do controle de senha, os 10 testes de páginas foram executados novamente e aprovados.
- Verificações HTTP locais: login, estilos, layout e favicon responderam com sucesso; o proxy `/api/v1/health/ready` retornou `ready`.
- Os nove pares principais de texto/fundo, incluindo os dois temas, a navegação e o login, tiveram contraste calculado acima de 4,5:1. Isso não substitui uma auditoria de acessibilidade da interface completa.
- Conferência visual e interação em navegador real permanecem pendentes. A prévia local foi disponibilizada em `http://127.0.0.1:5187/login`; o encaminhamento para o painel do aplicativo foi solicitado.

O build emite avisos sobre comentários de pureza de uma dependência e sobre o tamanho do bundle principal. Ambos são avisos; a compilação foi concluída. Não houve atualização de dependências nesta revisão.
