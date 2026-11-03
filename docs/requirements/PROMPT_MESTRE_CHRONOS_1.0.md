# PROMPT MESTRE — Chronos 1.0

## Chronos — Gestão Inteligente de Jornadas e Escalas

**Identificação: Chronos 1.0.** Atualização consolidada em 24/10/2026. Todos os requisitos não substituídos permanecem integrais. A Fase 1 é a tarefa atual; as demais fases são incrementais.

### 1. PAPEL E OBJETIVO

Atue como uma equipe sênior multidisciplinar composta por:

- Arquiteto de Software Full Stack.
- Desenvolvedor Python/FastAPI.
- Desenvolvedor React/TypeScript.
- Engenheiro de Dados.
- Especialista em Pesquisa Operacional e Otimização Matemática.
- Especialista em Automação de Processos com n8n.
- Analista de Processos e Melhoria Contínua.
- Especialista em Segurança da Informação e LGPD.
- Designer UX/UI.
- Engenheiro de Qualidade e Testes.

Sua missão é desenvolver uma aplicação web profissional, funcional e modular chamada **Chronos — Gestão Inteligente de Jornadas e Escalas**.

O projeto será utilizado como case de portfólio profissional, demonstrando capacidade de analisar um problema empresarial realista, planejar uma solução, programar algoritmos de otimização, automatizar processos, integrar sistemas, analisar dados e entregar software com qualidade de produção.

**Não construa apenas um CRUD ou um protótipo visual.**

A aplicação deverá executar processos reais sobre dados fictícios, persistir registros, calcular indicadores, gerar escalas, verificar restrições e demonstrar automações funcionando.

Todos os módulos deverão estar conectados de maneira coerente.

### 2. REGRAS FUNDAMENTAIS DE DESENVOLVIMENTO

1. Não modificar, apagar ou substituir outros projetos presentes no computador.
2. Criar o Chronos em diretório próprio, separado dos projetos existentes.
3. Antes de criar arquivos, verificar a estrutura do ambiente e apresentar o plano de implementação.
4. Não sobrescrever arquivos existentes sem antes verificar seu conteúdo.
5. Trabalhar de maneira incremental, mantendo a aplicação executável.
6. Utilizar Python no backend e React com TypeScript no frontend.
7. Adotar arquitetura modular, organizada e escalável.
8. Criar código legível, documentado e com comentários que expliquem regras de negócio importantes.
9. Não criar funcionalidades fictícias que aparentem estar funcionando.
10. Não apresentar testes como aprovados sem executá-los.
11. Utilizar exclusivamente dados sintéticos ou fictícios na demonstração.
12. Não realizar integrações externas que tenham custos ou efeitos reais sem autorização.
13. Não publicar o código no GitHub ou hospedar a aplicação sem aprovação.
14. Manter credenciais em variáveis de ambiente.
15. Criar um arquivo `.env.example`, sem segredos reais.
16. Priorizar tecnologias gratuitas ou open source.
17. Não exigir serviços de IA pagos para executar as funções principais.
18. Preservar os arquivos completos, evitando alterações desnecessárias de formatação.
19. Garantir que cada etapa tenha critérios verificáveis de conclusão.
20. Nunca confundir uma simulação de conformidade trabalhista com uma certificação jurídica.

Quando forem necessárias modificações, aplicar diretamente as alterações nos arquivos autorizados e apresentar um resumo com os arquivos modificados, testes realizados e pendências.

Se houver informações indispensáveis para uma decisão de arquitetura irreversível, explicar as alternativas; caso contrário, adotar uma opção tecnicamente sólida e documentar a escolha.

---

### 3. CONTEXTO EMPRESARIAL SIMULADO

**Empresa contratante:** Hospital Horizonte, instituição fictícia de médio porte.

**Cenário de demonstração:** uma unidade principal, 350 colaboradores sintéticos, operação hospitalar contínua 24 horas por dia, sete dias por semana. Setores assistenciais, administrativos e operacionais possuem horários, competências, jornadas e requisitos próprios.

**Setores:** Direção e gestão; Recursos Humanos; Financeiro e faturamento; Recepção e atendimento; Pronto-socorro; Unidade de Terapia Intensiva; Internação; Centro cirúrgico; Enfermagem; Farmácia hospitalar; Laboratório; Diagnóstico por imagem; Fisioterapia; Nutrição e cozinha; Higienização e limpeza; Lavanderia; Manutenção; Segurança; Logística e almoxarifado.

Cadastrar funções, qualificações e competências específicas com validade e evidência fictícia. A habilitação de uma função não autoriza automaticamente qualquer atividade de outra. Pessoas terão lotação principal única, contratos, disponibilidade e restrições próprias; equipes de apoio podem atuar em outros setores apenas quando elegíveis e autorizadas.

**Problema empresarial:** preparação manual de escalas, distribuição desigual de plantões/folgas, conflitos de descanso, falta de visibilidade de lacunas e custos, retrabalho e dificuldade de comparar alternativas. A cobertura deve considerar demanda por intervalo, atividade, competência e continuidade do atendimento, não apenas um total semanal de horas.

**Solicitação:** analisar a estrutura atual, simular jornadas, propor escalas, identificar impactos operacionais/financeiros, automatizar tarefas e permitir revisão e aprovação de gestores antes da adoção. Não assumir que as 350 pessoas sejam suficientes para toda demanda.

**Produto multissegmento:** Hospital Horizonte é o cenário principal, não a identidade do produto. Chronos deverá atender também clínicas, supermercados, indústrias, logística, hotéis, restaurantes, segurança, call centers, ensino e serviços. Setores, cargos, turnos e regras são dados configuráveis, sem dependência hospitalar no núcleo.

---

### 4. OBJETIVOS DO SISTEMA

O Chronos deverá:

1. Importar e cadastrar dados organizacionais.
2. Registrar colaboradores, departamentos e unidades.
3. Representar as jornadas atualmente utilizadas.
4. Simular mudanças de jornadas e escalas.
5. Calcular disponibilidade de horas.
6. Identificar necessidades operacionais por unidade.
7. Produzir escalas otimizadas automaticamente.
8. Verificar restrições trabalhistas configuradas.
9. Analisar o impacto financeiro das alternativas.
10. Comparar cenários.
11. Detectar conflitos e lacunas de cobertura.
12. Automatizar alertas e tarefas administrativas.
13. Disponibilizar indicadores gerenciais.
14. Preservar rastreabilidade e histórico das operações.
15. Disponibilizar um ambiente seguro de demonstração para recrutadores.

O principal resultado esperado é ajudar o gestor a tomar decisões fundamentadas em dados, sem substituir sua responsabilidade pelas decisões trabalhistas.

---

### 5. LEGISLAÇÃO E MOTOR DE REGRAS

Implementar um módulo específico chamado **LaborRules Engine**.

O objetivo é separar a legislação e as regras de jornada dos demais componentes do sistema.

#### 5.1 Referências normativas

Consultar e utilizar como base documental:

- Constituição Federal, artigo 7º.
- Emenda Constitucional nº 141/2026, promulgada em 16/10/2026.
- Consolidação das Leis do Trabalho (CLT).
- Disposições aplicáveis sobre jornada, intervalos, descanso, compensação e horas extraordinárias.
- Convenções e acordos coletivos, quando cadastrados.
- Normas específicas das categorias, quando pertinentes.

Fontes prioritárias:
- https://www.planalto.gov.br/
- https://www12.senado.leg.br/
- https://www.camara.leg.br/
- https://www.gov.br/trabalho-e-emprego/

Não depender de notícias ou modelos de linguagem como fonte única das regras legais.

#### 5.2 Marco normativo inicial

Implementar um conjunto versionado de regras, incluindo os marcos de transição da EC 141/2026:

- Contexto anterior: referência geral de jornada máxima de 44 horas semanais.
- Decorridos dois meses da publicação (data efetiva sujeita à revisão da contagem de vigência): referência geral de 42 horas semanais e dois dias de repouso remunerado por semana, observadas as regras específicas.
- Etapa posterior, 14 meses após a promulgação: referência geral de 40 horas semanais e dois dias de repouso.
- Manutenção salarial durante a redução de jornada, conforme disposições aplicáveis.
- Regimes excepcionais de compensação apenas quando houver fundamento normativo aplicável.
- Tratamento diferenciado de grupos expressamente previstos na legislação.

Validar os dispositivos exatos, a vigência e as exceções no texto oficial antes de codificar cada regra. O texto de origem mencionava 15/12/2026; registrar a divergência em relação ao prazo literal de dois meses da EC, sem ativar essa data automaticamente.

Não presumir que a mesma regra seja aplicável indistintamente a todos os trabalhadores.

#### 5.3 Regras configuráveis

O motor deverá permitir configurar:

- Início e fim da vigência de regras.
- Limite semanal de horas.
- Limites diários.
- Quantidade de dias de descanso.
- Intervalos intrajornada e interjornada.
- Restrições de trabalho aos domingos.
- Regras de feriados.
- Banco de horas.
- Horas extraordinárias.
- Categorias profissionais.
- Regras derivadas de acordos coletivos.
- Regimes especiais devidamente identificados.
- Exceções e justificativas documentadas.

Toda regra deverá registrar:

- Identificador.
- Descrição.
- Fonte normativa.
- Referência ao dispositivo.
- Data de vigência.
- Versão.
- Responsável pela configuração.
- Status de validação.
- Histórico de alterações.

O sistema não poderá alterar retroativamente escalas já aprovadas apenas porque uma regra foi atualizada.

Mudanças deverão gerar nova versão do cenário.

#### 5.4 Conformidade

Classificar os resultados como:

- Conforme com as regras configuradas.
- Não conforme com as regras configuradas.
- Pendente de validação jurídica.
- Não avaliado por ausência de regra aplicável.

Exibir claramente que a avaliação automatizada é uma ferramenta de apoio e não substitui a revisão jurídica ou trabalhista.

---

### 6. ARQUITETURA TECNOLÓGICA

#### Frontend

- React.
- TypeScript.
- Vite.
- React Router.
- Tailwind CSS.
- Componentes reutilizáveis.
- TanStack Query para comunicação com a API.
- React Hook Form e Zod.
- Biblioteca de gráficos Plotly ou Recharts.
- Calendário interativo de escalas.
- Interface responsiva.

#### Backend

- Python.
- FastAPI.
- Pydantic.
- SQLAlchemy.
- Alembic.
- PostgreSQL.
- Serviços organizados por domínio.
- API REST documentada.
- OpenAPI/Swagger.

#### Otimização

- Google OR-Tools com CP-SAT.
- Algoritmos determinísticos para cálculos básicos.
- Restrições rígidas e preferências ponderadas.
- Diagnóstico de inviabilidade.
- Registro dos parâmetros e resultados.

#### Automação

- n8n para integração e orquestração externa.
- APScheduler para tarefas locais simples.
- Worker separado para tarefas demoradas.
- Redis e fila de processamento quando justificado.

Evitar dependência obrigatória de n8n para funções fundamentais de cálculo e otimização.

#### Análise de dados

- pandas.
- NumPy.
- Plotly.
- Exportação CSV/XLSX.
- Dados preparados para consumo pelo Power BI.

#### Segurança

- Autenticação JWT.
- Hash seguro de senhas.
- Controle de acesso baseado em papéis (RBAC).
- Logs de auditoria.
- Segregação por organização.
- Validação de entradas.
- Proteção de endpoints.
- Política de retenção e exclusão de dados.
- Princípios de minimização e proteção de dados previstos na LGPD.

#### Infraestrutura

- Docker.
- Docker Compose.
- Configuração por `.env`.
- Testes automatizados.
- Git.
- GitHub Actions em etapa posterior.

---

### 7. ESTRUTURA DE DIRETÓRIOS

Planejar a organização inicial da seguinte maneira:

```text
Chronos/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── rules/
│   │   ├── optimization/
│   │   ├── automation/
│   │   ├── analytics/
│   │   ├── workers/
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── scripts/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   ├── utils/
│   │   └── styles/
│   └── package.json
│
├── automation/
│   └── n8n/
│
├── data/
│   ├── synthetic/
│   └── templates/
│
├── docs/
│   ├── requirements/
│   ├── architecture/
│   ├── business-process/
│   ├── database/
│   ├── api/
│   ├── legal-rules/
│   ├── testing/
│   └── portfolio-case/
│
├── scripts/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
└── CHANGELOG.md
```

A estrutura pode ser ajustada caso exista justificativa técnica documentada.

---

### 8. INTERFACE E IDENTIDADE VISUAL

Desenvolver uma interface corporativa moderna, inspirada em sistemas profissionais de planejamento operacional.

#### Identidade visual

Nome oficial: Chronos — Gestão Inteligente de Jornadas e Escalas.

Identificação de produto e entrega: Chronos 1.0. Identidade temporal abstrata e corporativa, sem nomes, ícones ou logotipos de produto exclusivamente hospitalar.

Estilo:
- Profissional.
- Tecnológico.
- Minimalista.
- Dashboard corporativo.
- Elementos visuais consistentes.
- Espaçamento equilibrado.
- Tipografia legível.

#### Temas

Disponibilizar:
- Dark Mode como tema inicial.
- Light Mode opcional.
- Preferência de tema persistida.

Paleta sugerida:
- Fundo escuro: azul-marinho profundo.
- Superfícies: grafite azulado.
- Destaques: azul e ciano.
- Sucesso: verde.
- Atenção: âmbar.
- Erros: vermelho moderado.

Utilizar cores sem comprometer acessibilidade.

#### Layout

Criar:

- Sidebar lateral.
- Cabeçalho superior.
- Breadcrumb.
- Cards de indicadores.
- Tabelas com paginação e filtros.
- Gráficos interativos.
- Formulários com validação.
- Modais de confirmação.
- Notificações.
- Indicadores de processamento.
- Layout responsivo para desktop, tablet e celular.

Todas as telas deverão utilizar padrões visuais consistentes.

---

### 9. MÓDULOS E TELAS DO SISTEMA

#### MÓDULO 01 — Dashboard Executivo

Criar a página inicial da plataforma.

Indicadores:

- Total de colaboradores.
- Total de unidades.
- Jornada semanal média.
- Distribuição das escalas.
- Quantidade de escalas pendentes.
- Cobertura operacional.
- Horas de trabalho disponíveis.
- Custo mensal estimado.
- Necessidade estimada de pessoal.
- Alertas de não conformidade.
- Automações executadas.

Gráficos:

- Distribuição por jornada.
- Cobertura semanal.
- Custo por unidade.
- Demanda de colaboradores por horário.
- Comparativo de cenários.
- Evolução das horas disponíveis.

Os indicadores deverão ser calculados a partir de dados reais do banco de demonstração, nunca por valores fixos no frontend.

#### MÓDULO 02 — Estrutura Organizacional

Gerenciar:

- Empresas.
- Unidades.
- Departamentos.
- Cargos.
- Centros de custo.
- Horários de funcionamento.
- Equipes.

Cada unidade poderá possuir necessidades operacionais específicas.

#### MÓDULO 03 — Colaboradores

Campos principais:

- Identificador interno.
- Nome fictício.
- Matrícula.
- Unidade.
- Departamento.
- Cargo.
- Jornada contratual.
- Salário-base fictício.
- Tipo de vínculo.
- Competências habilitadas.
- Disponibilidade.
- Restrições de trabalho.
- Preferências de folga.
- Status.

Implementar filtros, busca, importação e exportação.

Evitar coleta desnecessária de CPF, dados médicos ou informações sensíveis.

#### MÓDULO 04 — Jornadas e Escalas

Permitir visualizar e configurar:

- 6x1 como cenário histórico ou excepcional fundamentado.
- 5x2.
- 4x3 para simulação e regimes juridicamente admissíveis.
- 12x36, condicionada à validação contratual, normativa e dos descansos.
- Plantões de diferentes durações, diurnos e noturnos.
- Jornadas administrativas e regimes especiais com fundamento aplicável.
- Jornadas personalizadas.
- Turnos fixos.
- Turnos alternados.
- Escalas em revezamento.

Criar calendário mensal e semanal com:

- Nome dos colaboradores.
- Dias trabalhados.
- Horários de início e término.
- Intervalos.
- Folgas.
- Ausências registradas.
- Alertas de conflito.

Permitir ajustes manuais apenas a usuários autorizados.

Validar qualquer alteração contra as regras configuradas.

#### MÓDULO 05 — Simulador de Transição

Esta será uma das funcionalidades centrais do projeto.

O usuário deverá conseguir selecionar:

- Unidade.
- Departamento.
- Período.
- Escala atual.
- Escala pretendida.
- Limite de horas semanal.
- Demanda operacional.
- Quantidade de colaboradores.
- Restrições e acordos aplicáveis.

O sistema deverá produzir cenários independentes e comparáveis.

Exemplos:

Cenário A: organização atual de 44 horas como referência histórica.

Cenário B: planejamento para 42 horas.

Cenário C: planejamento para 40 horas.

Cenário D: jornada 4x3 simulada.

Cenário E: modelo personalizado.

Exibir:

- Horas disponíveis.
- Horas necessárias.
- Déficit ou excedente.
- Cobertura operacional.
- Colaboradores equivalentes.
- Custos estimados.
- Horários descobertos.
- Alertas de conformidade.
- Riscos operacionais.
- Comparação com cenário-base.

Não utilizar uma fórmula simplificada de divisão de horas como resultado definitivo de contratação.

O cálculo simplificado poderá existir como estimativa inicial, mas o dimensionamento principal deverá considerar a distribuição real da demanda, competências, descansos e disponibilidade.

#### MÓDULO 06 — Otimizador Inteligente de Escalas

Utilizar OR-Tools para gerar escalas automaticamente.

Entradas:

- Colaboradores disponíveis.
- Competências.
- Necessidade de pessoal por horário.
- Turnos possíveis.
- Jornada aplicável.
- Período de planejamento.
- Restrições trabalhistas.
- Preferências.
- Histórico de distribuição de folgas.
- Custos.

Restrições rígidas:

- Cobertura 24 horas conforme calendário e demanda do setor.
- Quantidade mínima por setor, atividade e intervalo, parametrizada com origem e revisão, sem inventar quantitativos mínimos universais.
- Habilitações válidas, matriz autorizada de substituições e indisponibilidade.
- Continuidade de atendimento e passagem de plantão quando obrigatórias.

- Jornada máxima aplicável.
- Descansos obrigatórios.
- Intervalos mínimos aplicáveis.
- Competência necessária para ocupar postos.
- Ausências e indisponibilidades.
- Limites de disponibilidade.
- Restrições contratuais.

Preferências ponderadas:

- Distribuição equilibrada de folgas.
- Menor número de lacunas de cobertura.
- Menor custo estimado.
- Continuidade operacional.
- Respeito às preferências informadas.
- Redução de trocas desnecessárias.

O algoritmo deverá:

1. Receber o cenário.
2. Construir o modelo matemático.
3. Executar a otimização.
4. Verificar a viabilidade.
5. Gerar uma escala proposta.
6. Exibir os indicadores.
7. Identificar restrições não atendidas, quando houver.
8. Registrar os resultados.
9. Enviar a proposta para aprovação.

Caso não exista solução viável, retornar explicações úteis e sugestões de alteração dos parâmetros.

Nunca simplesmente ignorar restrições legais para produzir uma escala. Separar modo estrito (cobertura obrigatória) de diagnóstico com lacunas explícitas, sem relaxar habilitações, descansos ou contratos; proposta incompleta não pode ser publicada. Distribuir plantões de forma equilibrada entre profissionais elegíveis.

Registrar tempo de execução, versão do algoritmo, parâmetros e status da otimização.

#### MÓDULO 07 — Impacto Financeiro

Criar simulador para:

- Custo atual.
- Custo projetado.
- Salários-base.
- Encargos estimados configuráveis.
- Benefícios.
- Horas extras projetadas.
- Adicionais configurados.
- Contratações adicionais.
- Custos de treinamento.
- Ganhos de produtividade simulados.
- Economia por redução de retrabalho administrativo.

Exibir valores e premissas separadamente.

Não inventar alíquotas legais nem assumir custos universais.

Permitir configurar encargos conforme o contexto da empresa e registrar a origem das premissas.

Criar comparativos mensais e anuais.

#### MÓDULO 08 — Automação de Processos

Criar central com automações administráveis.

Automações iniciais:

**A01 — Verificação de escalas**

Executa periodicamente a verificação de conflitos e mudanças de status.

**A02 — Monitoramento de cobertura**

Identifica horários com cobertura insuficiente e cria alertas.

**A03 — Avisos de aprovação**

Notifica gestores sobre escalas pendentes.

**A04 — Relatório operacional**

Gera resumo periódico de indicadores e disponibiliza arquivo para consulta.

**A05 — Monitoramento de vigência**

Identifica a proximidade de mudanças nas regras legais cadastradas e solicita revisão.

**A06 — Reotimização assistida**

Detecta alteração relevante na disponibilidade e propõe uma nova otimização, sem substituir a escala aprovada automaticamente.

**A07 — Auditoria de alterações**

Registra modificações relevantes em escalas, regras e permissões.

Cada automação deverá possuir:

- Identificador.
- Nome.
- Descrição.
- Evento disparador.
- Status.
- Última execução.
- Próxima execução.
- Histórico.
- Resultado.
- Mensagens de erro.
- Número de tentativas.
- Responsável.

#### MÓDULO 09 — Central de Aprovações

Implementar fluxo:

Rascunho → Em análise → Aprovado → Publicado.

Também permitir:

- Rejeitado.
- Cancelado.
- Substituído por nova versão.

Registrar:

- Solicitante.
- Responsável pela aprovação.
- Data.
- Justificativa.
- Versão.
- Diferenças entre propostas.

Não publicar escalas automaticamente em integrações externas.

#### MÓDULO 10 — Analytics e BI

Criar análises como:

- Jornada média.
- Cobertura por período.
- Utilização de horas.
- Distribuição de folgas.
- Custos por unidade.
- Demandas não atendidas.
- Eficiência de planejamento.
- Histórico de cenários.
- Tempo administrativo economizado.

Disponibilizar:

- Gráficos.
- Filtros por unidade.
- Filtros por período.
- Comparação de cenários.
- Exportação CSV/XLSX.
- Dataset preparado para Power BI.

#### MÓDULO 11 — LaborRules / Conformidade

Criar interface administrativa para:

- Consultar regras.
- Cadastrar regras de acordos coletivos.
- Visualizar vigência.
- Examinar conflitos.
- Identificar regras desatualizadas.
- Consultar referências normativas.
- Ver histórico de alterações.

Novas regras devem passar por revisão antes da ativação.

#### MÓDULO 12 — Administração e Auditoria

Criar:

- Usuários.
- Perfis e permissões.
- Configurações da empresa.
- Integrações.
- Histórico de execuções.
- Auditoria.
- Parâmetros do sistema.
- Configurações de notificações.
- Histórico de versões.

---

### 10. PERFIS DE ACESSO

Implementar inicialmente:

**Administrador:** gerencia usuários, empresas, integrações e configurações.

**RH:** administra jornadas, colaboradores, regras e simulações.

**Gestor:** consulta equipes, propõe escalas e aprova alterações permitidas.

**Financeiro:** consulta custos e relatórios financeiros, sem acesso desnecessário a informações pessoais.

**Analista:** consulta indicadores e executa simulações autorizadas.

**Demonstração:** navega em ambiente fictício com permissões limitadas.

Aplicar controle de acesso no backend, não apenas ocultando botões no frontend.

---

### 11. BANCO DE DADOS

Projetar modelo relacional normalizado.

Entidades mínimas:

- organizations
- units
- departments
- job_roles
- employees
- employee_skills
- availability_rules
- contracts
- shift_templates
- staffing_requirements
- work_schedules
- schedule_assignments
- schedule_versions
- optimization_scenarios
- optimization_runs
- financial_assumptions
- financial_scenarios
- labor_rules
- collective_agreements
- approvals
- automation_definitions
- automation_executions
- notifications
- audit_logs
- users
- roles
- permissions

Criar relacionamentos, chaves, índices, validações e migrations Alembic.

Entidades com informações empresariais deverão possuir isolamento por organização.

Priorizar integridade referencial e rastreabilidade.

---

### 12. API REST

Criar endpoints com versionamento `/api/v1`.

Grupos principais:

- `/auth`
- `/organizations`
- `/units`
- `/departments`
- `/employees`
- `/schedules`
- `/scenarios`
- `/optimization`
- `/financial`
- `/labor-rules`
- `/approvals`
- `/automations`
- `/analytics`
- `/notifications`
- `/audit`

Recursos essenciais:

- Validação com Pydantic.
- Erros padronizados.
- Paginação.
- Filtros.
- Ordenação.
- OpenAPI.
- Autorização por endpoint.
- Idempotência para operações críticas.
- Tratamento seguro de exceções.
- Identificadores de correlação para rastreamento.

Operações longas, como otimização matemática, deverão executar em segundo plano com acompanhamento de status.

---

### 13. INTELIGÊNCIA ARTIFICIAL

A IA será um módulo complementar e opcional.

Não utilizar IA generativa como mecanismo principal para calcular horas, validar normas ou gerar escalas.

Essas atividades deverão ser executadas por regras verificáveis e algoritmos determinísticos.

O módulo opcional poderá:

- Explicar diferenças entre cenários.
- Gerar resumos gerenciais.
- Traduzir resultados matemáticos em linguagem simples.
- Sugerir perguntas de análise.
- Explicar fatores que influenciam o custo.
- Auxiliar na interpretação de relatórios.

Implementar um serviço desacoplado que possa funcionar com:

1. Relatórios determinísticos gratuitos.
2. Modelo local, caso esteja disponível.
3. API externa opcional, habilitada explicitamente pelo administrador.

Não exigir Ollama instalado.

Não armazenar tokens ou chaves no frontend.

Não transmitir informações pessoais a modelos externos sem configuração apropriada e autorização.

Respostas de IA devem indicar quando forem interpretações ou sugestões, não conclusões legais.

---

### 14. AUTOMAÇÃO COM N8N

Criar workflows exportáveis para integração futura.

Fluxos inicialmente propostos:

**Workflow 1 — Nova escala pendente**

Evento → validar payload → localizar gestor → registrar notificação → aguardar aprovação.

**Workflow 2 — Alerta de cobertura**

Evento → analisar criticidade → verificar duplicidade → registrar alerta → comunicar responsável.

**Workflow 3 — Relatório programado**

Agendamento → consultar API → coletar indicadores → gerar relatório → armazenar arquivo → registrar execução.

**Workflow 4 — Alteração de disponibilidade**

Webhook → validar evento → atualizar registro → identificar escalas impactadas → solicitar reotimização.

Requisitos:

- Webhooks autenticados.
- Retentativas controladas.
- Prevenção de execuções duplicadas.
- Histórico.
- Tratamento de falhas.
- Desativação segura.
- Exportação JSON dos workflows.
- Documentação de configuração.

O sistema deverá funcionar mesmo quando o n8n não estiver instalado, mantendo as funções principais operacionais.

---

### 15. DADOS FICTÍCIOS E AMBIENTE DE DEMONSTRAÇÃO

Criar um conjunto consistente de dados sintéticos.

Cenário inicial:

- Hospital Horizonte.
- Uma unidade principal de demonstração, com arquitetura preparada para múltiplas unidades.
- 350 colaboradores fictícios, distribuídos nos 19 setores definidos.
- Setores assistenciais, administrativos e operacionais com necessidades próprias.
- Cargos compatíveis com as atividades.
- Diferentes turnos.
- Diferentes jornadas.
- Demandas por horário.
- Restrições de disponibilidade.
- Salários e custos simulados.
- Histórico fictício de escalas.

Os dados deverão ser gerados por script reproduzível.

Utilizar uma seed fixa quando necessário.

Disponibilizar um comando para restaurar o banco de demonstração.

Incluir situações específicas de teste:

1. Escala viável sem conflitos.
2. Escala com cobertura insuficiente.
3. Funcionário indisponível.
4. Conflito de descanso.
5. Limite semanal excedido.
6. Necessidade de contratação adicional.
7. Demanda de fim de semana.
8. Aumento de movimento em feriados.
9. Cenário de 42 horas.
10. Cenário de 40 horas.
11. Cenário 4x3 hipotético.
12. Mudança de regra por data de vigência.
13. Falha de integração externa.
14. Reprocessamento após erro.
15. Tentativa de acesso não autorizado.

Todos os números exibidos no dashboard devem corresponder aos dados gerados.

---

### 16. TESTES E QUALIDADE

Criar testes automatizados para:

**Backend:**
- Regras de negócio.
- Cálculos de horas.
- Datas de vigência.
- Descansos.
- Validação de jornadas.
- Custos.
- API.
- Autorização.
- Persistência.

**Otimização:**
- Solução viável.
- Solução inviável.
- Restrições rígidas.
- Preferências.
- Cobertura.
- Cenários com múltiplas unidades.
- Reprodutibilidade.

**Frontend:**
- Formulários.
- Navegação.
- Filtros.
- Calendário.
- Simulações.
- Aprovações.
- Erros de rede.
- Responsividade.

**Integração:**
- Banco.
- API.
- Frontend.
- Execução de tarefas.
- Workflows.
- Recuperação após falhas.

Criar testes de ponta a ponta para o fluxo principal:

Login → carregar empresa → consultar escala atual → criar cenário → executar otimização → analisar resultados → solicitar aprovação → aprovar → publicar cenário fictício → consultar dashboard.

Validar o fluxo com testes automatizados e, quando disponível, navegação real no navegador.

Não declarar funcionalidades concluídas com base somente na existência de arquivos ou componentes.

---

### 17. SEGURANÇA E PRIVACIDADE

Implementar:

- Hash seguro de senhas.
- Proteção contra acesso entre organizações.
- Controle de permissões.
- Validação de uploads.
- Limites de tamanho de arquivo.
- Proteção contra entradas maliciosas.
- Auditoria de mudanças.
- Tratamento de erros sem vazamento de segredos.
- Política de retenção de logs.
- Proteção de dados pessoais.
- Configuração segura de CORS.
- Gestão de segredos por ambiente.
- Rate limiting nos endpoints sensíveis.

Não incluir dados reais de funcionários no repositório.

---

### 18. DOCUMENTAÇÃO PROFISSIONAL

Produzir:

**README.md**
- Apresentação.
- Problema empresarial.
- Objetivos.
- Principais funcionalidades.
- Tecnologias.
- Arquitetura.
- Instalação.
- Configuração.
- Inicialização.
- Testes.
- Demonstração.
- Limitações.

**Documentação técnica**
- Arquitetura.
- Modelo entidade-relacionamento.
- API.
- Motor de regras.
- Modelo de otimização.
- Processos automatizados.
- Segurança.
- Procedimentos de manutenção.

**Estudo de caso para portfólio**
- Cliente fictício.
- Problema inicial.
- Diagnóstico.
- Processo anterior.
- Processo automatizado.
- Solução desenvolvida.
- Decisões técnicas.
- Resultados de testes.
- Comparação antes/depois.
- Limitações.
- Evoluções futuras.

Identificar explicitamente que o cliente e os indicadores são simulados.

---

### 19. INDICADORES PARA O PORTFÓLIO

Medir de maneira reproduzível:

- Tempo para gerar uma escala.
- Tempo de execução do algoritmo.
- Quantidade de conflitos identificados.
- Percentual de demanda coberta.
- Número de escalas viáveis.
- Custo estimado dos cenários.
- Quantidade de intervenções humanas.
- Taxa de sucesso das automações.
- Tempo de processamento de arquivos.
- Quantidade de verificações de regras executadas.

Criar comparação entre planejamento manual simulado e automatizado, informando claramente a metodologia utilizada.

Não inventar ganhos de produtividade como resultados efetivamente medidos.

---

### 20. PLANO DE DESENVOLVIMENTO

Executar o trabalho por fases.

**FASE 1 — Planejamento e arquitetura**
- Inspecionar ambiente.
- Definir estrutura.
- Documentar requisitos.
- Criar arquitetura.
- Modelar banco.
- Documentar regras iniciais.
- Definir critérios de aceite.

**FASE 2 — Backend e persistência**
- Inicializar FastAPI.
- Configurar PostgreSQL.
- Criar migrations.
- Criar autenticação.
- Implementar entidades principais.
- Criar endpoints.
- Criar dados fictícios.

**FASE 3 — Frontend**
- Implementar identidade visual.
- Criar layout.
- Implementar navegação.
- Conectar telas à API.
- Criar dashboard.
- Criar gestão de colaboradores e unidades.

**FASE 4 — Jornadas e motor de regras**
- Implementar modelos de jornada.
- Implementar regras versionadas.
- Criar validações.
- Criar calendário.
- Criar alertas de conformidade.

**FASE 5 — Simulador**
- Implementar cenários.
- Calcular capacidade.
- Comparar jornadas.
- Calcular custos.
- Exibir resultados.

**FASE 6 — Otimização**
- Implementar modelo OR-Tools.
- Aplicar restrições.
- Gerar propostas.
- Identificar inviabilidade.
- Implementar fluxo de aprovação.

**FASE 7 — Automações**
- Implementar scheduler.
- Criar notificações.
- Criar histórico de execuções.
- Preparar workflows n8n.
- Testar falhas e retentativas.

**FASE 8 — Analytics e IA**
- Criar indicadores.
- Gerar relatórios.
- Preparar exportação Power BI.
- Implementar IA explicativa opcional.

**FASE 9 — Segurança e testes**
- Auditar permissões.
- Validar cálculos.
- Executar testes automatizados.
- Testar interface.
- Corrigir problemas encontrados.

**FASE 10 — Portfólio**
- Finalizar documentação.
- Preparar screenshots.
- Criar roteiro de demonstração.
- Produzir estudo de caso.
- Preparar release 1.0.
- Solicitar aprovação antes de publicar.

Não iniciar todas as fases simultaneamente.

Manter checkpoints funcionais e registrar o progresso.

---

### 21. CRITÉRIOS MÍNIMOS DE ACEITE

O sistema só poderá ser considerado funcional quando:

- O frontend iniciar corretamente.
- O backend iniciar corretamente.
- O banco persistir os dados.
- O login funcionar.
- As permissões forem aplicadas.
- Os dados fictícios puderem ser carregados.
- O dashboard consultar dados reais da API.
- As jornadas puderem ser cadastradas e consultadas.
- O simulador comparar cenários.
- Os cálculos forem testados.
- O otimizador produzir pelo menos uma escala válida.
- O sistema identificar cenários inviáveis.
- O motor de regras aplicar as vigências cadastradas.
- A aprovação registrar a decisão.
- Pelo menos uma automação executar efetivamente.
- Os logs registrarem as operações.
- Os relatórios puderem ser exportados.
- O fluxo principal funcionar de ponta a ponta.
- A documentação de execução estiver correta.

Nenhuma funcionalidade deve ser marcada como concluída caso esteja apenas representada visualmente.

---

### 22. PREPARAÇÃO PARA EXECUÇÃO NO WINDOWS

O desenvolvimento será realizado inicialmente em ambiente Windows, utilizando VS Code e terminal PowerShell.

Considerar que a máquina poderá possuir recursos limitados.

Portanto:

- Evitar serviços desnecessários.
- Não instalar modelos de IA pesados automaticamente.
- Minimizar uso de memória.
- Evitar múltiplos processos redundantes.
- Não instalar dependências globalmente quando puder utilizar ambiente virtual.
- Não armazenar ambientes virtuais, caches ou bancos ativos em pastas sincronizadas pelo OneDrive quando isso prejudicar desempenho.
- Fornecer comandos compatíveis com PowerShell.
- Documentar instalação e configuração do Docker.
- Oferecer modo de desenvolvimento leve quando o Docker completo não estiver disponível.
- Permitir uso temporário de SQLite no desenvolvimento local, desde que as diferenças para PostgreSQL sejam documentadas e testadas.

Preparar scripts de inicialização para simplificar o processo.

---

### 23. EXPERIÊNCIA FINAL ESPERADA

Ao abrir o Chronos, o usuário deverá visualizar uma aplicação profissional, contendo:

1. Tela de login.
2. Dashboard executivo.
3. Cadastro de estrutura organizacional.
4. Cadastro de colaboradores.
5. Calendário de escalas.
6. Simulador de transição.
7. Otimizador de escalas.
8. Análise financeira.
9. Central de automações.
10. Central de aprovações.
11. Analytics e BI.
12. Regras trabalhistas.
13. Administração.

O usuário deverá conseguir selecionar uma unidade e jornada contratual cadastradas (6x1 apenas como referência histórica ou exceção fundamentada), criar um cenário alternativo, executar uma otimização, comparar resultados, verificar restrições e aprovar uma nova proposta.

Tudo isso deverá ocorrer sem necessidade de alterar manualmente o banco de dados ou executar scripts avulsos para cada ação.

---

### 24. RESULTADO FINAL E ENTREGA

Ao concluir cada fase, apresentar:

- Funcionalidades implementadas.
- Arquivos criados ou modificados.
- Testes executados e resultados.
- Erros conhecidos.
- Decisões técnicas.
- Comandos para executar.
- Próxima fase recomendada.

Ao concluir a versão inicial, preparar:

- Aplicação executável em ambiente local.
- Backend funcional.
- Frontend funcional.
- Banco de demonstração.
- Documentação.
- Testes.
- Relatório de validação.
- Materiais de portfólio.
- Release 1.0 preparada para revisão.

Não realizar publicação pública, deploy ou mudanças em outros repositórios sem aprovação explícita.

---

### 25. PRIMEIRA TAREFA A EXECUTAR

Inicie pela **FASE 1 — Planejamento e Arquitetura**.

Execute as seguintes atividades:

1. Inspecione o diretório de trabalho disponível.
2. Verifique as versões de Python, Node.js, Git e ferramentas necessárias.
3. Determine a melhor configuração de desenvolvimento considerando Windows e recursos disponíveis.
4. Defina a arquitetura inicial.
5. Crie a estrutura de diretórios do Chronos em uma pasta isolada.
6. Documente os requisitos funcionais e não funcionais.
7. Elabore o modelo inicial do banco de dados.
8. Defina o funcionamento do LaborRules Engine.
9. Especifique o algoritmo de otimização.
10. Crie um cronograma de implementação por fases.
11. Prepare uma primeira execução mínima do backend e frontend, caso o ambiente permita.
12. Execute as validações iniciais.
13. Apresente um relatório claro do que foi efetivamente criado e testado.

Após finalizar essa etapa, apresente o plano de implementação da FASE 2.

**Objetivo principal: entregar uma plataforma corporativa que demonstre capacidade real de automatizar a transição de jornadas de trabalho, combinando programação Full Stack, análise de dados, otimização matemática, automação de processos e governança.**

**INICIE O DESENVOLVIMENTO DO Chronos 1.0.**

---

### 26. CONTROLE DE ESCOPO DA ATUALIZAÇÃO CHRONOS 1.0

- Todos os documentos, telas, títulos, metadados e arquivos de release identificam Chronos 1.0.
- A arquitetura é corporativa e configurável para diferentes segmentos; Hospital Horizonte é apenas o cenário fictício principal, com 350 colaboradores e operação 24 horas.
- Escalas 5x2, 4x3, 12x36, plantões, turnos diurnos/noturnos, jornadas administrativas, regimes especiais e personalizados são configurações/simulações; nenhuma modalidade é presumida válida para todo cargo.
- Dimensionamento depende da atividade, competências, habilitações, fonte normativa profissional e condições aplicáveis; parâmetros sintéticos não são mínimos universais.
- Preservar desenvolvimento por fases, testes automatizados, n8n, simulador financeiro, OR-Tools, dashboard, LaborRules e todos os módulos descritos.
- Não modificar outros projetos nem publicar sem autorização.
- Executar agora somente a Fase 1, incluindo o checkpoint mínimo de backend/frontend se o ambiente permitir, e apresentar o plano concreto da Fase 2.
