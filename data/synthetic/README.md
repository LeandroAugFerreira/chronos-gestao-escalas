# Chronos 1.0 — Hospital Horizonte

Base totalmente sintética, seed 1042 e referência fixa 24/10/2026. O gerador é `backend/scripts/generate_demo.py`. Nomes intencionalmente artificiais; sem CPF, paciente, dado médico ou registro real de conselho. Valores de salário, jornadas, requisitos e habilitações são hipóteses, não dados normativos.

350 pessoas possuem lotação principal única em 19 setores; funções de enfermagem também existem nas áreas assistenciais. Uma organização e uma unidade são a escolha inicial de demonstração; o modelo aceita múltiplas unidades/segmentos. Os quantitativos por setor não comprovam suficiência nem mínimo legal.

`--check` verifica integridade e reprodução sem gravar. A geração sem `--check` regrava somente o caminho explícito da fixture, por padrão este JSON. A API lê o JSON e calcula totais; não há banco persistente nesta fase. Importação e restauração transacional da demonstração serão implementadas na Fase 2.

Plantões e demandas são templates ilustrativos, ainda sem calendário expandido nem avaliação de pausas/credenciais/regras. Contratos têm status `pending_review`. Credenciais `synthetic_only` não equivalem a habilitação real. O otimizador deverá construir intervalos e verificar elegibilidade; não consumir essas premissas como autorização automática de jornada.
