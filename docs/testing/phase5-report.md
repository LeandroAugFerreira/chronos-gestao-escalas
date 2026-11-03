# Chronos 1.0 — Relatório da Fase 5

Data: 24/10/2026. Entrega local limitada ao projeto Chronos e ao runtime isolado. Nenhuma publicação, cobrança, pagamento ou envio externo de dados de negócio foi realizado.

## Entrega efetiva

- Cenários imutáveis por unidade/população/mês, com fonte, chave/versão, antecessora explícita, autor, fingerprints e snapshots separados de capacidade, evidências e salários.
- Capacidade por calendário ou hipótese de ciclo estruturado; competências, validade de habilitações, indisponibilidades e orçamento contratual considerados. Demanda por atividade parametrizada com fonte; nenhuma razão hospitalar universal cadastrada.
- LaborRules reutilizado: todos os plantões persistidos no mês no modo calendário; amostra de um plantão por pessoa no modo ciclo. A amostra não prova a conformidade da hipótese completa.
- Projeções financeiras imutáveis de 12 meses com centavos/Decimal, base salarial preservada ao mudar meta semanal, rateio civil declarado, contratações hipotéticas, parcelas fixas/percentuais/horas, recorrência, sazonalidade e exclusões justificadas.
- Taxas, bases, salário hipotético, divisor, volume e conversão de minutos explícitos; sem alíquota/piso/divisor legal universal. Categorias ausentes permanecem pendentes.
- Comparativos de capacidade/custos, checagem salarial nominal limitada e sensibilidade sem alterar originais. Percentual com base zero retorna indefinido.
- Telas Cenários e Simulador financeiro com RHF/Zod, prévia financeira, confirmação de gravação, comparativos, gráfico e tabela mensal reconciliada; permissões e estados de rede.
- Sétima migration Alembic, 28 tabelas e novas permissões. Salários não aparecem em respostas de capacidade; evidências pessoais exigem permissão adicional. Idempotência, isolamento e auditoria mantidos.

Sem geração de escala viável, aprovação ou OR-Tools nesta fase. Arquitetura, fórmulas e limites completos em [phase5.md](../architecture/phase5.md); referências em [fontes da Fase 5](../legal-rules/phase5-sources.md).

## Validação

| Verificação | Resultado final |
|---|---|
| Backend SQLite + PostgreSQL real | 117 passed, zero falhas/skipped, um aviso; 253,43 s |
| Frontend Vitest/JSDOM | 38 passed, cinco arquivos; 53,81 s |
| TypeScript/Vite | Aprovado; 2.340 módulos; 16,90 s |
| HTTP real isolado | Aprovado; 351 pessoas no cenário (350 fixture + uma efêmera); cálculo observado em 4,741 s |
| Prontidão do banco local | HTTP 200; esquema 007; 350 colaboradores e 19 setores |
| Prompt Mestre e fixture | Integridade/reprodutibilidade aprovadas |
| Serviços próprios de teste | Encerrados; portas 8017/5187/5547 sem listener |
| QA visual em navegador | Pendente pelo bloqueio anteriormente registrado |

Resultados finais em [phase5-checks.json](phase5-checks.json); arquivos da etapa em [manifesto](phase5-file-manifest.md). Backend validado em SQLite e PostgreSQL 17.11 real, com schemas de teste isolados. Frontend em Vitest/Testing Library/JSDOM; build TypeScript/Vite executado.

Casos novos incluem arredondamento de meio centavo, rateio parcial, recorrência única sem multiplicação anual, sazonalidade, contratações com vigência, reconciliação de centavos, conversão de minutos, ordem independente de encargos, divisor ausente/inválido, comparação com base zero, ciclo com limite semanal, orçamento exato de quatro semanas, turnos atravessando mês, afastamento parcial, setor de destino, snapshot salarial imutável, proteção contra redução de salário via meta semanal, permissões, idempotência, sensibilidade e restauração da demonstração.

Frontend: fonte obrigatória, conversão de meta semanal para minutos, corpo de capacidade sem salário, sucessão normalizando referências nulas, erro sem perda de formulário, prévia antes de salvar, invalidação ao editar, parcela única explícita, divisor de horas obrigatório, valores elevados/negativos preservando centavos e estados vazios com pré-requisitos. Gráficos são mockados nos testes e conferidos pelos valores tabulares, sem inspeção visual real.

O smoke `backend/scripts/smoke_phase5.py` executa HTTP real por Vite/FastAPI em outro banco sintético. Mantém as verificações de sessão, dashboard, calendário e histórico; acrescenta um cenário com a população completa (350 da fixture + uma pessoa efêmera criada pelo próprio teste), projeção, custo de transição único, comparação e sensibilidade. Servidores encerrados no `finally`; banco principal não é usado pelo smoke. A duração medida do cenário está no JSON, como observação local e sem compromisso de desempenho em outras máquinas.

Avisos conhecidos: depreciação Starlette/httpx e comentários de tree-shaking de Zod removidos pelo Rollup. Não impediram testes ou build. A inspeção em navegador permanece pendente por bloqueio previamente registrado; não foi tentado contorno por outra ferramenta de navegação.

## Correção UTC e banco local

O caso de afastamento parcial revelou perda de deslocamento na entrada/importação anterior de indisponibilidades em SQLite. A API e o seed agora convertem explicitamente para UTC antes da persistência. O teste também usa UTC ao inserir diretamente uma fixture pelo ORM; PostgreSQL já converte instantes com fuso nativamente.

Criado `repair_demo_times.py`: somente desenvolvimento/teste e Hospital Horizonte marcado como demo, IDs/colaborador/motivo/tipo e intervalos exatamente compatíveis com a fixture legada. Não infere fuso de registros manuais, ignora divergências e não reescreve PostgreSQL. É idempotente e auditado. Testes verificam a reparação, a segunda execução, a preservação de alterações manuais e a recusa de produção.

No banco principal, **20 registros sintéticos confirmados foram corrigidos**, zero divergências. Não houve restauração da fixture. Um backup SQLite íntegro do estado anterior à migration foi criado/conferido em `chronos-before-phase5-007.sqlite3` no runtime externo. A migration 007 e a reparação foram aplicadas depois desse backup.

Conferência local: 350 colaboradores, 19 setores, zero cenários/projeções/plantões/regras ativados automaticamente. Prontidão com TestClient no banco principal: HTTP 200, fase 5, esquema `007_scenarios_finance`. Sem criação de conta ou senha padrão. Prompt Mestre e fixture continuam íntegros, com os validadores executados novamente.

Registros legados manuais cujo fuso se perdeu não podem ser corrigidos por inferência segura; exigem conferência da origem. Snapshots já salvos não são alterados pela reparação: é necessário gerar nova versão para incorporar uma correção de cadastro.

## Roteiro e próxima etapa

1. Em Jornadas e regras, cadastrar hipótese de regime com ciclo estruturado, se necessário.
2. Em Cenários, escolher mês/população e calendário ou ciclo, fonte, meta semanal e demanda. Salvar; derivar outra versão para comparar.
3. Em Simulador financeiro, selecionar cenário e informar fontes/parcelas/contratações. Calcular prévia, revisar gráfico/tabela e salvar. Duplicar para ajustar premissas, comparar e explorar sensibilidade.
4. Observar categorias pendentes, escopo da avaliação e fontes. Capacidade agregada/lacuna zero não comprovam cobertura ou viabilidade de escala; projeção não é folha oficial.

Próxima etapa: **Fase 6 — OR-Tools, worker, diagnóstico de cobertura/inviabilidade e aprovação versionada**. Plano em [roadmap](../roadmap.md). n8n/scheduler continuam na Fase 7. Checkpoint ainda sem prontidão de produção e sem publicação.
