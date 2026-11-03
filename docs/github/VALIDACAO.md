# Validação da cópia fonte — 02/11/2026

Backend/checagens existentes: **182 aprovados, 1 ignorado**.

Frontend: test: aprovado; build: aprovado.

O caso test_postgresql_profile_was_executed foi ignorado porque não havia CHRONOS_TEST_POSTGRES_URL em banco descartável *_test. Não houve homologação PostgreSQL nesta rodada. Testes de interface: 88 aprovados em 10 arquivos; build aprovado.

Os testes Python usaram ambientes já instalados, com segredos de ambiente removidos e arquivos temporários confinados à pasta de trabalho. O processo principal bloqueou DNS/conexões externas; conexões de loopback e subprocessos existentes foram revisados. Não foram iniciados n8n, envio SMTP real, conexão pessoal de IA ou transmissão fiscal. As simulações e documentos produzidos pelos testes são fictícios e não acompanham o pacote fonte.

Os testes inicialmente executados no sandbox não concluíram a inicialização; a execução isolada com acesso local adequado resolveu esse bloqueio de ambiente. Duas execuções completas pararam no limite inicial de cinco minutos, sem serem contabilizadas como aprovação. Os resultados acima usam as execuções concluídas e o reteste explicitado.

Dependências Python não foram instaladas ou adicionadas. Os builds reutilizaram dependências locais copiadas; para Chronos, o frontend foi restaurado em diretório novo pelo mesmo lockfile, sem scripts de instalação. Nenhum manifest da aplicação foi alterado. Os avisos de depreciação do adaptador de TestClient e o aviso de tamanho de chunk no build Chronos não foram tratados como novas funcionalidades ou como testes reprovados; não houve troca de dependências para suprimi-los.

Não houve instalação completa do backend a partir de ambiente vazio, teste de produção, novo build de EXE ou implantação. Os comandos do README foram conferidos no código, incluindo o preenchimento local de campos secretos deixados vazios nos exemplos. Este documento registra os testes locais; as execuções remotas são consultáveis na página de Actions do repositório.

As evidências estruturadas nesta pasta registram resultados reais. Os originais e os arquivos de lógica da aplicação foram preservados; somente documentação, exemplos sem credenciais e configuração de CI diferem na cópia.
