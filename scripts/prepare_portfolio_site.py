"""Publishable Chronos presentation and HTML manual in the existing portfolio checkout."""
from pathlib import Path
import argparse
import hashlib
from html import escape
import json
import re
import shutil
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT.parent / 'portfolio'
PUBLIC = 'https://leandroaugferreira.github.io/'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', value).encode('ascii','ignore').decode().lower()).strip('-')

def rich(value):
    value = escape(value)
    value = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', value)
    return re.sub(r'`(.+?)`', r'<code>\1</code>', value)

def render_manual(text):
    out=[]; toc=[]; listing=None
    def close():
        nonlocal listing
        if listing:
            out.append('</'+listing+'>'); listing=None
    for line in text.splitlines():
        if line.startswith('# '):
            continue
        if not line.strip():
            close(); continue
        if line.startswith('## '):
            close(); title=line[3:]; ident=slug(title); toc.append((ident,title))
            out.append('<h2 id="'+ident+'">'+rich(title)+'</h2>'); continue
        match=re.match(r'^(\d+\.|-) (.+)',line)
        if match:
            kind='ul' if match[1]=='-' else 'ol'
            if kind!=listing:
                close(); out.append('<'+kind+'>'); listing=kind
            out.append('<li>'+rich(match[2])+'</li>')
        else:
            close(); out.append('<p>'+rich(line)+'</p>')
    close()
    return '\n'.join(out), ''.join('<a href="#'+ident+'">'+escape(title)+'</a>' for ident,title in toc)

def head(title, description, path):
    css='assets/chronos.css?v='+sha(SITE/'assets/chronos.css')[:12]
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Leandro Augusto Ferreira</title><meta name="description" content="{description}"><meta name="author" content="Leandro Augusto Ferreira"><meta name="theme-color" content="#101f2a">
<link rel="canonical" href="{PUBLIC+path}"><link rel="icon" href="img/chronos-mark.svg" type="image/svg+xml"><meta property="og:type" content="website"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:url" content="{PUBLIC+path}"><meta property="og:image" content="{PUBLIC}img/chronos-social.png"><meta name="twitter:card" content="summary_large_image"><link rel="stylesheet" href="{css}">'''

def signature():
    return '<div class="signature"><span class="monogram" aria-hidden="true">lf.</span><span><small>DESIGN & DESENVOLVIMENTO</small><b>Leandro Augusto Ferreira</b></span></div>'

def navigation(manual=False):
    return '<a class="skip" href="#conteudo">Pular para o conteúdo</a><nav class="container project-nav" aria-label="Navegação do projeto"><a class="wordmark" href="'+PUBLIC+'chronos.html"><img src="img/chronos-mark.svg" width="38" height="38" alt="">chronos<span>.</span></a><div><a '+('' if manual else 'aria-current="page" ')+'href="'+PUBLIC+'chronos.html">O projeto</a><a '+('aria-current="page" ' if manual else '')+'href="chronos-manual.html" '+('' if manual else 'target="_blank" rel="noopener"')+'>Manual de uso</a><a href="'+PUBLIC+'#chronos">Portfólio ↗</a></div></nav>'

def manual_page():
    body,toc=render_manual((ROOT/'docs/portfolio/manual-web.md').read_text(encoding='utf-8'))
    return head('Manual do Chronos 1.0','Como baixar, abrir e explorar o Chronos. Guia com acesso de demonstração, roteiro rápido e explicações para visitantes e recrutadores.','chronos-manual.html')+'''</head><body class="manual-page">'''+navigation(True)+'''<main class="container" id="conteudo"><header class="manual-heading"><p class="eyebrow">CHRONOS 1.0 / GUIA DE USO</p><h1>Conheça. Explore.<br><em>Entenda o projeto.</em></h1><p>Do primeiro acesso às decisões de desenvolvimento. Um guia de leitura direta, com um roteiro rápido para começar.</p><a class="button primary" href="'''+PUBLIC+'''chronos.html#download">Ir para o download do aplicativo →</a></header><div class="manual-layout"><aside class="manual-index" aria-label="Índice do manual"><p class="eyebrow">NESTE GUIA</p>'''+toc+'''</aside><article class="manual-content" aria-label="Instruções de uso do Chronos">'''+body+'''</article></div></main><footer class="container">'''+signature()+'''<p>Chronos 1.0 · Guia atualizado em 01/11/2026</p></footer></body></html>'''

def project_page(download_url, artifact):
    size=f'{artifact.stat().st_size/1024/1024:.1f}'.replace('.',',')+' MB'
    checksum=sha(artifact)
    features=[('01','Uma estrutura que faz sentido','Unidades, setores, funções e competências configuráveis. O Hospital Horizonte demonstra uma operação com necessidades diferentes em cada área.'),('02','Pessoas por trás das escalas','Contratos, qualificações e indisponibilidades ajudam a determinar quais profissionais podem assumir cada atividade.'),('03','Comparar antes de decidir','Cenários versionados, projeções de custos e otimização permitem explorar hipóteses e revisar os resultados antes de aprovar uma proposta.')]
    cards=''.join(f'<article class="feature"><span>{n}</span><h3>{title}</h3><p>{copy}</p></article>' for n,title,copy in features)
    return head('Chronos 1.0 — pessoas e tempo em equilíbrio','Projeto full stack de Leandro Augusto Ferreira: gestão de jornadas, simulação financeira e otimização de escalas. Baixe a demonstração para Windows e explore o manual online.','chronos.html')+'''<link rel="stylesheet" href="assets/video-player.css"><script src="assets/video-player.js" defer></script></head><body><a class="skip" href="#conteudo">Pular para o conteúdo</a>'''+navigation().replace('<a class="skip" href="#conteudo">Pular para o conteúdo</a>','')+f'''<main class="container" id="conteudo"><header class="hero"><div><p class="eyebrow">PROJETO EM DESTAQUE / CHRONOS 1.0</p><h1>O tempo encontra<br>seu <em>equilíbrio.</em></h1><p class="lead">Gestão Inteligente de Jornadas e Escalas.</p><p>Como organizar equipes, atender às necessidades de cada setor e comparar alternativas de jornada? O Chronos conecta essas decisões em uma plataforma de planejamento.</p><div class="actions"><a class="button primary" href="#download">Experimentar no Windows ↓</a><a class="button" href="chronos-manual.html" target="_blank" rel="noopener">Abrir manual de uso ↗</a></div><p class="note">Um projeto de Leandro Augusto Ferreira. Demonstração local com dados fictícios.</p></div><aside class="hero-aside" aria-label="Cenário de demonstração"><img class="hero-symbol" src="img/chronos-mark.svg" alt="Símbolo Chronos: a letra C e os ponteiros de um relógio" width="150" height="150"><p class="eyebrow">PESSOAS · JORNADAS · DECISÕES</p><div class="numbers"><div><strong>350</strong><span>Colaboradores fictícios</span></div><div><strong>19</strong><span>Setores na demonstração</span></div><div><strong>24h</strong><span>Operação do cenário hospitalar</span></div><div><strong>12</strong><span>Meses na projeção financeira</span></div></div></aside></header>
<section id="projeto" aria-labelledby="projeto-titulo"><div class="section-heading"><p class="eyebrow">PARA QUEM ESTÁ AVALIANDO</p><h2 id="projeto-titulo">Um problema de gestão.<br><em>Várias decisões conectadas.</em></h2><p>O cenário principal é o Hospital Horizonte, mas setores, cargos, turnos e regras são configuráveis para outros segmentos.</p></div><div class="features">{cards}</div><div class="authorship"><div><p class="eyebrow">MINHA ATUAÇÃO</p><h3>Da ideia à aplicação.</h3></div><p>Concepção do produto, desenvolvimento full stack, modelagem de dados, regras de negócio, simulação financeira, otimização, testes e distribuição local. A interface também tem identidade própria: azul profundo, cobre, tons de papel e grafismos de tempo.</p></div></section>
<section aria-labelledby="tecnologia-titulo"><p class="eyebrow">O QUE OBSERVAR NO PROJETO</p><h2 id="tecnologia-titulo">Implementação com contexto.</h2><div class="technical-grid"><div><h3>Interface e experiência</h3><p>React e TypeScript, temas claro e escuro, navegação por perfil e componentes compartilhados entre os módulos.</p></div><div><h3>Dados e regras</h3><p>API FastAPI, SQLAlchemy, migrações Alembic, permissões por unidade e registros de auditoria. O executável usa SQLite local; a arquitetura também contempla PostgreSQL.</p></div><div><h3>Cálculos e propostas</h3><p>Projeção financeira com precisão decimal, OR-Tools para geração de propostas e processamento do otimizador separado da API.</p></div><div><h3>Revisão e rastreabilidade</h3><p>Versões de cenários, origem das premissas e revisão humana. Uma modalidade de jornada cadastrada não se torna automaticamente válida para qualquer cargo.</p></div></div><div class="tags"><span>Python</span><span>React</span><span>TypeScript</span><span>FastAPI</span><span>OR-Tools</span><span>SQLAlchemy</span></div></section>
<section id="download" class="download-section" aria-labelledby="download-titulo"><div><p class="eyebrow">EXPERIMENTE NO SEU COMPUTADOR</p><h2 id="download-titulo">Abra o aplicativo.<br><em>Explore no seu ritmo.</em></h2><p>Baixe o executável, abra o arquivo e aguarde a janela indicar que está pronto. O Chronos abre no navegador e funciona no seu computador, sem instalação de Python ou Node.js.</p><div class="actions"><a class="button primary" href="{escape(download_url,quote=True)}" download>Baixar para Windows (.exe) · {size}</a><a class="button" href="chronos-manual.html#baixe-e-abra-o-aplicativo" target="_blank" rel="noopener">Como abrir o aplicativo ↗</a></div><p class="note">Windows de 64 bits · Chronos 1.0 · Edição de demonstração · Executável sem assinatura digital</p></div><div class="demo-access"><p class="eyebrow">ACESSO DE CONSULTA INCLUÍDO</p><dl><div><dt>Organização</dt><dd><code>horizonte</code></dd></div><div><dt>Usuário</dt><dd><code>demo</code></dd></div><div><dt>Senha demonstrativa</dt><dd><code>ChronosDemo@2026</code></dd></div></dl><p>Consulte dashboard, unidades, setores e catálogos. Para editar dados fictícios e testar os demais módulos, crie seu próprio administrador na janela do aplicativo.</p></div></section>
<section id="manual" class="manual-callout" aria-labelledby="manual-titulo"><div><p class="eyebrow">MANUAL EM UMA ABA PRÓPRIA</p><h2 id="manual-titulo">Um roteiro claro para começar.</h2><p>Primeiro acesso, passeio de cinco minutos, criação do administrador e explicação dos módulos. Tudo em uma página com índice, leitura confortável e instruções diretas.</p></div><a class="button primary" href="chronos-manual.html" target="_blank" rel="noopener">Abrir o manual completo ↗</a></section>
<section id="apresentacao" aria-labelledby="apresentacao-titulo"><p class="eyebrow">VISÃO GERAL EM VÍDEO</p><h2 id="apresentacao-titulo">Entenda como as partes se conectam.</h2><div class="chronos-player" data-project-player data-project-name="Chronos 1.0" data-scenes="media/chronos-apresentacao-cenas.json"><video controls playsinline preload="metadata" poster="img/teasers/chronos-completo.jpg" width="1280" height="720" aria-label="Guia ilustrado de apresentação do Chronos 1.0"><source src="media/chronos-apresentacao.mp4" type="video/mp4"><track kind="subtitles" src="media/chronos-apresentacao-pt.vtt" srclang="pt-BR" label="Português BR" default><track kind="subtitles" src="media/chronos-apresentacao-en.vtt" srclang="en" label="English">Seu navegador não reproduz este vídeo.</video><div class="chronos-controls"><button type="button" data-video-toggle aria-label="Reproduzir apresentação do Chronos">▶ Reproduzir</button><label>Legendas <select data-caption-language aria-label="Idioma das legendas do Chronos"><option value="pt-BR">Português BR</option><option value="en">English</option><option value="off">Sem legendas</option></select></label></div></div><p class="note">Guia ilustrado das funções do projeto, com narração e legendas. Os diagramas explicam os fluxos; a interface atual pode ser explorada no aplicativo para Windows.</p></section>
<section aria-labelledby="detalhes-titulo"><h2 id="detalhes-titulo">Para aprofundar a avaliação.</h2><details><summary>Código-fonte e integridade dos downloads</summary><p>O código-fonte é uma alternativa para avaliação técnica. Seu uso exige a preparação do ambiente descrita na documentação incluída.</p><div class="actions"><a class="button" href="downloads/Chronos-1.0-codigo-fonte.zip" download>Baixar código-fonte</a><a class="button" href="downloads/Chronos-1.0-Windows-manifesto.json">Integridade do executável</a><a class="button" href="downloads/Chronos-1.0-manifesto.json">Integridade do código-fonte</a></div><p class="hash">SHA-256 do executável: <code>{checksum}</code></p></details><details><summary>Escopo da demonstração</summary><p>Os dados são fictícios. Os resultados dependem dos cadastros, das premissas e das revisões aplicáveis. O aplicativo não certifica conformidade jurídica ou dimensionamento profissional e não representa uma liberação para produção hospitalar.</p><p>O núcleo funciona sem n8n. A integração n8n permanece desativada pela revisão de dependências. Avaliações em navegador real, Power BI Desktop e homologação operacional continuam pendentes.</p></details></section></main><footer class="container">{signature()}<p>Chronos 1.0 · Pessoas e tempo, em equilíbrio.</p></footer></body></html>'''

def update_cards():
    page=SITE/'index.html'; text=page.read_text(encoding='utf-8')
    for start,end in [('<!-- CHRONOS FEATURED START -->','<!-- CHRONOS FEATURED END -->'),('<!-- CHRONOS GALLERY START -->','<!-- CHRONOS GALLERY END -->')]:
        a=text.index(start); b=text.index(end,a)+len(end)
        card=text[a:b]
        card=card.replace('Hospital Horizonte: 350 colaboradores fictícios, 19 setores e manual completo de uso.','350 colaboradores fictícios, 19 setores e aplicativo para Windows. Explore o manual online e experimente a demonstração.')
        def refresh(match):
            path=match[1]
            return path+'?v='+sha(SITE/path)[:12] if (SITE/path).is_file() else match[0]
        card=re.sub(r'((?:media/chronos-[^"?]+|img/teasers/chronos[^"?]+))\?v=[a-f0-9]+',refresh,card)
        text=text[:a]+card+text[b:]
    text=re.sub(r'(assets/chronos-featured\.css)\?v=[a-f0-9]+',lambda m:m[1]+'?v='+sha(SITE/m[1])[:12],text)
    page.write_text(text,encoding='utf-8')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manual-only',action='store_true')
    parser.add_argument('--executable',type=Path)
    parser.add_argument('--download-url',default='downloads/Chronos.exe')
    parser.add_argument('--source-package',type=Path)
    args=parser.parse_args()
    shutil.copyfile(ROOT/'frontend/public/chronos-mark.svg',SITE/'img/chronos-mark.svg')
    shutil.copyfile(ROOT/'docs/portfolio/chronos-site.css',SITE/'assets/chronos.css')
    (SITE/'chronos-manual.html').write_text(manual_page(),encoding='utf-8')
    if args.manual_only:
        return
    if not args.executable or not args.executable.is_file() or not args.source_package or not args.source_package.is_file():
        parser.error('Informe o executável validado e o pacote fonte.')
    if args.download_url.startswith('downloads/'):
        shutil.copyfile(args.executable,SITE/args.download_url)
    receipt={'product':'Chronos 1.0','edition':'Windows x64 demo','file':'Chronos.exe','bytes':args.executable.stat().st_size,
        'sha256':sha(args.executable),'download_url':args.download_url,'reference_date':'2026-11-01','digitally_signed':False,
        'demo_data':'Hospital Horizonte / 350 colaboradores / 19 setores','personal_accounts_included':False,'n8n_enabled':False,'production_ready':False}
    (SITE/'downloads/Chronos-1.0-Windows-manifesto.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(args.source_package,SITE/'downloads/Chronos-1.0-codigo-fonte.zip')
    shutil.copyfile(args.source_package.with_suffix('.zip.receipt.json'),SITE/'downloads/Chronos-1.0-manifesto.json')
    (SITE/'chronos.html').write_text(project_page(args.download_url,args.executable),encoding='utf-8')
    update_cards()
    print(json.dumps({'executable_sha256':receipt['sha256'],'bytes':receipt['bytes'],'manual':'chronos-manual.html'}))

if __name__=='__main__':
    main()
