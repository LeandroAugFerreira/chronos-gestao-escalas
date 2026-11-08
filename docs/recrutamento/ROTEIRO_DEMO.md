# Chronos — roteiro de demonstração para entrevistas (3 minutos)

**Atenção:** demonstração web é visualização estática de benchmark antigo, não solver rodando online. Todas as pessoas/demandas são fictícias.

## 00:00–00:25 | Problema

Abra [página do projeto](https://leandroaugferreira.github.io/chronos.html).

**Fala sugerida:** “O Chronos conecta contratos, competências, indisponibilidades, demanda e regras para comparar cenários de jornada. Ele calcula propostas para revisão humana, não autoriza uma escala automaticamente.”

## 00:25–01:00 | Modelo e premissas

Abra [tour interativo](https://leandroaugferreira.github.io/chronos-demo.html) e selecione **3 profissionais**. Mostre 1.440/1.440 postos-minuto em uma atividade de um dia, sob parâmetros sintéticos.

**Fala:** “Um caso pequeno com três turnos fictícios de oito horas permite cobertura numérica total; não significa dimensionamento hospitalar validado.”

## 01:00–01:35 | Lacuna explícita

Alterne para **2 profissionais**. Mostre 960 de 1.440 postos-minuto, lacuna 480, 66,7% de cobertura.

**Fala:** “Aqui está a decisão importante: o sistema não pode esconder uma demanda descoberta. O custo menor é de uma escala parcial — não é economia real.”

## 01:35–02:05 | Comparação verificável

Compare a política first-fit e CP-SAT. As duas obtiveram mesma cobertura e mesmo custo no caso pequeno. Abra [benchmark.json](../portfolio/benchmark.json) e [fixture](../../data/synthetic/portfolio_benchmark.json).

**Fala:** “Prefiro mostrar um resultado honesto: este microensaio não prova superioridade em cobertura ou custo; comprova a reprodutibilidade e o relato transparente de limitações.”

## 02:05–02:35 | Arquitetura real

Abra [diagrama](ARQUITETURA.md), [solver](../../backend/app/services/optimizer.py) e [revisão de propostas](../../backend/app/api/optimization.py).

**Fala:** “A API captura um snapshot, o worker resolve restrições por OR-Tools, um verificador independente confere o resultado e outra pessoa precisa aprovar a proposta. Há bloqueios para entradas alteradas.”

## 02:35–03:00 | Evidências e limitações

Mostre [execução do GitHub Actions](https://github.com/LeandroAugFerreira/chronos-gestao-escalas/actions/runs/42512605602).

**Fala:** “O CI valida o backend, componentes React e um login real no Chromium com SQLite fictício. Para uso em produção, ainda faltam revisões jurídicas, segurança/infra, PostgreSQL e a homologação de todos os fluxos.”

## Contingências

- Sem internet: use a fixture e os Markdown locais; não alegue demonstração live.
- Sem instalador: o tour estático e as evidências são suficientes para uma triagem; vídeo/EXE exigem acesso local.
- Não compartilhar JWT/senha do runner, pois são aleatórios e descartáveis.
- Não desabilitar bloqueio de n8n para demonstrar workflows.
- Distinguir **Hospital Horizonte (350 pessoas sintéticas)** de **microbenchmark (3/2 profissionais, 1 atividade/dia)**.
- Não falar em ROI, ganhos de produtividade ou conformidade legal não medidos.

[15 perguntas](ENTREVISTA_TECNICA.md) · [Estudo de caso](ESTUDO_DE_CASO.md).
