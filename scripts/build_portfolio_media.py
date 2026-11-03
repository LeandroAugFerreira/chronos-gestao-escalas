"""Portfolio explainer: original diagrams, shared mascot and continuous PT-BR narration.

Documentation tools: Pillow, NumPy, edge-tts and FFmpeg. These are not app dependencies.
CHRONOS_MEDIA_TOOLS may point to an existing tools directory with edge-tts.
Visuals are explanatory diagrams, not screenshots of the application.
"""
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import wave

if os.environ.get('CHRONOS_MEDIA_TOOLS'):
    sys.path.insert(0, os.environ['CHRONOS_MEDIA_TOOLS'])
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ['CHRONOS_RUNTIME_DIR'])/'portfolio-2026-10-27'
OUTPUT = ROOT/'output/portfolio'
VOICE = 'pt-BR-AntonioNeural'
FPS = 24
FONT = Path('C:/Windows/Fonts')

SPECS = {
 'resumo': [
  {'title':'Chronos 1.0 • Pessoas, tempo e planejamento', 'image':'intro',
   'pt':'Conheça o Chronos. Uma plataforma para organizar pessoas, jornadas e escalas, com dados de demonstração e decisões rastreáveis.',
   'en':'Meet Chronos: a platform for organizing people, working hours and schedules, using demonstration data and traceable decisions.'},
  {'title':'Cenários, custos e cobertura', 'image':'flow',
   'pt':'Compare hipóteses de jornada, custos e cobertura. Contratos, habilitações e descansos fazem parte da análise.',
   'en':'Compare working-time, cost and coverage assumptions. Contracts, qualifications and rest periods are part of the analysis.'},
  {'title':'Explore o projeto e o manual', 'image':'manual',
   'pt':'Explore o projeto e o manual completo no portfólio.',
   'en':'Explore the project and its complete user guide in the portfolio.'}],
 'apresentacao': [
  {'title':'Chronos 1.0 • Gestão inteligente de jornadas e escalas', 'image':'intro',
   'pt':'Este é um guia do Chronos, um projeto para conectar pessoas, jornadas e planejamento. O Hospital Horizonte é o cenário fictício, com trezentos e cinquenta colaboradores em dezenove setores.',
   'en':'This is a guide to Chronos, a project connecting people, working hours and planning. Hospital Horizonte is the fictional scenario, with 350 employees across 19 departments.'},
  {'title':'Cadastros e regras com fontes', 'image':'records',
   'pt':'A estrutura é configurável para diferentes empresas. Contratos, competências, qualificações e indisponibilidades ajudam a definir quem pode realizar cada atividade. Cadastrar uma regra não confirma sua validade jurídica.',
   'en':'The structure is configurable for different companies. Contracts, skills, qualifications and unavailability help define who can perform each activity. Registering a rule does not establish legal validity.'},
  {'title':'Cenários independentes e versões preservadas', 'image':'flow',
   'pt':'Os cenários congelam as hipóteses e permitem comparar jornadas. A capacidade agregada mostra uma estimativa de horas, mas não substitui uma escala viável por posto e turno.',
   'en':'Scenarios freeze assumptions and allow working-time comparisons. Aggregate capacity estimates hours, but does not replace a feasible schedule for each position and shift.'},
  {'title':'Projeções financeiras em 12 meses', 'image':'finance',
   'pt':'No financeiro, as parcelas têm fontes e uma projeção de doze meses. Os cálculos preservam centavos e salários contratuais. Resultados projetados não são economia comprovada.',
   'en':'Financial components have documented sources and a 12-month projection. Calculations preserve cents and contractual salaries. Projected results are not demonstrated savings.'},
  {'title':'Otimização com restrições e revisão humana', 'image':'solver',
   'pt':'O otimizador considera demanda, habilitações, disponibilidade e descansos. Lacunas ficam visíveis. A proposta mantém sua versão e precisa de revisão humana; o autor não aprova sua própria execução.',
   'en':'The optimizer considers demand, qualifications, availability and rest. Coverage gaps remain visible. Proposals retain their version and require human review; authors cannot approve their own run.'},
  {'title':'Manual e demonstração local', 'image':'manual',
   'pt':'Na página do projeto, consulte o manual, as instruções de execução e o código-fonte. A conta demo permite consultar o painel e a estrutura. O sistema é local; esta página apresenta o projeto, sem hospedar uma API pública.',
   'en':'The project page provides the manual, setup instructions and source code. The demo account can view the dashboard and structure. The system runs locally; this page presents the project without hosting a public API.'}]
}


def font(size, bold=False):
    return ImageFont.truetype(str(FONT/('segoeuib.ttf' if bold else 'segoeui.ttf')), size)


def lines(draw, text, xy, size=27, width=900, fill='#bbc6cc', bold=False, leading=1.35):
    face=font(size,bold); x,y=xy; current=''
    for word in text.split():
        trial=(current+' '+word).strip()
        if draw.textlength(trial,font=face)>width and current:
            draw.text((x,y),current,font=face,fill=fill);y+=round(size*leading);current=word
        else:current=trial
    if current:draw.text((x,y),current,font=face,fill=fill)
    return y+round(size*leading)


def diagram(kind):
    image=Image.new('RGB',(1280,720),'#101f2a');d=ImageDraw.Draw(image)
    for x in range(0,1280,80):d.line((x,0,x,720),fill='#1a2c37')
    for y in range(0,720,80):d.line((0,y,1280,y),fill='#1a2c37')
    d.line((65,66,1215,66),fill='#3b4b54',width=2)
    d.text((70,26),'CHRONOS 1.0',font=font(23,True),fill='#e9b98c')
    d.text((849,30),'GUIA ILUSTRADO DO PROJETO',font=font(16),fill='#bbc6cc')
    if kind=='intro':
        d.text((70,110),'Pessoas. Tempo. Planejamento.',font=font(50,True),fill='#f0eee8')
        lines(d,'Gestão Inteligente de Jornadas e Escalas',(74,188),31)
        d.ellipse((920,292,1170,542),outline='#e9b98c',width=5)
        d.line((1045,417,1045,340),fill='#f0eee8',width=6);d.line((1045,417,1103,449),fill='#f0eee8',width=6)
        for x,value,label in ((270,'350','colaboradores fictícios'),(580,'19','setores configuráveis')):
            d.text((x,323),value,font=font(91,True),fill='#e9b98c');lines(d,label,(x,433),25,width=300)
        lines(d,'Hospital Horizonte • cenário de demonstração',(270,580),25)
    elif kind in ('flow','records','solver'):
        title={'flow':'Da hipótese à decisão','records':'Dados com contexto e origem','solver':'Restrições antes da proposta'}[kind]
        d.text((70,115),title,font=font(50,True),fill='#f0eee8')
        items={'flow':[('Cadastros','Pessoas e condições'),('Jornadas','Regras e vigências'),('Cenários','Versões independentes'),('Propostas','Cobertura e revisão')],
               'records':[('Contratos','Carga, salário e vigência'),('Competências','Atividades compatíveis'),('Habilitações','Validade e evidências'),('Disponibilidade','Ausências e descansos')],
               'solver':[('Demanda','Atividade, horário e fonte'),('Elegibilidade','Habilitação e competência'),('Restrições','Contrato e descanso'),('Revisão','Lacunas e decisão humana')]}[kind]
        for i,(label,note) in enumerate(items):
            x=260+(i%2)*474;y=255+(i//2)*180
            d.rounded_rectangle((x,y,x+439,y+143),radius=18,fill='#192c37',outline='#3b4b54',width=2)
            d.text((x+25,y+20),label,font=font(32,True),fill='#e9b98c');lines(d,note,(x+25,y+75),24,width=395)
        lines(d,'Hipóteses explícitas • sem aprovação automática',(265,638),24)
    elif kind=='finance':
        d.text((70,115),'Quanto custa cada hipótese?',font=font(50,True),fill='#f0eee8')
        d.text((265,255),'12 meses',font=font(82,True),fill='#e9b98c')
        lines(d,'Parcelas, fontes e recorrências',(268,367),30)
        for i in range(12):
            x=273+i*75;d.ellipse((x,477,x+17,494),fill='#e9b98c')
            if i<11:d.line((x+17,485,x+74,485),fill='#3b4b54',width=3)
        lines(d,'Centavos exatos • salários preservados',(270,548),29)
        lines(d,'Projeção não comprova economia real.',(270,603),25)
    else:
        d.text((70,115),'O próximo passo está no manual.',font=font(48,True),fill='#f0eee8')
        for i,label in enumerate(('Acesso e primeiros passos','Cadastros, regras e cenários','Custos, otimização e relatórios')):
            y=278+i*95;d.ellipse((274,y+5,285,y+16),fill='#e9b98c');lines(d,label,(310,y-5),31,width=850)
        lines(d,'Leia o manual online e baixe o aplicativo.',(270,600),27)
    return image


def normalized(text):return ''.join(c.lower() for c in text if c.isalnum())


async def audio(kind, chapters):
    spoken=' '.join(c['pt'] for c in chapters);digest=hashlib.sha256((spoken+VOICE+'+3%-2Hz').encode()).hexdigest()
    mp3=WORK/(kind+'.mp3');meta=WORK/(kind+'.words.json');marker=WORK/(kind+'.sha256')
    if not (mp3.exists() and meta.exists() and marker.exists() and marker.read_text()==digest):
        import edge_tts
        words=[];voice=edge_tts.Communicate(spoken,VOICE,rate='+3%',pitch='-2Hz',boundary='WordBoundary')
        with mp3.open('wb') as stream:
            async for chunk in voice.stream():
                if chunk['type']=='audio':stream.write(chunk['data'])
                elif chunk['type']=='WordBoundary':words.append({'text':chunk['text'],'start':chunk['offset']/1e7,'end':(chunk['offset']+chunk['duration'])/1e7})
        assert words
        meta.write_text(json.dumps(words,ensure_ascii=False),encoding='utf-8');marker.write_text(digest)
    wav=WORK/(kind+'.wav')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(mp3),'-ar','24000','-ac','1',str(wav)],check=True)
    with wave.open(str(wav),'rb') as source:samples=np.frombuffer(source.readframes(source.getnframes()),dtype='<i2').astype(np.float32)/32768
    words=json.loads(meta.read_text(encoding='utf-8'));assert ''.join(normalized(w['text']) for w in words)==normalized(spoken)
    cursor=0
    for w in words:w['position']=cursor;cursor+=len(normalized(w['text']))
    cursor=0;timeline=[]
    for chapter in chapters:
        end=cursor+len(normalized(chapter['pt']));selected=[w for w in words if cursor<=w['position']<end]
        timeline.append(chapter|{'start':selected[0]['start'],'end':selected[-1]['end']});cursor=end
    for i,c in enumerate(timeline):c['scene_start']=0 if not i else (timeline[i-1]['end']+c['start'])/2
    return timeline,samples,len(samples)/24000


def stamp(value):
    ms=round(value*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'


def render(kind, chapters, samples, duration, mascot):
    frames=[diagram(c['image']) for c in chapters]
    position=(12,720-mascot.height-10)
    output=OUTPUT/f'chronos-{kind}.mp4'
    command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r',str(FPS),'-i','-',
        '-i',str(WORK/(kind+'.wav')),'-map','0:v','-map','1:a','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',
        '-af','loudnorm=I=-16:TP=-1.5:LRA=11','-t',str(duration),'-movflags','+faststart',str(output)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE);index=0
    try:
        for n in range(math.ceil(duration*FPS)):
            t=n/FPS
            while index+1<len(chapters) and t>=chapters[index+1]['scene_start']:index+=1
            frame=frames[index].copy();frame.paste(mascot,position,mascot)
            segment=samples[int(t*24000):int((t+1/FPS)*24000)]
            level=min(1,float(np.sqrt(np.mean(segment**2)))*6) if len(segment) else 0
            d=ImageDraw.Draw(frame);x=position[0]+round(mascot.width*.415);y=position[1]+round(mascot.height*.265)
            for bar in range(5):
                height=1+round(level*(3+3*abs(math.sin(n*.7+bar))))
                d.rounded_rectangle((x-8+bar*4,y-height/2,x-6+bar*4,y+height/2),radius=1,fill='#38e4ff')
            if n==2*FPS:frame.save(OUTPUT/f'chronos-{kind}-preview.jpg',quality=94)
            if n%FPS==0 and index not in getattr(render,'saved',set()):
                frame.save(WORK/f'{kind}-scene-{index}.jpg',quality=92)
                render.saved=getattr(render,'saved',set())|{index}
            process.stdin.write(frame.tobytes())
        process.stdin.close();assert process.wait()==0
    finally:
        if process.poll() is None:process.terminate()
    scenes=[{'start':c['scene_start'],'end':chapters[i+1]['scene_start'] if i+1<len(chapters) else duration,'title':c['title']} for i,c in enumerate(chapters)]
    (OUTPUT/f'chronos-{kind}-cenas.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2),encoding='utf-8')
    for language in ('pt','en'):
        blocks=['WEBVTT','']
        for i,c in enumerate(chapters,1):blocks.extend([str(i),stamp(c['start'])+' --> '+stamp(c['end']),c[language],''])
        (OUTPUT/f'chronos-{kind}-{language}.vtt').write_text('\n'.join(blocks),encoding='utf-8')


async def main():
    WORK.mkdir(parents=True,exist_ok=True);OUTPUT.mkdir(parents=True,exist_ok=True)
    mascot=Image.open(ROOT.parent/'portfolio/img/transcricao/mascote-vox.png').convert('RGBA');mascot.thumbnail((500,243),Image.Resampling.LANCZOS)
    report={}
    for kind,chapters in SPECS.items():
        render.saved=set();timeline,samples,duration=await audio(kind,chapters)
        print(f'{kind}: audio ready, {duration:.2f}s',flush=True)
        render(kind,timeline,samples,duration,mascot)
        report[kind]={'duration':duration,'voice':VOICE,'rate':'+3%','pitch':'-2Hz','continuous_audio':True,'visuals':'explanatory diagrams; not application screenshots'}
        print(f'{kind}: rendered',flush=True)
    (OUTPUT/'chronos-media.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':asyncio.run(main())
