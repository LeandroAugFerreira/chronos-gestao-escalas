# Plano priorizado — Chronos para recrutadores

**Data:** 08/11/2026. **Foco:** melhorar verificabilidade sem alterar regras profissionais, ativar n8n ou publicar backend com credenciais de demonstração.

| Ordem | Entrega | Impacto | Esforço | Risco | Aceite |
| --- | --- | --- | --- | --- | --- |
| P0 | Teste que reconcilia benchmark e dados fictícios | Credibilidade | Baixo | Baixo | SHA, empate de cobertura/custo, lacuna e ausência de ROI verificados |
| P0 | Smoke navegador Chromium, SQLite efêmero e login real | Evidência visual do produto | Médio | Médio | CI verde e capturas com dados fictícios |
| P0 | Tour web para celular sem backend | Facilita triagem de recrutadores | Médio | Baixo | Dois cenários fiéis aos dados, aviso de simulação e botão de fonte |
| P0 | Preservar bloqueio n8n | Segurança | Baixo | Alto se desrespeitado | Nenhuma execução n8n no CI nem ativação da integração |
| P1 | Teste E2E de cenário, execução, verificação, submissão e segundo aprovador | Mostra regra principal | Alto | Médio | Logs com status e bloqueio de autoaprovação; fixture descartável |
| P1 | PostgreSQL efêmero no CI | Banco alvo de implantação | Médio | Médio | Migrações, permissões, integridade e rollback comprovados |
| P1 | QA de teclado, contraste, tema, responsividade e erros | Acessibilidade | Médio | Baixo/médio | Evidências reais em viewports diferentes |
| P1 | Revisão atualizada de dependências e configurações HTTP | Segurança | Médio | Médio | Varredura documentada sem suprimir bloqueios |
| P2 | Corrigir e reavaliar árvore n8n em ambiente separado | Futuras automações | Alto | Alto | Nenhum runtime ativado até auditoria satisfatória |
| P2 | Validar Power BI Desktop e DAX nativos | Empregabilidade Dados/BI | Médio/alto | Médio | PBIX real e refresh reproduzível |
| P2 | Endurecimento de operação, métricas e recuperação | Preparação à produção | Alto | Alto | Plano formal e teste de recuperação |
| P3 | Refatoração por domínio de arquivos extensos | Manutenção | Alto | Médio | Diffs pequenos com regressão e revisões |

## Exposição pública segura

A apresentação recomendada é um **tour estático** [chronos-demo.html](https://leandroaugferreira.github.io/chronos-demo.html) com dados do benchmark histórico e sem rede de escrita, JWT, contas ou API online. Ele não roda o solver. É útil para triagem, acompanhado do código e CI.

**Hospedar a API de verdade não está incluso**. Antes de expor: HTTPS e cookies Secure, autenticação de baixo privilégio, limitação de taxa, banco isolado, CORS, logging sanitizado, threat modeling, revisão de dependências, custos, proteção de dados, limpeza de estado entre sessões e homologação formal. Não copiar senha pública de demonstração para instância exposta.

## Política de divulgação

- Medições do histórico ficam associadas à sua fixture, seed, ambiente e data; não comparar tempo de máquinas sem controle.
- O caso de dois profissionais é **incompleto**; R$ 960 não é economia sobre escala completa de R$ 1.440.
- A marca OPTIMAL do diagnóstico não valida cobertura integral ou legislação.
- Explicar separadamente o smoke do navegador (login e telas) e pytest (solver).
- Não alegar teste de paciente, hospital real, trabalho humano, certificação jurídica ou IA generativa ativa para decidir jornada.

## Progresso implementado

A branch de recrutamento inclui teste de benchmark reproduzível e job de Chromium com banco temporário. A página web estática, quando publicada no portfólio, ficará no repositório do site, separada da API.

A integração à main deve ocorrer somente após CI e revisão do diff. Esta entrega não altera decisões do solver, regras trabalhistas nem automatizações existentes.

[Auditoria](AUDITORIA.md) · [Evidências](EVIDENCIAS.md) · [Arquitetura](ARQUITETURA.md).
