"""Сборка отчёта .docx из простого описания блоков (python-docx) и экспорт в PDF через Word.

Оформление как у ранее сданных отчётов курса: титул «Дисциплина / Кафедра / ОТЧЁТ / по практической
работе №N / Тема / Выполнил», Times New Roman 14, полуторный интервал, поля 3/1,5/2/2 см.
"""
import subprocess
from pathlib import Path

import docx
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

FONT = 'Times New Roman'
MONO = 'Courier New'
TEXT_WIDTH = Cm(16.5)

_ACC = '(дата обращения: 17.10.2026). — Текст : электронный.'
SOURCES = {   # оформление по ГОСТ Р 7.0.100-2018; ключи используются в Report.use_sources / cite
    'task': 'Задание на практические и лабораторные работы по дисциплине «Проектирование архитектуры ПО». — '
            'Москва, 2026. — Текст : электронный.',
    'm1': 'Практическая работа №1. Развертывание контейнеризированных сред для нескольких типов баз данных : '
          'методические указания. — 2026. — 43 с. — Текст : электронный.',
    'm2': 'Практическая работа №2. CRUD-операции с различными базами данных : методические указания. — 2026. — '
          '71 с. — Текст : электронный.',
    'm3': 'Практическая работа №3. Проектирование логической и физической структуры данных : методические '
          'указания. — 2026. — 34 с. — Текст : электронный.',
    'docker': f'Docker Compose : документация. — URL: https://docs.docker.com/compose/ {_ACC}',
    'redis': f'Redis Documentation. — URL: https://redis.io/docs/latest/ {_ACC}',
    'mongo': f'MongoDB Manual. — URL: https://www.mongodb.com/docs/manual/ {_ACC}',
    'neo4j': f'Neo4j Cypher Manual. — URL: https://neo4j.com/docs/cypher-manual/current/ {_ACC}',
    'es': f'Elasticsearch Guide 8.16. — URL: https://www.elastic.co/guide/en/elasticsearch/reference/8.16/index.html {_ACC}',
    'pg': f'PostgreSQL 16 Documentation. — URL: https://www.postgresql.org/docs/16/index.html {_ACC}',
    'pgpart': f'PostgreSQL 16 Documentation. Table Partitioning. — URL: '
              f'https://www.postgresql.org/docs/16/ddl-partitioning.html {_ACC}',
    'debezium': f'Debezium Documentation. — URL: https://debezium.io/documentation/ {_ACC}',
    'fastapi': f'FastAPI Documentation. — URL: https://fastapi.tiangolo.com/ {_ACC}',
    'c4': f'Brown S. The C4 model for visualising software architecture. — URL: https://c4model.com {_ACC}',
    'jwt': f'Jones M., Bradley J., Sakimura N. JSON Web Token (JWT) : RFC 7519. — IETF, 2015. — URL: '
           f'https://www.rfc-editor.org/rfc/rfc7519 {_ACC}',
    'oauth': f'Hardt D. The OAuth 2.0 Authorization Framework : RFC 6749. — IETF, 2012. — URL: '
             f'https://www.rfc-editor.org/rfc/rfc6749 {_ACC}',
    'pbkdf2': f'Moriarty K., Kaliski B., Rusch A. PKCS #5: Password-Based Cryptography Specification Version 2.1 : '
              f'RFC 8018. — IETF, 2017. — URL: https://www.rfc-editor.org/rfc/rfc8018 {_ACC}',
    'owasp': f'OWASP Cheat Sheet Series. Password Storage Cheat Sheet. — URL: '
             f'https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html {_ACC}',
    'kleppmann': 'Клеппман М. Высоконагруженные приложения. Программирование, масштабирование, поддержка / '
                 'М. Клеппман. — Санкт-Петербург : Питер, 2018. — 640 с. — Текст : непосредственный.',
    'sadalage': 'Садаладж П. Дж., Фаулер М. NoSQL: новая методология разработки нереляционных баз данных / '
                'П. Дж. Садаладж, М. Фаулер. — Москва : Вильямс, 2013. — 192 с. — Текст : непосредственный.',
    'richardson': 'Ричардсон К. Микросервисы. Паттерны разработки и рефакторинга / К. Ричардсон. — '
                  'Санкт-Петербург : Питер, 2019. — 544 с. — Текст : непосредственный.',
    'yourdon': 'Yourdon E. Modern Structured Analysis / E. Yourdon. — Englewood Cliffs : Prentice Hall, 1989. — '
               '672 p. — Текст : непосредственный.',
}


def _set_font(run, size=14, bold=False, italic=False, name=FONT):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run._element.rPr.rFonts.set(qn('w:eastAsia'), name)


class Report:
    def __init__(self, work_title, topic):
        self.d = docx.Document()
        self.fig = 0
        self.src = []
        self.tab = 0
        s = self.d.sections[0]
        s.page_height, s.page_width = Cm(29.7), Cm(21)
        s.left_margin, s.right_margin, s.top_margin, s.bottom_margin = Cm(3), Cm(1.5), Cm(2), Cm(2)
        st = self.d.styles['Normal']
        st.font.name = FONT
        st.font.size = Pt(14)
        st.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        pf = st.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.5
        for name, size in (('Heading 1', 14), ('Heading 2', 14)):
            h = self.d.styles[name]
            h.font.name, h.font.size, h.font.bold, h.font.italic = FONT, Pt(size), True, False
            h.font.color.rgb = None
            rf = h.element.rPr.rFonts
            for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
                if rf.get(qn(a)) is not None:
                    del rf.attrib[qn(a)]
            for a in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
                rf.set(qn(a), FONT)
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True
            h.paragraph_format.line_spacing = 1.5
        self._title(work_title, topic)
        self._toc()
        self._page_numbers()

    # ---------- содержание ----------
    def _toc(self):
        """Страница «Содержание»: поле TOC по заголовкам 1–2 уровня. Номера страниц проставляет Word
        при экспорте (to_pdf обновляет поле и сохраняет .docx)."""
        self._center('СОДЕРЖАНИЕ', 14, True).paragraph_format.space_after = Pt(12)
        p = self.d.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        for kind, text in (('begin', None), ('instr', 'TOC \\o "1-2" \\h \\z \\u'), ('separate', None),
                           ('text', 'Содержание обновляется при экспорте в PDF (to_pdf).'), ('end', None)):
            r = p.add_run()
            if kind == 'instr':
                el = OxmlElement('w:instrText'); el.set(qn('xml:space'), 'preserve'); el.text = text
            elif kind == 'text':
                r.text = text; continue
            else:
                el = OxmlElement('w:fldChar'); el.set(qn('w:fldCharType'), kind)
            r._r.append(el)
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def use_sources(self, keys):
        """Задать порядок источников отчёта (ключи SOURCES); номера для ссылок [N] — по этому порядку."""
        self.src = list(keys)

    def cite(self, *keys):
        """Ссылка в тексте: cite('pg', 'redis') → [3, 5]; подряд идущие номера сворачиваются: [3–6]."""
        nums = sorted(self.src.index(k) + 1 for k in keys)
        parts, i = [], 0
        while i < len(nums):
            j = i
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                j += 1
            parts.append(str(nums[i]) if j == i else f'{nums[i]}, {nums[j]}' if j == i + 1 else f'{nums[i]}–{nums[j]}')
            i = j + 1
        return '[' + ', '.join(parts) + ']'

    def references(self, items=None, title='Список использованных источников'):
        """Нумерованный список источников (ГОСТ Р 7.0.100-2018), ссылки в тексте — [N]."""
        if items is None:
            items = [SOURCES[k] for k in self.src]
        self.h1(title)
        for i, it in enumerate(items, start=1):
            par = self.d.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            par.paragraph_format.first_line_indent = Cm(1.25)
            _set_font(par.add_run(f'{i}. {it}'), 14)

    # ---------- титул и колонтитул ----------
    def _center(self, text, size=14, bold=False, space_before=0):
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(space_before)
        _set_font(p.add_run(text), size, bold)
        return p

    def _title(self, work_title, topic):
        self._center('Дисциплина «Проектирование архитектуры ПО»')
        self._center('Кафедра корпоративных информационных систем')
        self._center('ОТЧЁТ', 16, True, space_before=170)
        self._center(work_title)
        self._center(f'Тема: {topic}', space_before=12)
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.space_before = Pt(130)
        _set_font(p.add_run('Выполнил: студент группы БСБО-01-23'), 14)
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _set_font(p.add_run('Судовский Андрей Леонидович'), 14)
        self._center('Москва, 2026', space_before=110)
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def _page_numbers(self):
        s = self.d.sections[0]
        s.different_first_page_header_footer = True
        p = s.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run()
        for tag, text in (('begin', None), (None, 'PAGE'), ('end', None)):
            if tag:
                el = OxmlElement('w:fldChar'); el.set(qn('w:fldCharType'), tag)
            else:
                el = OxmlElement('w:instrText'); el.set(qn('xml:space'), 'preserve'); el.text = text
            r._r.append(el)
        _set_font(r, 12)

    # ---------- блоки ----------
    def h1(self, text):
        self.d.add_heading(text, level=1)

    def h2(self, text):
        self.d.add_heading(text, level=2)

    def p(self, text, indent=True):
        """Абзац; **жирный** фрагмент и `код` выделяются."""
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if indent:
            par.paragraph_format.first_line_indent = Cm(1.25)
        self._inline(par, text)
        return par

    def _inline(self, par, text):
        import re
        for part in re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', text):
            if not part:
                continue
            if part.startswith('**'):
                _set_font(par.add_run(part[2:-2]), 14, bold=True)
            elif part.startswith('`'):
                _set_font(par.add_run(part[1:-1]), 13, name=MONO)
            else:
                _set_font(par.add_run(part), 14)

    def bullets(self, items):
        for it in items:
            par = self.d.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            par.paragraph_format.left_indent = Cm(1.25)
            par.paragraph_format.first_line_indent = Cm(-0.5)
            self._inline(par, '– ' + it)

    def figure(self, path, caption):
        self.fig += 1
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_before = Pt(6)
        par.paragraph_format.keep_with_next = True
        par.paragraph_format.line_spacing = 1.0
        par.add_run().add_picture(str(path), width=TEXT_WIDTH)
        cap = self.d.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(6)
        _set_font(cap.add_run(f'Рисунок {self.fig} — {caption}'), 12)
        return self.fig

    def table(self, header, rows, widths_cm, caption, size=12):
        self.tab += 1
        cap = self.d.add_paragraph()
        cap.paragraph_format.keep_with_next = True
        cap.paragraph_format.space_before = Pt(6)
        _set_font(cap.add_run(f'Таблица {self.tab} — {caption}'), 12)
        t = self.d.add_table(rows=1, cols=len(header))
        t.style = 'Table Grid'
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(header):
            self._cell(t.rows[0].cells[i], h, widths_cm[i], bold=True, size=size)
        for r in rows:
            cells = t.add_row().cells
            for i, v in enumerate(r):
                self._cell(cells[i], v, widths_cm[i], size=size)
        t.autofit = False   # фиксированная раскладка: ширины колонок как заданы, а не по содержимому
        tblPr = t._tbl.tblPr
        lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblPr.append(lay)
        for i, col in enumerate(t.columns):
            col.width = Cm(widths_cm[i])
        for row in t.rows:   # строки не рвутся между страницами
            trPr = row._tr.get_or_add_trPr()
            el = OxmlElement('w:cantSplit'); trPr.append(el)
        self.d.add_paragraph().paragraph_format.line_spacing = 1.0
        return self.tab

    def _cell(self, cell, text, width_cm, bold=False, size=12):
        cell.width = Cm(width_cm)
        par = cell.paragraphs[0]
        par.paragraph_format.line_spacing = 1.0
        par.paragraph_format.first_line_indent = Cm(0)
        import re
        for part in re.split(r'(`[^`]+`)', str(text)):
            if not part:
                continue
            if part.startswith('`'):
                _set_font(par.add_run(part[1:-1]), size - 2, bold=bold, name=MONO)
            else:
                _set_font(par.add_run(part), size, bold=bold)

    def code(self, text, size=9):
        # моноширинная строка без пробелов не переносится Word'ом и уходит за поле — режем сами:
        # ширина символа Courier New ≈ 0,6 кегля, ширина текста 16,5 см ≈ 468 pt
        width = int(468 / (size * 0.6)) - 1
        lines = []
        for line in text.rstrip('\n').split('\n'):
            indent = ' ' * (len(line) - len(line.lstrip(' ')) + 4)
            while len(line) > width:
                cut = line.rfind(' ', len(indent), width)
                cut = cut if cut > len(indent) + 10 else width
                lines.append(line[:cut])
                line = indent + line[cut:].lstrip(' ')
            lines.append(line)
        for line in lines:
            par = self.d.add_paragraph()
            par.paragraph_format.line_spacing = 1.0
            par.paragraph_format.first_line_indent = Cm(0)
            _set_font(par.add_run(line if line else ' '), size, name=MONO)

    def page_break(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def save(self, path):
        path = Path(path)
        self.d.save(path)
        return path


def to_pdf(docx_path):
    """Экспорт в PDF через установленный Word (COM): поля, шрифты и разрывы как в Word."""
    docx_path = Path(docx_path).resolve()
    pdf = docx_path.with_suffix('.pdf')
    # Содержание (поле TOC) обновляется дважды: после первого прохода само оглавление сдвигает страницы.
    # Порядок важен: сначала PDF, потом сохранение .docx с готовым содержанием (если сохранить раньше,
    # Word молча не экспортирует документ).
    if pdf.exists():
        pdf.unlink()
    ps = ("$w = New-Object -ComObject Word.Application; $w.Visible = $false; $w.DisplayAlerts = 0; "
          f"$d = $w.Documents.Open('{docx_path}', $false, $false); "
          "$d.Fields.Update() | Out-Null; "
          "foreach ($t in $d.TablesOfContents) { $t.Update() | Out-Null; $t.Update() | Out-Null }; "
          f"$d.ExportAsFixedFormat('{pdf}', 17); "
          f"if (-not (Test-Path '{pdf}')) {{ $d.SaveAs2('{pdf}', 17) }}; "
          f"$d.SaveAs2('{docx_path}', 16); $d.Close($false); $w.Quit()")
    for _ in range(3):   # экспорт Word иногда молча не создаёт файл — повторяем с исходного .docx
        src = docx_path.read_bytes()
        subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=True)
        if pdf.exists():
            return pdf
        docx_path.write_bytes(src)
    raise RuntimeError(f'Word не создал {pdf}')
