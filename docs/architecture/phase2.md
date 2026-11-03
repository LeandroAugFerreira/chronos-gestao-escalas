# Chronos 1.0 — Backend e persistência (Fase 2)

## Implementação

Configuração Pydantic Settings por ambiente e `.env` ignorado pelo Git. SQLAlchemy 2 com PostgreSQL/psycopg e perfil SQLite opt-in. Quatro migrations Alembic congeladas criam 23 tabelas: identidade/RBAC, estrutura/catálogos, pessoas/contratos/disponibilidade e idempotência. O servidor nunca usa `create_all` nem migra silenciosamente ao iniciar.

Organizações são provisionadas administrativamente, não por cadastro público. O CLI importa Hospital Horizonte e cria o primeiro administrador com senha escolhida no terminal. API permite consultar a organização autenticada; não existe usuário global que navegue livremente entre empresas. Catálogos de papéis/permissões são globais, sem endpoint público de alteração.

As referências empresariais usam `organization_id` e FKs compostas; a relação pessoa → setor inclui também `unit_id`. Repositórios resolvem o tenant pelo usuário autenticado. Permissões carregadas do banco possuem escopo próprio por unidade: um papel com leitura agregada global não amplia a leitura de pessoas de outro papel. O papel admin limitado a unidade não pode criar usuários ou unidades globais.

Cadastros implementados: unidades, setores, funções, competências, qualificações, colaboradores, contratos, habilidades, habilitações e disponibilidade. Jornadas são importadas como catálogo pendente de revisão; configuração executável de jornadas e regras continua na Fase 4. Edição de colaborador nesta fase altera nome/status com revisão otimista. Não há exclusão pública de pessoas, edição de organização/unidade/setor ou transferência de lotação nesta entrega; as telas e operações adicionais são incrementos da Fase 3.

## Autenticação e autorização

Argon2id para senhas; JWT HS256 com algoritmo fixo, emissor/audiência, tipo, organização, sessão, emissão/validade e identificador. Sem segredo de reserva: falta de configuração retorna 503; produção exige banco e segredo. Senhas possuem 12–128 caracteres no provisionamento e nunca são retornadas pela API.

Access token dura 15 minutos por padrão; refresh opaco dura sete dias e apenas seu hash é persistido. Refresh é rotacionado em transação. Reutilização revoga toda a família e invalida inclusive tokens de acesso associados. Logout também revoga a família imediatamente. Cada requisição confirma usuário ativo, sessão não revogada e permissões atuais no banco. Isso prioriza revogação imediata sobre autenticação totalmente sem estado.

Limite de login persistido por conta e IP, com HMAC dos identificadores, incremento atômico e janela configurável. Não confiar em `X-Forwarded-For` enviado pelo cliente. O perfil de produção deverá definir proxy confiável e TLS antes de exposição; a execução entregue usa apenas loopback.

Tokens são retornados pela API para uso por clientes autorizados e Swagger. A interface existente conserva a leitura pública de fixture; login visual será Fase 3. O frontend futuro deverá manter acesso em memória e definir refresh em cookie HttpOnly com proteção CSRF ou BFF, sem localStorage para credenciais.

| Perfil | Capacidades desta fase |
|---|---|
| admin | Estrutura, pessoas, custos de contrato, catálogos, usuários e auditoria, conforme escopo |
| hr | Leitura de estrutura; pessoas, contratos e catálogos |
| manager | Leitura de estrutura, pessoas e catálogos; sem salário ou escrita |
| finance | Estrutura/catálogos e valores contratuais; sem lista de pessoas |
| analyst | Estrutura/catálogos e quantidade de pessoas agregada; sem dados individuais |
| demo | Estrutura/catálogos e quantidade agregada; sem dados individuais |

## Transações e rastreabilidade

Criação de cadastro e auditoria confirmam na mesma transação. Conflito de integridade faz rollback e retorna 409. Atualização de pessoa exige `revision`; comparação atômica evita sobrescrever edição concorrente. Datas de contratos/habilitações são validadas, contrato sobreposto é bloqueado e indisponibilidade exige instantes com fuso. Esses controles de integridade não constituem avaliação trabalhista.

POSTs de cadastro aceitam `Idempotency-Key` opaca. A chave é isolada por tenant/ator/rota e armazenada como HMAC junto ao HMAC do conteúdo, sem senha ou payload integral. Repetição devolve o recurso existente, sem duplicar criação/auditoria; conteúdo divergente retorna 409. A resposta de replay mostra a representação atual do recurso, não um snapshot da resposta antiga. Chamadas concorrentes têm uma única transação vencedora e podem exigir retry após 409. PATCH usa revisão otimista; refresh tem consumo único próprio.

Erros de validação não incluem o valor de entrada, evitando eco de senha. Erros SQL não expõem instruções, credenciais ou paths. `X-Correlation-ID` gerado pelo servidor liga resposta e auditoria; tokens e senhas não entram nos logs de auditoria. CORS allowlist é explícita; respostas de API usam `Cache-Control: no-store`.

## Demonstração e restauração

UUIDs determinísticos mapeiam a fixture para persistência normalizada. Importação transacional: 350 pessoas, 19 setores, 38 funções, competências, qualificações, contratos e disponibilidade. Repetir a mesma fixture preserva alterações manuais e não duplica; fixture diferente exige revisão/restauração explícita.

`restore-demo --confirm 'Hospital Horizonte'` aceita somente desenvolvimento/teste, ID/slug esperados e `is_demo=true`. Restaura pessoas e catálogos fictícios em transação, preservando usuários, permissões, sessões, unidades e auditoria. A unidade principal recupera seus atributos da fixture. Unidades adicionais e seus escopos permanecem. Não restaura regras/escala/otimizador, ainda não implementados.

O JSON público `/demo/summary` continua independente do banco para preservar o frontend da Fase 1. `/analytics/workforce` consulta a persistência e aplica o escopo do usuário. Não confundir esses dois resultados após alterações no banco; o dashboard conectado ao banco será implementado na Fase 3.

## Referências de implementação

- [SQLAlchemy: chaves e constraints](https://docs.sqlalchemy.org/en/20/core/constraints.html).
- [Alembic: particularidades SQLite](https://alembic.sqlalchemy.org/en/latest/batch.html).
- [OWASP: armazenamento de senhas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
- [PyJWT: validação de tokens](https://pyjwt.readthedocs.io/en/latest/api.html).

RLS PostgreSQL, retenção automática, recovery operacional e auditoria de segurança completa seguem no endurecimento da Fase 9; não são alegados como implantados por existir isolamento na aplicação/FKs.
