# Chronos 1.0 — Backup e recuperação

Backups contêm dados, hashes de senha, sessões e chaves de serviço armazenadas pelo sistema. Guarde-os fora do projeto/OneDrive, em pasta privada, com proteção de acesso e criptografia do armazenamento conforme a operação. SHA-256 verifica integridade do arquivo; não autentica sua procedência. Não publique os arquivos de banco ou manifests operacionais.

## SQLite local

O comando usa a API de backup SQLite, que gera uma cópia consistente sem copiar de forma ingênua um arquivo ativo. Faz leitura da origem, confere integridade/FKs/schema e grava manifest com hash e contagens. Os schemas 009 e 010 são reconhecidos; a aplicação da Fase 9 exige head 010_pattern_revision.

```powershell
& $pythonPath .\backend\scripts\recovery.py backup --source "$env:CHRONOS_RUNTIME_DIR\chronos.sqlite3" --directory "$env:CHRONOS_RUNTIME_DIR\backups"
& $pythonPath .\backend\scripts\recovery.py restore --backup 'CAMINHO_DO_BACKUP.sqlite3' --manifest 'CAMINHO_DO_MANIFEST.json' --directory "$env:CHRONOS_RUNTIME_DIR\recuperacao-nova" --confirm-isolated-restore
```

A pasta de destino da restauração **não pode existir**. Não há opção de sobrescrever o banco principal. O original e o backup permanecem intactos. Hash/schema/contagens divergentes interrompem a operação antes de criar o destino.

Na cópia restaurada, sessões são revogadas, credenciais de serviço e rotinas ativas são desabilitadas, jobs/outbox/entregas queued/running são cancelados e execuções interrompidas são marcadas failed. Uma auditoria registra a recuperação. Aprovações históricas, pessoas, contratos, cálculos e digests de cenário permanecem armazenados; cancelar efeitos pendentes não significa rejeitar decisões históricas.

Antes de servir a cópia, confira integridade/contagens, migre a cópia ao head atual se necessário, escolha um segredo JWT novo, faça login novamente e revise chaves/rotinas/cálculos. Nunca reative efeitos pendentes por simples restauração. A troca do banco operacional é uma ação separada, com serviços parados e revisão explícita; este comando não a realiza.

## PostgreSQL

Em produção, use `pg_dump`/`pg_restore` compatíveis com o servidor, armazenamento protegido e credenciais fora da linha de comando. Restaure primeiro num **banco novo e isolado**, nunca com `--clean` sobre o banco operacional. Use `--single-transaction --exit-on-error --no-owner --no-acl`, aplique a política de suspensão de efeitos na cópia e confira schema/contagens/digests antes de considerar qualquer troca operacional.

O teste nativo usa uma base com nome `chronos_recovery_<id>_test`, restaura o schema de teste, revoga sessões/chaves e suspende efeitos na cópia, confere as fontes e elimina apenas essa base descartável no finally. A base de origem e o banco principal não são restaurados ou apagados. Credencial efêmera fica somente no ambiente dos processos de teste; não aparece no argv ou nas evidências públicas.

O perfil `scripts/test-portable-postgres.ps1` configura `CHRONOS_PG_BIN` para os binários portáteis. Num PostgreSQL externo, configure esse caminho ou disponibilize `pg_dump`/`pg_restore` no PATH. Sem essas ferramentas, o caso nativo é explicitamente skipped e não conta como recuperação PostgreSQL validada.

## Operação de produção ainda não liberada

Servir frontend/API por HTTPS e origem explícita; usar proxy com limites coerentes de corpo/tempo e cabeçalhos de segurança também nos arquivos estáticos. Os cabeçalhos adicionados pela API não configuram automaticamente o servidor estático. Manter Postgres privado e autenticação dos operadores, revisar segredos/rotação, backups e restauração periódica. Nenhum proxy, certificado, publicação, gateway Power BI ou operação cloud foi configurado nesta fase.
