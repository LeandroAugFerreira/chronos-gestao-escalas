# GitHub Actions — preparação local

Os workflows estão versionados neste repositório. Resultados remotos devem ser consultados na [página de Actions](https://github.com/LeandroAugFerreira/chronos-gestao-escalas/actions); as evidências locais de preparo são registradas separadamente. Foram preparados/revisados com permissões de leitura e sem referência a secrets do autor, deploy, prefeitura, SMTP de operação ou conta pessoal de IA.

Os novos fluxos de testes usam apenas dependências já declaradas. As referências checkout, setup-python e setup-node foram conferidas nos README oficiais em 02/11/2026 e usam v7 nas cópias preparadas. Não foram inventados hashes de commits. A execução em Linux e o provisionamento do runner ainda precisam de comprovação no GitHub.

O workflow de teste proposto está em .github/workflows/tests.yml. Banco de testes é criado pelas fixtures; não existe .env privado na cópia. O n8n não é instalado ou iniciado pelos novos jobs.

Referências primárias consultadas: [checkout](https://github.com/actions/checkout/blob/main/README.md), [setup-python](https://github.com/actions/setup-python/blob/main/README.md), [setup-node](https://github.com/actions/setup-node/blob/main/README.md). A consulta confirmou os exemplos com v7; os jobs propostos ainda não foram executados no GitHub.
