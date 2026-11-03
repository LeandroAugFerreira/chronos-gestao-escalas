# Chronos 1.0 — Fontes consultadas na Fase 4

Consulta em 24/10/2026. Referências para o cadastro e a revisão; nenhuma destas páginas ativa regras automaticamente. Fontes públicas não substituem contratos e instrumentos coletivos da organização, que não foram fornecidos. As premissas da fixture continuam sintéticas.

| Fonte oficial | Observação para implementação |
|---|---|
| [CLT compilada — Planalto](https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm) | Arts. 59-A, 66 e 71 tratam de condições de 12x36, descanso entre jornadas e intervalos. A página contém redações históricas e trechos sem vigência: não extrair o primeiro texto encontrado como regra ativa. Exceções e instrumentos aplicáveis precisam de revisão. Os critérios do motor recebem parâmetros explícitos, sem liberar regimes pelo nome. |
| [EC 141/2026 — Planalto](https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm) | O texto consultado apresenta transição em meses a partir da publicação, etapas de redução semanal, condições para acordos e diferentes efeitos no tempo. Não converter automaticamente a data fixa mencionada no prompt original em início de regra. Validar publicação, destinatários e exceções antes de registrar vigências aplicáveis. |
| [Resolução Cofen 743/2024](https://www.cofen.gov.br/resolucao-cofen-no-743-de-12-de-marco-de-2024/) | Revoga a Resolução 543/2017 e remete ao Parecer Normativo 1/2024 para planejamento da força de trabalho de enfermagem. Não foi adotada razão universal de profissionais por setor/leito. O dimensionamento é configurável e será integrado à cobertura/otimização na Fase 6. |

O motor da Fase 4 calcula critérios de planejamento e identifica ausência, pendência e conflito. Não resolve automaticamente hierarquia normativa, excepcionalidades de categoria, instrumentos coletivos ou todas as regras de repouso/noturno. Ver `docs/architecture/phase4.md` para o limite exato de cada avaliador. Evidência da validação é uma declaração auditada do responsável autenticado; contratos e registros profissionais de demonstração não recebem aprovação fictícia.
