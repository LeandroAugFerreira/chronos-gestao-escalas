# Chronos 1.0 — Referências da Fase 5

Consultas em 24/10/2026. A fase implementa estimativas configuráveis e não ativa novos limites, taxas, pisos ou divisores legais automaticamente.

- [Decimal — documentação oficial Python](https://docs.python.org/3/library/decimal.html): aritmética decimal e controle explícito de arredondamento. Implementação usa centavos inteiros, contexto Decimal e `ROUND_HALF_UP`; taxas em pontos-base, sem operações monetárias em ponto flutuante binário.
- [EC 141/2026 — Planalto](https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm): o texto consultado prevê transição e preservação salarial, com condições de aplicação. As datas e exceções continuam sujeitas a revisão, conforme fontes da Fase 4. O simulador mantém salários dos snapshots ao mudar metas semanais e não determina automaticamente a incidência da emenda em cada contrato.

Não foram fornecidos instrumentos coletivos, políticas reais de encargos, pisos, benefícios ou divisores profissionais. Por isso cada componente exige sua própria fonte e condições. Rateio por dias civis, razão de conversão de minutos e volumes de adicionais são premissas declaradas de simulação; não representam uma conclusão sobre a folha legalmente devida.
