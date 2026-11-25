# Chronos 2.0 — evolução da versão 1.0

Data de referência das fontes: **25/11/2026**. Versão demonstrativa, sujeita à revisão humana.

## O que evoluiu

A versão 1.0 organizou pessoas, contratos, competências, calendário, cenários, custos e otimização OR-Tools. A 2.0 preserva esses módulos e acrescenta **Transição de jornadas**: uma comparação explícita por data das referências normativas, da carga contratual, dos repousos declarados e do valor da hora com salário mensal preservado.

O recrutador pode consultar a apresentação e o executável anteriores, examinar a nova comparação, exportar suas premissas e fontes e conferir os testes. A versão não é uma nova aplicação sem vínculo com a anterior.

## Base normativa e recorte

| Fonte primária | Aplicação na comparação |
|---|---|
| [EC 141/2026](https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm) | Transição para 42h em 16/12/2026 e 40h em 16/12/2027; dois repousos; salário preservado; contrato já até 40h sem redução proporcional automática |
| [Decreto 13.173/2026](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/decreto/d13173.htm) | Referências de divisores 210/200, prevalência de divisor menor; tratamento específico de revezamento e 12x36 |
| [Portaria MTE 2.041/2026](https://www.in.gov.br/web/dou/-/portaria-mte-n-2.041-de-19-de-novembro-de-2026-745783275) | Publicada em 23/11; repousos, salário e disciplina complementar; conferir a retificação de 25/11 e instrumentos aplicáveis |
| [Cautelar do STF nas ADIs 8.041 e 8.042](https://portal.stf.jus.br/processos/downloadPeca.asp?ext=.pdf&id=15392248509) | Hipótese explícita de até 8h24 durante a transição sem ACT/CCT até 15/12/2026; compensação e exceções dependem do enquadramento e da evolução judicial |

O texto do Planalto e a decisão integral do STF foram consultados. O leitor do DOU retornou 502 durante a pesquisa; a Portaria foi lida na [reprodução do próprio documento do DOU](https://www.cspb.org.br/UserFiles/files/Regras-5x-2-MTE.pdf). A referência normativa continua sendo o endereço oficial. Não se presume que um comunicado de imprensa substitua o ato.

O perfil `br-ec141-2026.11.25` fixa a data de revisão, os artigos e a interpretação utilizada. Projeções futuras levam aviso de revisão de atos posteriores. Há normas e decisões em evolução: a comparação não certifica conformidade jurídica.

## Comportamento entregue

- Nova área autenticada `/transicao`, disponível a quem tem leitura da organização, sem consulta a salários cadastrados de outras pessoas.
- `GET /api/v1/labor-transition`: perfil e fontes; `POST /api/v1/labor-transition/compare`: cálculo com validação de entrada.
- Limites por etapa e menor carga contratual, contagem declarada de repousos de 24h e valor da hora em Decimal/centavos.
- Comparação com a referência contratual anterior e preservação do salário nominal no cálculo. O aumento do valor da hora não é apresentado como reajuste mensal nem economia.
- Exceção transitória de 8h24 depende de seleção explícita, data e declaração da situação de negociação; continua marcada para revisão.
- 12x36, revezamento, outros regimes e compensação de repousos recebem revisão específica. Não são aprovados/reprovados automaticamente pelo limite diário comum ou por uma simples contagem semanal.
- Exportação JSON com premissas, perfil, fontes, resultados e digest. Resultado anterior é limpo quando as premissas são alteradas.
- Exemplos fictícios pré-calculados para o portfólio, gerados pelo mesmo comparador, sem alegar execução de API ou de solver no site estático.

## Preservação da base

Base Git da evolução: `19791998f55d8f850890b0c3abcd46de6d760f77`. O motor de escalas, as versões persistidas de regras, o algoritmo OR-Tools e seus benchmarks permanecem na base existente. Esta entrega acrescenta comparação de transição; **não aplica uma migração automática de regras a todas as escalas**. A adoção de parâmetros em cenários continua sujeita às fontes e à revisão das regras configuradas.

O executável 2.0 usa a pasta `Chronos/2.0-demo`, separada da demonstração 1.0, sem copiar bancos, administradores ou segredos do autor. O instalador/pacote anterior continua disponível no portfólio. Não há migração destrutiva de banco.

## Verificações

Testes novos cobrem viradas de vigência, divisor mais favorável, salário preservado, contratos menores, hipótese de 8h24, regimes especiais, compensação, rejeição de dados inválidos, autorização da API e digests. O frontend testa submissão, resultado, falha de rede e remoção de comparação desatualizada. Evidências finais e números de testes são registrados ao concluir a entrega.

Para reproduzir a fixture do tour: `python backend/scripts/export_transition_demo.py --check`. A integração n8n e os gates de produção da base não foram liberados por esta atualização.
