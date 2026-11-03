# Chronos 1.0 — Fase 9: segurança e fluxo integrado

O checkpoint adiciona limites HTTP antes do parsing, validação de origens/configuração de produção, cabeçalhos de segurança, erros inesperados seguros, recuperação em cópia isolada e testes do fluxo completo entre módulos. [Achados e bloqueios](../security/phase9-findings.md) e [procedimentos de recuperação](../operations/recovery.md) descrevem as condições operacionais.

## Limites e sessão

`RequestLimits` é middleware ASGI que conta bytes inclusive sem Content-Length, verifica framing, recusa compressão de entrada e limita o tempo de recebimento do corpo. Defaults: 1 MiB/10 s, ajustáveis dentro de limites tipados por `CHRONOS_MAX_REQUEST_BYTES` e `CHRONOS_REQUEST_BODY_SECONDS`. O prazo não é timeout do solver ou do processamento de negócio. Tamanho excedido retorna 413, framing inválido 400, compressão 415 e recebimento lento 408, sem executar o endpoint.

A API adiciona nosniff, DENY, no-referrer e Permissions-Policy; erros e respostas API mantêm no-store e identificador de correlação. A resposta 500 é genérica. Origens são explícitas, sem credenciais/caminhos/curingas; produção exige HTTPS e cookie Secure, além de banco/segredo válidos. OpenAPI/docs não ficam públicos no perfil production. Isso não instala TLS ou configura os arquivos estáticos.

JWT, refresh rotacionado/HttpOnly, CSRF ligado à família, rate limit de login e escopos existentes continuam ativos. Testes verificam os seis papéis na API, sem tratar guardas de interface como autorização suficiente. O bloqueio de organização nas mutações permanece; permissões financeiras/pessoais e de unidades continuam independentes.

## Correção de revisão

`WorkPattern` já tinha incremento de revision no endpoint de revisão, mas faltava a coluna no modelo/banco. A migration 010_pattern_revision acrescenta inteiro não nulo com default 1, sem reescrever os dados anteriores. O incremento foi mantido; o digest passa a incluir a coluna. Mesmo uma nova conferência de jornada já validada muda revision e torna o digest anterior obsoleto. Tests demonstram resposta 409 para reapresentação antiga.

Schemas e revisão de catálogo continuam diferentes de aprovação jurídica universal. Nenhum regime, contrato ou regra é automaticamente validado pela migration. Propostas históricas permanecem armazenadas; revisões antigas podem exigir nova conferência com o digest atual. O endpoint ready exige head 010. São dez migrations e 41 tabelas de domínio.

## Recuperação e integrações

SQLite usa backup consistente, manifest/hash e verificação de integridade. Restauração aceita apenas destino novo fora do projeto/OneDrive. PostgreSQL é validado por dump/restore nativo em banco descartável. A política comum da cópia revoga sessões e chaves, desabilita rotinas, cancela efeitos pendentes e audita a recuperação. Não troca o banco operacional nem publica escalas.

O consumidor local continua executando A01–A07. A partida n8n foi bloqueada após auditoria da árvore atual e da candidata mais recente, ambas com avisos altos/críticos. Arquivos/runtime foram preservados. Mocks e receptores de teste não constituem liberação desse runtime. Nenhuma integração externa foi habilitada.

## Validação e limites de aceite

O fluxo integrado em ASGI/HTTP inclui revisão via API, projeção, OR-Tools real, submissão, recusa de autoaprovação, aprovação por segundo usuário, automação local, analytics, exportações e nova instância da aplicação lendo o estado persistido. Dados de base, vínculos de contratos e regras para esse caso são fixtures explícitas e sintéticas, sem valor normativo.

O smoke HTTP real usa proxy Vite, cookies/CSRF, API, CLI do worker e exportações; demonstra que premissas pendentes continuam bloqueando submissão. Não usa navegador. Excel nativo foi conferido em somente leitura; Power BI Desktop não foi executado. O bloqueio anterior de automação visual permanece respeitado. O checkpoint não libera produção nem satisfaz os itens de aceite visual ainda pendentes.
