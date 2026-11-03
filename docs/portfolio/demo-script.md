# Chronos 1.0 — Roteiro de demonstração

Apresentação sugerida de 12–15 minutos, ajustável ao público. Duração é planejamento de apresentação, não métrica de produtividade do produto. Utilize somente dados fictícios em ambiente isolado; não prepare a apresentação modificando o banco principal ou marcando regras como válidas sem justificativa.

| Etapa | Ação | Mensagem verificável |
|---|---|---|
| 1. Contexto | Apresentar o nome Chronos e o Hospital Horizonte | Produto corporativo configurável; hospital fictício com 350 pessoas e 19 setores, sem dados de paciente |
| 2. Cadastro | Entrar e filtrar visão geral/colaboradores/unidade | Números vêm da API; permissões e escopos limitam campos e menus |
| 3. Jornada | Abrir calendário/regras e mostrar uma prévia | Nome de regime não confirma validade; avaliação depende das regras, vigência e fontes configuradas |
| 4. Alternativas | Selecionar cenários versionados compatíveis | Capacidade agregada, hipóteses e evidências ficam explícitas; uma alternativa não é somada à outra |
| 5. Financeiro | Abrir projeção, parcelas e comparação/sensibilidade | Centavos/Decimal, 12 meses e premissas; redução de jornada não reduz salário automaticamente |
| 6. Solver | Mostrar fila, execução e resultado verificável | OR-Tools respeita restrições configuradas e expõe lacunas; worker deve estar ativo |
| 7. Governança | Mostrar bloqueios de uma proposta pendente e fluxo com segundo responsável | O autor não aprova sua própria proposta; insumos alterados exigem nova conferência |
| 8. Automação | Executar uma rotina local autorizada e consultar histórico | Consumidor local opera sem n8n; n8n está bloqueado por auditoria e não deve ser iniciado |
| 9. Dados | Selecionar cenário/execução/projeção em Analytics e exportar | Fonte, grão, período, hashes e permissões acompanham o relatório; explicação gratuita funciona sem IA externa |
| 10. Evidência | Abrir relatório da Fase 9 e estudo de caso | Separar testes, microensaio, dados observados de teste e itens pendentes; não anunciar release de produção |

## Preparação verificável

- Criar contas de demonstração próprias, com papéis autorizados e senha privada. O segundo responsável precisa ser diferente do autor da execução.
- Garantir que backend, frontend e worker local estejam disponíveis. Habilitar apenas a rotina local que será mostrada; manter o scheduler opcional e integrações externas desativados.
- Preparar cenários pela aplicação/API e registrar as fontes das hipóteses. A fixture original contém dados pendentes; não é uma base juridicamente validada.
- Conferir estado real antes da apresentação. Se não houver proposta elegível para aprovação, mostrar o bloqueio e a evidência do teste integrado; não afirmar que uma aprovação ao vivo ocorreu.
- Guardar o arquivo exportado num diretório privado. Não projetar `.env`, ferramentas com cookies/tokens, logs privados ou contas reais.

## Limites de apresentação

Capturas ainda não foram produzidas. O [plano de screenshots](../release/screenshots.json) identifica telas/temas a verificar quando o acesso permitido a navegador estiver disponível. Não substituir essa pendência por imagens geradas, mockups ou renders de planilhas apresentados como interface real.

O microensaio do estudo de caso usa uma atividade e três/dois profissionais; não representa desempenho operacional dos 350 colaboradores. A árvore n8n tem avisos pendentes. Excel foi conferido; Power BI Desktop e QA visual de navegador continuam pendentes. A apresentação deve terminar com esses limites explícitos.
