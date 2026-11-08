# Entrevista técnica — 15 perguntas e respostas fundamentadas no Chronos

Respostas baseadas no código. O autor deve confirmar o que fez pessoalmente e estudar para conseguir explicar e modificar as funções sem depender de respostas decoradas.

## 1. Que problema o Chronos aborda?
Conecta demandas, contratos, jornadas, competências e custos hipotéticos em cenários versionados de planejamento. Otimização sugere alternativas, não certifica regras jurídicas. [Estudo de caso](ESTUDO_DE_CASO.md).

## 2. Como a aplicação está dividida?
Frontend React/TypeScript/Vite, cliente HTTP, API FastAPI/Pydantic, SQLAlchemy/Alembic, banco PostgreSQL alvo e SQLite local opcional, worker OR-Tools CP-SAT. [Arquitetura](ARQUITETURA.md).

## 3. Por que PostgreSQL e SQLite?
PostgreSQL é alvo de implantação; SQLite só funciona com habilitação explícita em desenvolvimento/teste, fora de projeto/OneDrive, e é proibido em produção. [database.py](../../backend/app/core/database.py).

## 4. O que é CP-SAT?
Solver do OR-Tools de programação por restrições, com variáveis inteiras/booleanas, regras hard/soft, objetivos e verificação posterior. [optimizer.py](../../backend/app/services/optimizer.py). **Estudar:** modelagem e resultados inviáveis.

## 5. Como o sistema trata a falta de equipe?
Registra cobertura parcial e lacuna; OPTIMAL no diagnóstico não elimina demanda descoberta. Premissas e lacunas podem bloquear aprovação. [optimizer.py](../../backend/app/services/optimizer.py).

## 6. Por que há verificador independente?
Para checar soluções após o solver (elegibilidade, sobreposição, descanso e cobertura), evitando aceitar somente o status do algoritmo. [check_solution](../../backend/app/services/optimizer.py).

## 7. Por que snapshots e digests?
Vinculam propostas a entradas e versões específicas; alteração das premissas ou conteúdo divergente bloqueia aprovação. [optimization_snapshot.py](../../backend/app/services/optimization_snapshot.py).

## 8. Pode aprovar a própria proposta?
Não. A rota de decisão impede aprovação pela mesma pessoa que criou a execução e valida estados, perfis e digest. [optimization.py](../../backend/app/api/optimization.py).

## 9. Como funciona autorização?
Papéis, permissões e escopo por unidade/organização, conferidos a cada requisição. Permissão numa área não amplia outras. [dependencies.py](../../backend/app/api/dependencies.py), [security.py](../../backend/app/core/security.py).

## 10. Como a sessão web protege credenciais?
Senha Argon2id; access JWT em memória, refresh HttpOnly, CSRF assinado e origem permitida. [browser_session.py](../../backend/app/api/browser_session.py), [client.ts](../../frontend/src/services/client.ts). **Estudar:** XSS, CSRF, cookie Secure e expiração.

## 11. O que torna uma gravação idempotente?
Identificador de requisição, comparação de entrada e persistência/retorno estável evitam efeitos repetidos, conforme implementação de domínio. [idempotency.py](../../backend/app/services/idempotency.py).

## 12. O que é uma simulação financeira?
Projeção sob hipóteses configuradas, em centavos/Decimal; não gasto observado nem economia de cliente real. [financial.py](../../backend/app/services/financial.py).

## 13. O solver foi melhor que first-fit?
Não no microensaio publicado. Com 3 fictícios ambos cobriram 1.440; com 2, ambos cobriram 960 e deixaram 480 sem cobertura, com custo hipotético igual em cada cenário. [benchmark.json](../portfolio/benchmark.json).

## 14. Quais testes foram executados?
Nesta revisão: 184 pytest aprovados, 1 ignorado, 88 Vitest aprovados, build e browser Chromium (login/dashboard/otimização). Consultar [EVIDENCIAS.md](EVIDENCIAS.md) e o CI do mesmo commit. **Estudar:** diferenciação entre unitários, integração, E2E e execução histórica.

## 15. O que não pode ser publicado como produto pronto?
n8n bloqueado; backend sem implantação pública homologada; falta PostgreSQL recente, testes completos de interface, conformidade legal e revisão de segurança/infraestrutura. Não prometer escala clínica ou trabalhista certificada. [Plano](PLANO_DE_MELHORIAS.md).

---

## Exercício para entrevista

Desenhe snapshot → solver → verificador → proposta → outro aprovador. Explique o cenário de dois profissionais sem vender a cobertura parcial como economia. Mostre a fixture e o CI. Descreva com transparência o uso de IA/Codex, as decisões que verificou e o que precisa aprender.

**Não alegar:** hospital cliente, impacto produtivo medido, n8n em execução, Power BI nativo concluído ou conformidade universal.
