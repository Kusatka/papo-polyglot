"""Диаграммы ЛР №1: C4 (контекст, контейнеры) и DFD в нотации Йордана–Коуда (контекстная, уровень 1).

SVG собирается по координатам (Mermaid не умеет нотацию Йордана: процессы-окружности и хранилища из двух
параллельных линий). Каждая диаграмма пишется в <имя>.html; PNG делает tools/svg_render.sh через Brave.
Запуск: python -P make_diagrams.py
"""
import html
import math
from pathlib import Path

OUT = Path(__file__).parent
FONT = "'Segoe UI', Arial, sans-serif"
C_PERSON, C_SYSTEM, C_CONT, C_EXT, C_DB = '#08427B', '#1168BD', '#438DD5', '#8C8C8C', '#438DD5'


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.items = w, h, []

    def add(self, s):
        self.items.append(s)

    def text(self, x, y, lines, size=15, color='#000', weight='normal', anchor='middle', lh=1.3, italic=False, halo=False):
        if isinstance(lines, str):
            lines = [lines]
        style = 'font-style:italic;' if italic else ''
        extra = ' stroke="#fff" stroke-width="5" paint-order="stroke" stroke-linejoin="round"' if halo else ''
        y0 = y - (len(lines) - 1) * size * lh / 2
        for i, ln in enumerate(lines):
            self.add(f'<text x="{x}" y="{y0 + i * size * lh:.1f}" font-size="{size}" fill="{color}" font-weight="{weight}" '
                     f'text-anchor="{anchor}" dominant-baseline="middle" style="{style}"{extra}>{html.escape(ln)}</text>')

    def arrow(self, pts, label=None, at=None, size=14, color='#444', dash=False, anchor='middle'):
        d = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
        da = ' stroke-dasharray="7 5"' if dash else ''
        self.add(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="2"{da} marker-end="url(#arr)"/>')
        if label:
            if at is None:
                (x1, y1), (x2, y2) = pts[len(pts) // 2 - 1], pts[len(pts) // 2]
                at = ((x1 + x2) / 2, (y1 + y2) / 2)
            self.text(at[0], at[1], label, size=size, color='#222', halo=True, anchor=anchor)

    def save(self, name, title):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
               f'font-family="{FONT}"><defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" '
               f'markerHeight="9" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#444"/></marker></defs>'
               f'<rect width="100%" height="100%" fill="#fff"/>' + '\n'.join(self.items) + '</svg>')
        (OUT / f'{name}.svg').write_text(svg, encoding='utf-8')
        (OUT / f'{name}.html').write_text(
            f'<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f'<style>body{{margin:0;background:#fff}}</style></head><body>{svg}</body></html>', encoding='utf-8')


# ---------- C4 ----------
def c4_box(s, cx, cy, w, h, title, kind, desc, color, person=False, db=False, dashed=False):
    x, y = cx - w / 2, cy - h / 2
    if db:   # цилиндр (ContainerDb)
        ry = 14
        s.add(f'<path d="M{x},{y + ry} A{w / 2},{ry} 0 0 1 {x + w},{y + ry} V{y + h - ry} A{w / 2},{ry} 0 0 1 {x},{y + h - ry} Z" '
              f'fill="{color}" stroke="#2e6295" stroke-width="1.5"/>')
        s.add(f'<path d="M{x},{y + ry} A{w / 2},{ry} 0 0 0 {x + w},{y + ry}" fill="none" stroke="#2e6295" stroke-width="1.5"/>')
        y += 10
    else:
        da = ' stroke-dasharray="8 5"' if dashed else ''
        s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{color}" stroke="#0b3d6e" stroke-width="1.5"{da}/>')
    if person:
        s.add(f'<circle cx="{cx}" cy="{y - 34}" r="32" fill="{color}" stroke="#0b3d6e" stroke-width="1.5"/>')
    n = 1 + 1 + len(desc)
    top = cy - (n * 19) / 2 + (8 if db else 0)
    s.text(cx, top + 4, title, size=17, color='#fff', weight='bold')
    s.text(cx, top + 27, kind, size=13, color='#e8f0fa', italic=True)
    for i, ln in enumerate(desc):
        s.text(cx, top + 54 + i * 19, ln, size=14, color='#fff')


def boundary(s, x, y, w, h, title, kind):
    s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="#666" stroke-width="1.5" stroke-dasharray="10 6"/>')
    s.text(x + 14, y + h - 34, title, size=15, color='#333', weight='bold', anchor='start')
    s.text(x + 14, y + h - 14, kind, size=13, color='#555', anchor='start', italic=True)


def c4_context():
    s = Svg(1500, 450)
    s.text(750, 26, 'C4, уровень 1 — контекст системы (ЛР №1)', size=19, weight='bold')
    c4_box(s, 165, 260, 270, 190, 'Пользователь API', '[Person]',
           ['преподаватель, сотрудник', 'кафедры (роли teacher,', 'student); Swagger UI, curl,', 'PowerShell'], C_PERSON, person=True)
    c4_box(s, 750, 260, 370, 210, 'Аналитическая система кафедры', '[Software System]',
           ['API Gateway с JWT-аутентификацией', 'и сервисы лабораторных работ;', 'ЛР №1 — 10 студентов с минимальной', 'посещаемостью лекций с термином'], C_SYSTEM)
    c4_box(s, 1320, 260, 330, 210, 'Хранилища данных кафедры', '[Software System, внешняя]',
           ['стенд ПР №1 со структурой ПР №3:', 'PostgreSQL, Elasticsearch, Redis,', 'MongoDB, Neo4j (сеть Docker', 'practice01_default)'], C_EXT)
    s.arrow([(300, 235), (565, 235)], ['Получает JWT,', 'запрашивает отчёт', '[HTTP, JSON]'], at=(432, 185))
    s.arrow([(565, 290), (300, 290)], ['Отчёт: студенты,', '% посещения, период,', 'термин в курсах'], at=(432, 340))
    s.arrow([(935, 260), (1155, 260)], ['Читает лекции,', 'посещаемость,', 'карточки студентов', '[HTTP, SQL, RESP]'], at=(1045, 192))
    s.save('c4_context', 'C4 контекст')


def c4_container():
    s = Svg(1640, 960)
    s.text(820, 26, 'C4, уровень 2 — контейнеры (ЛР №1)', size=19, weight='bold')
    c4_box(s, 160, 230, 250, 170, 'Пользователь API', '[Person]',
           ['преподаватель (teacher)', 'или студент (student);', 'Swagger UI, curl, PowerShell'], C_PERSON, person=True)
    boundary(s, 420, 60, 540, 820, 'Аналитическая система кафедры', '[Software System; docker compose, проект lab1]')
    c4_box(s, 680, 230, 470, 250, 'API Gateway', '[Container: Python 3.12, FastAPI, uvicorn; api-gateway :8000]',
           ['POST /auth/login — проверка пароля (PBKDF2)', 'и выдача JWT (HS256, 60 мин);', 'проверка JWT на каждом вызове;',
            'GET /api/lab1/report — маршрутизация', 'в сервис ЛР №1; Swagger UI /docs'], C_CONT)
    c4_box(s, 680, 610, 470, 250, 'Сервис ЛР №1', '[Container: Python 3.12, FastAPI; lab1-service :8001]',
           ['GET /report — отчёт о 10 студентах', 'с минимальной посещаемостью лекций,', 'содержащих термин, за период;',
            'повторная проверка JWT; порт наружу', 'не опубликован (только сеть Docker)'], C_CONT)
    boundary(s, 1050, 60, 560, 860, 'Стенд хранилищ ПР №1 (структура ПР №3)', '[сеть Docker practice01_default]')
    c4_box(s, 1330, 200, 420, 190, 'Elasticsearch 8.16', '[ContainerDb: индекс lectures]',
           ['title, annotation, content_text,', 'анализатор russian_custom', '(словоформы), lecture_type'], C_DB, db=True)
    c4_box(s, 1330, 450, 420, 200, 'PostgreSQL 16', '[ContainerDb: university_system]',
           ['attendance — 20 недельных партиций', '+ default; schedule, lectures,', 'students, student_groups, specialties'], C_DB, db=True)
    c4_box(s, 1330, 690, 420, 170, 'Redis 7, база 2', '[ContainerDb: кэш ключ-значение]',
           ['хеши student:{id} — карточка', 'студента, TTL 7200 с'], C_DB, db=True)
    s.text(1330, 822, 'MongoDB и Neo4j в выборке ЛР №1 не участвуют', size=14, color='#555', italic=True)
    s.arrow([(285, 215), (445, 215)], ['вход, вызов', 'отчёта [HTTP', ':8000, JSON,', 'Bearer JWT]'], at=(352, 160))
    s.arrow([(445, 265), (285, 265)], ['JWT, отчёт', 'JSON, 401/422'], at=(352, 300))
    s.arrow([(680, 355), (680, 485)], ['GET /report с тем же JWT', '[HTTP :8001, внутри сети Docker]'], at=(680, 420))
    s.arrow([(915, 560), (1120, 220)], ['1. фраза → id лекций', '[HTTP, Query DSL]'], at=(1000, 330))
    s.arrow([(915, 610), (1120, 470)], ['2. агрегат посещаемости;', '3а. карточки при промахе', '[SQL, psycopg]'], at=(1050, 552))
    s.arrow([(915, 660), (1120, 690)], ['3. HGETALL / HSET+EXPIRE', '[RESP]'], at=(1010, 712))
    s.save('c4_container', 'C4 контейнеры')


# ---------- DFD (Йордан–Коуд) ----------
def process(s, cx, cy, r, num, name):
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff8e6" stroke="#9a6b00" stroke-width="2"/>')
    s.text(cx, cy - r + 26, num, size=16, weight='bold', color='#7a5200')
    s.text(cx, cy + 10, name, size=15)


def entity(s, cx, cy, w, h, name):
    s.add(f'<rect x="{cx - w / 2}" y="{cy - h / 2}" width="{w}" height="{h}" fill="#eef3fb" stroke="#2e4a7a" stroke-width="2"/>')
    s.text(cx, cy, name, size=15, weight='bold')


def store(s, cx, cy, w, sid, name):
    x1, x2 = cx - w / 2, cx + w / 2
    s.add(f'<line x1="{x1}" y1="{cy - 24}" x2="{x2}" y2="{cy - 24}" stroke="#2f6b2f" stroke-width="2"/>')
    s.add(f'<line x1="{x1}" y1="{cy + 24}" x2="{x2}" y2="{cy + 24}" stroke="#2f6b2f" stroke-width="2"/>')
    s.text(x1 + 8, cy, sid, size=15, weight='bold', color='#2f6b2f', anchor='start')
    s.text(cx + 18, cy, name, size=14)


def on(c, toward, r):
    """точка на окружности процесса c=(x, y) в сторону точки toward"""
    dx, dy = toward[0] - c[0], toward[1] - c[1]
    d = math.hypot(dx, dy)
    return (c[0] + r * dx / d, c[1] + r * dy / d)


def dfd_context():
    s = Svg(1500, 520)
    s.text(750, 26, 'DFD (Йордан–Коуд), контекстная диаграмма — ЛР №1', size=19, weight='bold')
    P, R = (750, 290), 135
    entity(s, 165, 290, 260, 230, 'Пользователь API')
    entity(s, 1330, 290, 250, 110, '')
    s.text(1330, 290, ['Загрузка данных', 'кафедры (ПР №3)'], size=15, weight='bold')
    process(s, *P, R, '0', ['Формирование отчёта', 'о посещаемости лекций', 'по термину за период'])
    cx = lambda y: P[0] - math.sqrt(R * R - (y - P[1]) ** 2)      # левая точка окружности на высоте y
    s.arrow([(295, 200), (cx(200), 200)], 'логин, пароль', at=(450, 186))
    s.arrow([(cx(245), 245), (295, 245)], 'JWT (access_token)', at=(450, 231))
    s.arrow([(295, 335), (cx(335), 335)], 'термин, период, limit, JWT', at=(450, 321))
    s.arrow([(cx(380), 380), (295, 380)], ['отчёт: карточки 10 студентов, % посещения,', 'период, термин в занятиях курса;',
                                           'отказ 401 / 422'], at=(450, 428))
    s.arrow([(1205, 290), (P[0] + R, 290)], ['студенты, группы, специальности,', 'курсы, лекции (тексты), расписание,',
                                              'отметки посещаемости'], at=(1045, 225))
    s.save('dfd_context', 'DFD контекст')


def dfd_level1():
    s = Svg(1840, 1180)
    s.text(920, 26, 'DFD (Йордан–Коуд), уровень 1 — процессы шлюза и сервиса ЛР №1', size=19, weight='bold')
    R = 92
    P1, P2, P3, P4, P5, P6 = (470, 250), (470, 700), (900, 470), (1360, 470), (1360, 900), (900, 960)
    E = (150, 470)
    entity(s, *E, 220, 90, 'Пользователь API')
    process(s, *P1, R, '1', ['Аутентифицировать', 'пользователя'])
    process(s, *P2, R, '2', ['Проверить JWT', 'и передать запрос'])
    process(s, *P3, R, '3', ['Найти лекции', 'с термином'])
    process(s, *P4, R, '4', ['Рассчитать', 'посещаемость', 'за период'])
    process(s, *P5, R, '5', ['Получить', 'карточки', 'студентов'])
    process(s, *P6, R, '6', ['Сформировать', 'отчёт'])
    store(s, 470, 75, 400, 'D1', 'Учётные записи шлюза (логин, роль, PBKDF2)')
    store(s, 900, 185, 380, 'D2', 'Индекс lectures (Elasticsearch)')
    store(s, 1430, 185, 520, 'D3', 'Журнал attendance (недельные партиции) и schedule')
    store(s, 1640, 1090, 330, 'D4', 'Студенты, группы, специальности')
    store(s, 1130, 1110, 340, 'D5', 'Кэш student:{id} (Redis, TTL 2 ч)')
    s.text(1430, 225, '(PostgreSQL)', size=13, color='#2f6b2f', italic=True)
    s.text(1640, 1130, '(PostgreSQL)', size=13, color='#2f6b2f', italic=True)
    # 1. вход
    s.arrow([(130, 425), (130, 235), on(P1, (130, 235), R)], 'логин, пароль', at=(250, 222))
    s.arrow([on(P1, (170, 275), R), (170, 275), (170, 425)], 'JWT', at=(260, 290))
    s.arrow([(470, 99), on(P1, (470, 99), R)], ['роль, хеш', 'пароля'], at=(530, 128), anchor='start')
    # 2. вызов отчёта
    s.arrow([(260, 455), (300, 455), (300, 660), on(P2, (300, 660), R)], ['термин, период,', 'limit, JWT'], at=(300, 560))
    s.arrow([on(P2, (230, 740), R), (230, 740), (230, 515)], ['401 /', '422'], at=(230, 640))
    s.arrow([on(P2, P3, R), on(P3, P2, R)], ['термин,', 'период, limit'], at=(690, 560))
    # 3. поиск лекций
    s.arrow([(900, 209), on(P3, (900, 209), R)], ['id лекций, курс,', 'название, фрагмент'], at=(965, 290), anchor='start')
    s.arrow([on(P3, P4, R), on(P4, P3, R)], ['id лекций,', 'период, limit'], at=(1130, 440))
    s.arrow([on(P3, P6, R), on(P6, P3, R)], ['термин в занятиях', 'курсов, фрагменты'], at=(800, 715))
    # 4. посещаемость
    s.arrow([(1360, 209), on(P4, (1360, 209), R)], ['отметки is_present', 'по лекциям периода'], at=(1425, 300), anchor='start')
    s.arrow([on(P4, P5, R), on(P5, P4, R)], ['id 10 студентов', 'с минимальным %'], at=(1370, 690), anchor='start')
    s.arrow([on(P4, P6, R), on(P6, P4, R)], ['посещено, всего, %,', 'курсы студента'], at=(1080, 720))
    # 5. карточки
    s.arrow([(1110, 1086), on(P5, (1110, 1086), R)], 'карточка (попадание)', at=(1110, 1040))
    s.arrow([on(P5, (1250, 1086), R), (1250, 1086)], ['промах: запись', 'карточки, TTL'], at=(1335, 1060), anchor='start')
    s.arrow([(1640, 1066), on(P5, (1640, 1066), R)], ['карточка', '(промах)'], at=(1560, 990))
    s.arrow([on(P5, P6, R), on(P6, P5, R)], 'карточки студентов', at=(1130, 905))
    # 6. отчёт
    s.arrow([on(P6, (150, 960), R), (150, 960), (150, 515)], ['отчёт: карточки, % посещения,', 'период, термин в занятиях курса'],
            at=(470, 960))
    s.save('dfd_level1', 'DFD уровень 1')


if __name__ == '__main__':
    c4_context(); c4_container(); dfd_context(); dfd_level1()
    print('ok')
