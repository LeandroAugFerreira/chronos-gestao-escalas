# Chronos 1.0 — Windows, identidade e portfólio

Edição de demonstração de 01/11/2026. A publicação de apresentação/downloads é distinta de uma liberação operacional de produção.

## Resultado validado

- Frontend com identidade própria: build de produção concluído e 88 testes aprovados; os 10 testes de páginas foram repetidos após concluir o controle de senha.
- Regressão backend nesta entrega: 47 testes aprovados, incluindo otimizador, worker real, cancelamento, revisão das propostas e empacotador. Backend de teste: SQLite. Não houve alteração do banco de desenvolvimento.
- Iniciador em fonte: instalação isolada, autenticação com CSRF, restrições demo, criação inicial de administrador, fila real de otimização, subprocesso OR-Tools, seed idempotente e integridade SQLite aprovados.
- Executável compilado com PyInstaller 6.22.3 e Python 3.13, sem console, com interface/API no mesmo endereço de loopback. Testado em Windows 11 x64 com PATH limitado ao System32, sem Python ou Node disponíveis no PATH e com variáveis de conexão herdadas inválidas, ignoradas pela aplicação.
- O mesmo autoteste passou no binário: `frozen=true`, OR-Tools `OPTIMAL`, fila concluída, 350 colaboradores preservados e encerramento sem processo ou porta remanescente do teste.
- O scanner examinou 4.053 conteúdos, incluindo módulos Python e arquivos descomprimidos. Nenhum segredo configurado, senha administrativa pessoal, e-mail administrativo pessoal ou arquivo de banco/configuração privada foi encontrado.
- Manual HTML com índice e 11 tópicos, acesso por nova aba e roteiro para visitantes/recrutadores. Sem incorporação ou dependência de PDF nas páginas atuais de apresentação/manual.

Os resultados estruturados e o SHA-256 do binário constam em `windows-exe-2026-11-01.json`.

## Distribuição

O EXE contém runtimes e recursos necessários, mas não contém banco ou contas da instalação do autor. Cria sua base fictícia, conta demo e segredo por instalação. O administrador escolhe as próprias credenciais. O worker do otimizador usa um processo separado e protocolo de arquivos, compatível com a aplicação sem console.

O manual incluído no executável é HTML e pode ser lido sem instalação de visualizador PDF. A página do portfólio mantém o código-fonte como alternativa para análise técnica e oferece o aplicativo como caminho principal de experimentação.

## Limites mantidos

Executável sem assinatura digital. Não foi realizada conferência visual automatizada em navegador real. A inicialização da janela Tk foi testada; isso não equivale à avaliação visual integral da interface.

n8n e scheduler continuam desativados. Permanecem pendentes homologação operacional, avaliação no Power BI Desktop, revisão de segurança aplicável à produção e os demais gates anteriores. Contagens e resultados fictícios não comprovam dimensionamento, validade jurídica universal ou economia real.

O conteúdo para o Destaque do LinkedIn foi preparado em `docs/portfolio/linkedin-destaque.md`. O acesso ao Chrome não foi executado: a revisão automática retornou falha por limite de uso. Esse bloqueio não é uma avaliação de insegurança e não comprova publicação no LinkedIn.
