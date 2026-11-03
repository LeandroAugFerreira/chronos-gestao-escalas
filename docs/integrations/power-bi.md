# Chronos 1.0 — Dataset local para Power BI

Exporte **CSV e Power BI** em Analytics. Escolha explicitamente o cenário e, se desejado e autorizado, uma otimização e uma projeção. Extraia o ZIP numa pasta protegida. O pacote não contém PBIX, credenciais ou conexão ao banco.

## Importação

1. No Power BI Desktop, crie o parâmetro de texto `PastaChronos` com a pasta extraída, sem barra final.
2. Crie uma consulta em branco para cada bloco `let` de `power-query.m`, usando o nome indicado no comentário. O importador usa CSV com vírgula, UTF-8, aspas e tipos explícitos. Datas são ISO, números monetários são inteiros em centavos.
3. Configure somente os relacionamentos de `manifest.json`, cardinalidade um-para-muitos e filtro em um sentido. Desative detecção automática de relacionamentos adicionais por IDs repetidos. As tabelas de fatos não se relacionam diretamente entre si.
4. Crie apenas as medidas de `measures.dax` que existirem no seu pacote. Formate cobertura como percentual e a projeção como BRL. Campos de identificador devem permanecer texto e não devem ser somados.
5. Confira contagens e totais contra o XLSX ou o JSON do mesmo relatório. Uma tabela sem registros não prova resultado zero ou execução bem-sucedida.

## Grãos e relações

| Tabela | Grão | Relacionamento |
|---|---|---|
| units | Uma unidade; nome/fuso no instante de extração | units.unit_id → scenario.unit_id e executions.unit_id |
| scenario | Uma versão selecionada; capacidade mensal simulada | scenario.scenario_id → fatos abaixo |
| coverage | Uma otimização; seu horizonte completo | scenario → coverage |
| proposals | Uma proposta versionada da execução | scenario → proposals |
| assignments | Uma atribuição inteira; inclusão opcional e pessoal | scenario → assignments |
| finance | Uma projeção por mês, 12 meses | scenario → finance |
| executions | Uma tentativa iniciada no mês civil do cenário | units → executions |

Somente as tabelas autorizadas aparecem. `scenario` também contém as medidas de capacidade da versão selecionada; seus valores não devem ser multiplicados por junções com os fatos. Use os relacionamentos em vez de expandir junções que repitam linhas. Não conecte adicionalmente `units` aos fatos ligados a `scenario`, evitando caminhos ambíguos.

## Atualização e segurança

O modelo representa uma extração, não uma conexão ao vivo. Para atualizar, gere outra seleção e substitua **todos** os arquivos juntos. Não anexe pacotes sobrepostos ou alternativas como se fossem fatos independentes. Mantenha o manifest de cada extração para rastreabilidade e compare a mesma versão/período.

RBAC é aplicado na exportação pelo Chronos. O arquivo salvo deixa de consultar permissões da plataforma. Proteja a pasta, evite incluir atribuições quando desnecessário e configure segurança/RLS e audiência antes de eventual compartilhamento. Nenhum compartilhamento, gateway, agendamento na nuvem ou publicação foi configurado.

A estrutura M, os tipos, as chaves e as referências foram verificados nos arquivos gerados. **Execução no Power BI Desktop e medidas no motor DAX permanecem pendentes**; o pacote é uma preparação local, não uma integração com conta Power BI testada.

Referências técnicas: [modelagem em estrela](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema) e [Csv.Document](https://learn.microsoft.com/en-us/powerquery-m/csv-document), documentação Microsoft.
