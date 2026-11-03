"""Build the Chronos local-use manual with ReportLab (documentation dependency only).

Run with the bundled document Python runtime; does not import the app or read .env.
"""
from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Preformatted

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'output/pdf/Chronos-1.0-Manual-de-Uso.pdf'
FONT_DIR = Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('ChronosText', str(FONT_DIR/'segoeui.ttf')))
pdfmetrics.registerFont(TTFont('ChronosBold', str(FONT_DIR/'segoeuib.ttf')))
pdfmetrics.registerFont(TTFont('ChronosMono', str(FONT_DIR/'consola.ttf')))
pdfmetrics.registerFontFamily('ChronosText', normal='ChronosText', bold='ChronosBold', italic='ChronosText', boldItalic='ChronosBold')
INK = colors.HexColor('#152B3A')
MUTED = colors.HexColor('#526875')
TEAL = colors.HexColor('#007E87')
STYLES = {
    'body': ParagraphStyle('Body', fontName='ChronosText', fontSize=10.1, leading=14, textColor=INK, spaceAfter=7),
    'h1': ParagraphStyle('Hero', fontName='ChronosBold', fontSize=32, leading=38, textColor=INK, spaceAfter=9),
    'h2': ParagraphStyle('Chapter', fontName='ChronosBold', fontSize=19, leading=24, textColor=INK, spaceAfter=13, keepWithNext=True),
    'h3': ParagraphStyle('Section', fontName='ChronosBold', fontSize=11.4, leading=16, textColor=TEAL, spaceBefore=8, spaceAfter=6, keepWithNext=True),
    'item': ParagraphStyle('Item', fontName='ChronosText', fontSize=10.1, leading=14, textColor=INK, leftIndent=15, firstLineIndent=-12, spaceAfter=5),
    'code': ParagraphStyle('Code', fontName='ChronosMono', fontSize=8.2, leading=11.6, textColor=INK, backColor=colors.HexColor('#F0F5F7'), borderPadding=8, spaceBefore=4, spaceAfter=10),
}


def rich(text):
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    def link(match):
        value = match[1].rstrip('.,;')
        return '<link href="'+value+'" color="#007E87">'+value+'</link>'+match[1][len(value):]
    text = re.sub(r'(?<!\w)(https?://[^\s<]+)', link, text)
    return text


def footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(TEAL)
    canvas.rect(0, h-8, w, 8, stroke=0, fill=1)
    canvas.setStrokeColor(colors.HexColor('#DCE6E9'))
    canvas.line(46, 38, w-46, 38)
    canvas.setFillColor(MUTED)
    canvas.setFont('ChronosText', 8)
    canvas.drawString(46, 24, 'CHRONOS 1.0  |  Manual de uso local  |  27/10/2026')
    canvas.drawRightString(w-46, 24, str(doc.page))
    canvas.restoreState()


def build():
    text = (ROOT/'docs/manual-de-uso.md').read_text(encoding='utf-8')
    story = []
    for line in text.splitlines():
        if line.startswith('```'):
            if 'code_lines' in locals():
                story.append(Preformatted('\n'.join(code_lines), STYLES['code']))
                del code_lines
            else:
                code_lines = []
            continue
        if 'code_lines' in locals():
            code_lines.append(line)
            continue
        if not line.strip():
            continue
        if line == '<!-- page -->':
            story.append(PageBreak()); continue
        if line.startswith('# '):
            story.append(Paragraph(rich(line[2:]), STYLES['h1'])); continue
        if line.startswith('## '):
            story.append(Paragraph(rich(line[3:]), STYLES['h2'])); continue
        if line.startswith('### '):
            story.append(Paragraph(rich(line[4:]), STYLES['h3'])); continue
        item = re.match(r'^(\d+\.|-) (.+)', line)
        if item:
            label = '•' if item[1] == '-' else item[1]
            story.append(Paragraph(rich(label+' '+item[2]), STYLES['item']))
        else:
            story.append(Paragraph(rich(line), STYLES['body']))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=46, leftMargin=46,
        topMargin=36, bottomMargin=50, title='Chronos 1.0 - Manual de uso',
        author='Chronos', subject='Instruções de uso local - Hospital Horizonte', pageCompression=1)
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(str(OUTPUT))


if __name__ == '__main__':
    build()
