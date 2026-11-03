# Chronos 1.0 — Exportação cadastral, 27/10/2026

Esta rodada de homologação continua a Fase 10 e atende parte da lacuna RF03: exportação do cadastro básico de colaboradores pela interface e pela API. Hospital Horizonte permanece o cenário fictício, com 350 pessoas e 19 setores. Não há alteração do banco principal ou publicação.

## Comportamento entregue

Na tela **Colaboradores**, **Exportar CSV** usa a busca, unidade, setor, situação e ordenação selecionados. Exporta todas as páginas da seleção, restritas à organização e às unidades autorizadas para `people:read`. Uma permissão global de outra família não amplia esse escopo. A consulta compartilhada com a listagem evita diferenças de filtros e ordem entre os dois caminhos.

O CSV contém apenas os dez campos básicos: identificador da pessoa, organização, unidade, setor, função, nome, matrícula, situação, marcação de dado sintético e revisão. Não consulta contratos, salários, preferências, qualificações, evidências ou ausências. Unidade/setor/função são IDs para relacionamento com os respectivos catálogos; não é uma exportação completa de todos os vínculos.

O arquivo usa UTF-8 com BOM, vírgula, CRLF e aspas CSV para campos que precisam delas. Textos com início interpretável como fórmula recebem apóstrofo de proteção, como nos relatórios existentes. IDs e matrícula devem ser importados como texto para preservar sua representação. O download não mantém o controle de acesso do Chronos; o operador deve proteger o armazenamento do arquivo.

A API recusa seleções acima de 20.000 linhas ou 8 MiB, sem entregar parte dos registros. Uma seleção vazia gera cabeçalho e zero linhas. A resposta informa contagem, data UTC de extração, tamanho e SHA-256; o cliente verifica os bytes antes de preparar o download. Submissões simultâneas pela mesma ação são impedidas e falhas não geram mensagem de sucesso. Se os filtros mudarem durante a preparação, o resultado continua identificado como a solicitação original.

O evento `people.export` registra ator, correlação, contagem, tamanho, hash e filtros não textuais. A busca é registrada apenas como presente/ausente, sem copiar nomes, matrículas ou o CSV para a auditoria. Preparar o arquivo não cria evento de alteração cadastral ou automação. A auditoria confirma preparação; não comprova que o navegador salvou ou que alguém abriu o arquivo.

## Validação e limites

- **87 testes frontend aprovados**, incluindo 6 novos testes da exportação; suite completa em JSDOM.
- **75 testes backend aprovados** nos módulos de cadastros, analytics e exportação cadastral, incluindo 4 casos novos executados em SQLite e PostgreSQL (8 execuções). Não é uma repetição de toda a suite backend.
- TypeScript e build Vite aprovados: 2.348 módulos e build em 33,31 s. As duas anotações de comentários do Zod foram removidas pelo Rollup com aviso; sem falha. O backend emitiu o aviso de depreciação já existente de TestClient/httpx; nenhuma dependência foi alterada nesta rodada.
- Identidade, versão, hash do Prompt Mestre e documentos obrigatórios conferidos pelo validador. PostgreSQL de teste encerrado pelo script após a execução.

Resultados desta rodada, perfis de banco, hashes dos relatórios de teste e fontes estão em [checks](people-export-2026-10-27-checks.json). Os testes verificam reconciliação com todas as páginas da API, filtros/ordem, campos permitidos, Unicode e quebra de linha, proteção de fórmula, auditoria, limites e isolamento de organização/unidade. A interface é exercitada em JSDOM, incluindo filtros reais da página, ausência de paginação no pedido, reenvio, integridade e bloqueio de duplo clique.

O backend gerou relatório JUnit. Para o frontend, a evidência é a saída final do processo concluído com código zero; o comando não produziu o XML solicitado e sua saída foi registrada como transcrição, sem repetir os testes apenas para gerar outro formato.

Os testes históricos mantêm seu escopo e data nos relatórios anteriores. Não houve nova auditoria n8n nesta rodada: permanece vigente a [análise de 27/10](../security/homologation-2026-10-27.json), com candidata 2.45.4 não instalada e execução bloqueada. QA de navegador/capturas e Power BI Desktop seguem pendentes. Não se declarou validação nativa de Excel para este novo CSV.

RF03 permanece parcial: importação genérica, edição/exclusão ampla, encerramento contratual e exportação dos vínculos especializados ainda precisam de implementação e validação. Não há nova migration, instalação de dependências ou ativação de automações.

## Entrega local

Pacote desta rodada: `releases/chronos-1.0-exportacao-cadastral-2026-10-27.zip`. Inclui fontes, testes, documentação, fixture e build, sem banco ativo, contas, segredos ou runtime. O manifest interno e o recibo externo verificam a integridade; reprodutibilidade e inicialização da cópia extraída ficam no recibo posterior ao empacotamento. Os pacotes anteriores foram preservados. `release_ready=false`, `published=false`.
