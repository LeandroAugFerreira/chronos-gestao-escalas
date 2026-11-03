"""Produce a public manual without workstation paths or personal account details."""
from pathlib import Path
import importlib.util
import os
import re

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = ROOT.parent/'portfolio'
WORK = Path(os.environ['CHRONOS_RUNTIME_DIR'])/'portfolio-2026-10-27/manual'

intro = '''# Chronos 1.0

Manual de instruções - edição para portfólio

Gestão Inteligente de Jornadas e Escalas

Edição de 27/10/2026. Cenário fictício: Hospital Horizonte.

## 1. Conheça a plataforma e os acessos

Este manual apresenta os módulos do Chronos e a execução local do projeto. A página do portfólio exibe a apresentação e a documentação; ela não hospeda uma API pública ou um ambiente online de login.

Na instalação local, abra **http://127.0.0.1:5187**. O administrador é criado pelo operador durante o setup, com usuário e senha escolhidos por ele. Não há conta administrativa pessoal incluída no código-fonte.

### Acesso genérico de apresentação

- **Organização:** horizonte.
- **Usuário:** demo.
- **Senha demonstrativa:** ChronosDemo@2026.
- **Perfil:** Demonstração, com consulta ao dashboard, unidades, setores e catálogos.

Essa conta está configurada no ambiente de apresentação do autor. Para reproduzi-la numa instalação nova, o administrador deve usar **Acessos → Novo acesso**, selecionar **Demonstração** e cadastrar as credenciais acima. O pacote não transporta contas ou banco ativo. Não confunda essa conta de consulta com um administrador.

Em **Visão geral**, a base inicial contém **350 colaboradores e 19 setores** fictícios. São contagens de cadastro; cobertura e custos dependem dos cálculos solicitados. O uso de e-mail como usuário não ativa login Google nem envia mensagens.

### Roteiro inicial

1. Confira os totais em **Visão geral**.
2. Consulte **Unidades**, **Setores** e **Catálogos**.
3. Alterne os temas claro/escuro no botão de sol/lua.
4. Com um perfil operacional autorizado, siga as próximas páginas para pessoas, calendário, cenários, financeiro e otimização.
5. Use **Sair da plataforma** ao terminar. Fechar a aba não desliga os servidores.

Os módulos e os botões seguem o perfil e a unidade autorizada. A conta demo não altera dados, consulta salários, exporta pessoas ou aprova escalas. As páginas seguintes descrevem também as funções dos perfis operacionais. O administrador continua sujeito à exigência de outro responsável para aprovar sua própria proposta.
'''

operation = '''## 9. Instalação e operação local

### Prepare uma instalação nova

O pacote contém código-fonte para avaliação técnica, não um instalador. Use Windows, Python 3.13 e Node.js compatível com o frontend (a validação utilizou Node 22.14). Extraia numa pasta nova e confira o hash do download. Exemplo de pasta: **C:\\Projetos\\Chronos-1.0**.

No PowerShell, entre na pasta extraída e defina um runtime fora do projeto e do OneDrive:

```powershell
Set-Location 'C:\\Projetos\\Chronos-1.0'
$env:CHRONOS_RUNTIME_DIR =
  Join-Path $env:LOCALAPPDATA 'Chronos\\1.0'
.\\scripts\\setup.ps1 -RuntimeDir $env:CHRONOS_RUNTIME_DIR
.\\scripts\\create-admin.ps1 -RuntimeDir $env:CHRONOS_RUNTIME_DIR
```

Escolha as credenciais do seu administrador. O setup instala dependências, prepara o banco local e importa os dados fictícios. O pacote não contém bancos ativos, contas do autor, segredos ou runtimes. Confira **docs/release/handover.md** para requisitos e opções de banco.

### Inicie os componentes

Abra três terminais na raiz do projeto. Repita a definição de **CHRONOS_RUNTIME_DIR** em cada terminal e execute **um comando por terminal**:

```powershell
.\\scripts\\start-backend.ps1 -RuntimeDir $env:CHRONOS_RUNTIME_DIR
```

```powershell
.\\scripts\\start-frontend.ps1
```

```powershell
.\\scripts\\start-worker.ps1 -RuntimeDir $env:CHRONOS_RUNTIME_DIR
```

Abra **http://127.0.0.1:5187**, organização **horizonte**, com seu administrador. Para criar o visitante demo, siga a página 1. O consumidor de automações é opcional e usa **scripts/start-automations.ps1**; as definições continuam desativadas por padrão. **n8n permanece bloqueado** pela revisão de dependências.

### Encerre ou resolva um problema

Use **Sair da plataforma** e **Ctrl+C** em cada terminal. Não restaure o banco apenas para abrir novamente o projeto. Faça backup antes de intervenções, conforme **docs/operations/recovery.md**.

- **Página não abre:** confirme os servidores e o endereço local. **401:** entre novamente. **403/404:** confira perfil e unidade.
- **409:** reveja conflito, sobreposição ou insumos alterados. **Cálculo na fila:** confirme o worker.
- **503/500:** consulte **http://127.0.0.1:8017/api/v1/health/ready** e informe a correlação ao suporte. Não compartilhe segredos ou dumps.

O núcleo funciona sem n8n. QA visual de navegador, Power BI Desktop e liberação de produção continuam pendentes. Uma página estática de portfólio não equivale a uma implantação operacional do sistema.
'''


def main():
    source=(ROOT/'docs/manual-de-uso.md').read_text(encoding='utf-8').split('<!-- page -->')
    assert len(source)==9
    source[0]=intro;source[-1]=operation
    text='\n<!-- page -->\n'.join(source)
    text=text.replace('Nesta execução local, ele foi iniciado junto da API e da interface.', 'Inicie-o no ambiente local conforme as instruções da página 9.')
    text=text.replace('A agenda depende do scheduler, que não foi iniciado nesta sessão. O consumidor de eventos locais está ativo.', 'A agenda depende do scheduler, que deve ser habilitado separadamente. Inicie o consumidor local para processar os eventos autorizados.')
    for value in ('stop-live-session','start-live-session'):
        assert value not in text
    assert not re.search(r'@gmail\.com|C:\\Users\\|[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}|Chronos@\d{4}',text)
    public=ROOT/'docs/portfolio/manual-publico.md';public.write_text(text,encoding='utf-8')
    docs=WORK/'docs';docs.mkdir(parents=True,exist_ok=True)
    (docs/'manual-de-uso.md').write_text(text,encoding='utf-8')
    spec=importlib.util.spec_from_file_location('chronos_manual',ROOT/'scripts/build_user_manual.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=WORK
    module.OUTPUT=PORTFOLIO/'downloads/Chronos-1.0-Manual-de-Uso.pdf'
    module.build()


if __name__=='__main__':main()
