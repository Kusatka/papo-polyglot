"""Сборка отчётов ЛР2–3 из проверяемых Markdown-исходников в DOCX.

Запускать bundled Python. Финальная проверка: render_docx.py и просмотр всех страниц.
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent


def build(number):
    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21)
    sec.left_margin, sec.right_margin = Cm(3), Cm(1.5)
    sec.top_margin = sec.bottom_margin = Cm(2)
    for name in ['Normal', 'Title', 'Heading 1', 'Heading 2']:
        style = doc.styles[name]
        style.font.name = 'Times New Roman'
        style.font.size = Pt(14 if name != 'Title' else 18)
        style.font.color.rgb = RGBColor(0, 0, 0)
        fonts = style.element.get_or_add_rPr().rFonts
        for key in list(fonts.attrib):
            if key.endswith('Theme'):
                del fonts.attrib[key]
        for key in ['ascii', 'hAnsi', 'eastAsia', 'cs']:
            fonts.set(qn('w:' + key), 'Times New Roman')
        for border in style.element.xpath('.//w:pBdr'):
            border.getparent().remove(border)
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.space_after = Pt(0 if name == 'Normal' else 6)
    title = doc.add_paragraph(f'Лабораторная работа {number}', 'Title')
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph('Дисциплина «Проектирование архитектуры ПО»').alignment = WD_ALIGN_PARAGRAPH.CENTER
    topic = 'Вместимость аудитории и технические требования' if number == 2 else 'Плановые и посещённые часы лекций группы'
    doc.add_paragraph(topic).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph('Судовский Андрей Леонидович\nБСБО-01-23\nМосква 2026').alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_page_break()
    sec.different_first_page_header_footer = True
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    source = ROOT / f'ОТЧЁТ_ЛР{number}_исходник.md'
    for line in source.read_text(encoding='utf-8').splitlines()[4:]:
        if not line.strip():
            continue
        if line.startswith('## '):
            doc.add_heading(line[3:], level=1)
        elif line.startswith('!['):
            caption, relative = re.fullmatch(r'!\[(.*?)\]\((.*?)\)', line).groups()
            p = doc.add_paragraph()
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(str(ROOT / relative), width=Cm(16.5))
            doc.add_paragraph(caption).alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            p = doc.add_paragraph(line.replace('`', ''))
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.first_line_indent = Cm(1.25)
    path = ROOT / f'Отчёт_Лабораторная_{number}.docx'
    for border in doc.element.xpath('.//w:pBdr'):
        border.getparent().remove(border)
    doc.save(path)
    print(path)


if __name__ == '__main__':
    build(2)
    build(3)
