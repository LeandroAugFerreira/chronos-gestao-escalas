# Chronos 1.0 — LaborRules Engine

Especificação da Fase 1, não implementação de validação jurídica. Fontes consultadas em 24/10/2026. Leitura documental e validação de aplicabilidade são estados distintos. Nenhuma regra é ativada nesta fase.

## Registro de fontes e pendências

| Fonte primária | Dispositivo a modelar | Situação |
|---|---|---|
| [Constituição Federal](https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm) | art. 7º, XIII, XIV, XV e parágrafos pertinentes | Vincular texto e alterações por vigência na Fase 4 |
| [EC 141/2026 — texto oficial](https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm) e [publicação original na Câmara](https://www2.camara.leg.br/legin/fed/emecon/2026/emendaconstitucional-141-16-outubro-2026-800062-publicacaooriginal-181622-pl.html) | arts. 1–10; art. 6º I/II e art. 10 I | Documento localizado; aplicação por contrato/categoria ainda pendente |
| [CLT compilada](https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm) | arts. 58, 59, 59-A, 66, 67, 71, 73 e disposições de negociação coletiva | Revisar texto vigente e interações com regras superiores antes de implementação |
| [Cofen, Resolução 743/2024](https://www.cofen.gov.br/resolucao-cofen-no-743-de-12-de-marco-de-2024/) | Revogação da Res. 543/2017 e referência ao Parecer Normativo 01/2024 | Cadastro de fonte; não fornece mínimo universal por setor |
| [Cofen — esclarecimento do planejamento de pessoal](https://www.cofen.gov.br/entenda-a-decisao-do-cofen-sobre-o-dimensionamento-da-equipe-de-enfermagem/) | Planejamento da força de trabalho pelo enfermeiro | Revisão especializada e atividade/localidade necessárias |
| Acordos/convenções do Hospital Horizonte | Escopo, categoria, localidade, datas e regras específicas | Nenhum instrumento real fornecido; cadastrar somente documento fictício claramente identificado ou fonte validada |

A EC consultada descreve progressão para 42h dois meses após publicação e 40h um ano depois desse prazo, além de repouso, proteção salarial e situações diferenciadas. O prompt de origem mencionava 15/12/2026. O texto usa meses, não sessenta dias. A especificação conserva o prazo literal e registra a divergência; não ativa data calculada. Contagem da vigência, exceções e aplicação a contratos exigem revisão. Não presumir liberação do 12x36, dispensa de controle ou aplicação indistinta a vínculos públicos/privados.

## Modelo de regra

Campos obrigatórios: `rule_key`, versão, nome, descrição, fonte/URL/documento/hash, dispositivo, publicado_em, valid_from/until, escopo (organização, localidade, categoria, vínculo, contrato, acordo), parâmetros tipados, responsável, validation_status, validador/data e histórico. Estados de configuração: draft → pending_review → validated → active → retired. Validação documental não significa aprovação jurídica; a ativação exige ambas e responsável autorizado.

Não executar expressões Python/SQL fornecidas pelo usuário. Avaliadores registrados por tipo e esquemas Pydantic controlam limites, descansos, intervalos, dias consecutivos, semanal/média compensatória, adicional noturno e condições especiais.

## Avaliação

1. Receber snapshot da versão de cenário, contratos, acordos e qualificações.
2. Resolver organização, unidade/fuso, categoria e vínculo para cada pessoa e intervalo. Segmentar o horizonte em mudanças de contrato, regra, acordo e credencial.
3. Localizar regras aplicáveis com prioridade e justificativa explícitas; fonte hierárquica e alcance não serão reduzidos a "regra mais recente vence". Conflito irresolvido gera pendência.
4. Contabilizar duração real, minutos remuneráveis, pausas, descanso entre jornadas e repouso por janelas configuradas. Não confundir hora noturna reduzida com tempo decorrido.
5. Avaliar acumuladores com histórico anterior e compromissos seguintes ao horizonte; evitar escala que parece válida apenas por cortar domingo/meia-noite.
6. Emitir resultado por regra, pessoa e intervalo com evidência e versão. Agregar sem esconder violações ou ausências de avaliação.
7. Snapshot e resultado imutáveis. Mudança cria nova versão, sem retroatividade automática em escala aprovada.

Saídas obrigatórias: **Conforme com as regras configuradas**, **Não conforme com as regras configuradas**, **Pendente de validação jurídica**, **Não avaliado por ausência de regra aplicável**. Violação conhecida permanece evidenciada mesmo se houver regra ausente. Na submissão/aprovação, uma pendência ou falta de regra impede atestar conformidade; não impede explorar uma hipótese claramente marcada.

## Famílias de regras a implementar na Fase 4

- Limites diários, semanais, por ciclo/média; horas extras e compensação; preservação salarial quando aplicável.
- Pausas intrajornada com cobertura durante a pausa; interjornada; repouso e dias consecutivos; domingos/feriados por localidade.
- Regimes 5x2, 4x3, 12x36, plantões e especiais associados ao fundamento e ao contrato; nenhum enum equivale a permissão legal.
- Validade de competências/habilitações e equivalências autorizadas. Credencial vencida no meio do plantão retira elegibilidade naquele intervalo.
- Requisitos operacionais parametrizados e normas profissionais com metodologia/revisão. Sem quantitativo hospitalar universal embutido no motor.

## Testes previstos

Fronteiras antes/no/depois da vigência; contratos simultâneos; ausência de acordo; 12x36 sem fundamento; 4x3 hipotético; plantão que cruza meia-noite e mudança de regra; credencial vencida; descanso com histórico anterior; domingo/feriado; conflito entre fontes; jornada noturna; regra ausente; atualização sem alterar versões aprovadas. Esses testes serão implementados com o motor, não são alegados como executados na Fase 1.
