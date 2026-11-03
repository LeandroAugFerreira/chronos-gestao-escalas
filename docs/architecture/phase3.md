# Chronos 1.0 — Frontend integrado e sessão web (Fase 3)

## Interface entregue

React/TypeScript/Vite com Router, TanStack Query, Tailwind 4, React Hook Form/Zod, Recharts e ícones temporais/corporativos neutros. Dark inicial, light persistido, layout com sidebar, breadcrumb, navegação móvel, cards, tabelas paginadas, filtros, formulários e diálogos. A identificação permanece Chronos 1.0; Hospital Horizonte é a organização de demonstração, obtida da API.

Telas: login; visão geral; colaboradores e detalhes; setores; unidades; catálogos; criação/listagem de acessos; auditoria. Permissões e escopos controlam rotas e ações visíveis, sem substituir a autorização do backend. Perfis sem acesso a pessoas não recebem a tela de colaboradores. Cadastro/edição respeitam revisão otimista, chave idempotente na criação, erros de rede e confirmação após resposta do servidor. Campos ficam bloqueados durante o salvamento.

Formulários possuem labels e erros associados por ID, mensagens anunciadas, botão de envio pendente e validação antes do POST. Diálogos gerenciam foco, Escape e Tab; a página possui link para pular ao conteúdo. O CSS inclui breakpoints móveis e redução de movimento. Esses recursos não equivalem a auditoria visual completa: navegação real/responsividade/contraste em navegador continuam sem verificação nesta sessão.

## Sessão e segurança

O navegador usa `/api/v1/session/csrf`, `/session/login`, `/session/refresh` e `/session/logout`, pelo proxy de mesma origem. A API original `/auth/*` permanece disponível para clientes Bearer/Swagger.

O refresh opaco fica em cookie **HttpOnly, SameSite=Strict, host-only**, sem Domain. Em produção, `CHRONOS_COOKIE_SECURE=true` é obrigatório, com nomes `__Host-chronos-refresh` e `__Host-chronos-csrf`, Secure e Path=/. HTTP sem Secure é reservado ao desenvolvimento local em loopback. Cookie não é interpretado como autenticação de endpoints de negócio: estes continuam exigindo Bearer.

CSRF é um token assinado por HMAC, com nonce/data, ligado à família de sessão (ou contexto anônimo antes do login) e duração de uma hora. Um cookie HttpOnly guarda a cópia; a rota de bootstrap retorna o token por JSON e o cliente o envia em `X-CSRF-Token`. POSTs de sessão exigem correspondência, assinatura válida e Origin da allowlist; requisições marcadas cross-site são rejeitadas. Login troca o contexto e revoga a família anterior daquele navegador. Não há refresh token na resposta JSON web.

Access token, CSRF e identidade ficam somente em memória. O único valor persistido pelo frontend é `chronos-theme`. Atualizar a página restaura sessão pelo cookie, sem pedir credenciais novamente quando a sessão é válida. Respostas 401 provocam uma única renovação e uma repetição autorizada; 403 não amplia permissão. Renovação concorrente na mesma aba usa single-flight; Web Locks, quando disponível, serializa entre abas. BroadcastChannel comunica apenas alteração de sessão, sem tokens. Navegadores sem essas APIs mantêm a proteção do servidor, podendo precisar de novo login em uma disputa de renovação entre abas.

O cliente compara a identidade retornada na renovação. Se outra conta assumiu o navegador, não repete uma operação pendente com essa identidade. Mudança/saída limpa e cancela o cache de consultas. Falha de rede ao sair não é exibida como logout concluído: a interface mantém a sessão e permite tentar a revogação novamente.

## Dashboard e dados

`GET /analytics/overview` calcula dados diretamente do banco e aplica escopo de organização/unidade. Retorna origem, instante da consulta, organização, pessoas ativas/inativas, setores, unidades, distribuição por setor/grupo e jornadas contratuais vigentes. A média semanal usa contratos vigentes de pessoas ativas, na data local da organização, e não representa capacidade operacional disponível.

Gráficos usam esses resultados; o gráfico de setores mostra até oito maiores e oferece lista textual acessível de todos. Sem dados, a interface mostra estado vazio; falhas são explícitas. Cobertura, custos projetados e conformidade permanecem **não calculados/não avaliados**, sem percentuais fictícios.

O frontend operacional deixou de usar `/demo/summary`; a rota permanece como fixture histórica da Fase 1 para compatibilidade. Atualização no banco aparece após invalidação das consultas, não por alteração de valores fixos no frontend.

## Complementos do backend

Migration `005_catalog_revisions` adiciona revisão a funções, competências e qualificações, mantendo 23 tabelas. PATCH de unidades/setores/catálogos exige revisão atual. Alteração de lotação exige permissão na unidade atual e na de destino, referências do mesmo tenant e setor compatível com a unidade. Setor com pessoas não muda de unidade até que a equipe seja transferida. Auditoria acompanha as alterações na mesma transação.

A mudança de função/lotação não atribui automaticamente competências ou habilitações e não avalia validade jurídica de jornada. Jornadas de referência são somente leitura; calendário e LaborRules executável continuam para a Fase 4.

## Referências

- [OWASP — prevenção de CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
- [Starlette — cookies em respostas](https://starlette.dev/responses/).
- [Tailwind — integração Vite](https://tailwindcss.com/docs/installation/using-vite).
- [React Hook Form — resolvers](https://react-hook-form.com/integrations).
