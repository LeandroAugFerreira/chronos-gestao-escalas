# Chronos 1.0 — demonstração para Windows

O executável reúne a interface compilada, a API local, o processador de otimização e os recursos de demonstração. Não exige Python ou Node.js instalados no computador do visitante.

Abra `Chronos.exe` e aguarde a janela indicar que está pronto. O endereço local é exibido nessa janela. Mantenha-a aberta durante o uso. A conta pública de consulta usa organização `horizonte`, usuário `demo` e senha `ChronosDemo@2026`. Para testar edições e simulações, crie seu próprio administrador no botão da janela de controle.

Os dados são criados em `%LOCALAPPDATA%\Chronos\1.0-demo`. O executável não transporta `.env`, banco, conta administrativa ou segredo da instalação de desenvolvimento. A primeira abertura cria uma base a partir do fixture sintético e um segredo próprio da instalação. Execuções seguintes preservam os cadastros.

O botão Manual abre o guia HTML incluído no pacote. O mesmo guia fica disponível no portfólio. O agendamento automático e n8n permanecem desativados. Esta é uma demonstração local para avaliação, sem assinatura digital ou liberação para produção.

## Compilação

Prepare o ambiente Python de desenvolvimento, o build do frontend e o PyInstaller no subdiretório `build-tools` de um runtime fora do projeto. Prepare também o guia HTML com `scripts/prepare_portfolio_site.py --manual-only`.

Execute `scripts/build-windows.ps1 -RuntimeDir <runtime>`. A especificação PyInstaller contém uma lista explícita de recursos. Caches, bancos e configurações pessoais não fazem parte dos dados da distribuição.

Valide a saída com `Chronos.exe --self-test --data-dir <pasta-nova-vazia>`. O teste inicializa uma instalação isolada, verifica a interface servida por HTTP, login e logout com CSRF, restrições da conta demo, criação de administrador, fila real de otimização, OR-Tools em subprocesso, persistência e integridade do SQLite. O relatório é salvo em `self-test.json` nessa pasta.
