"""Единый детерминированный набор данных предметной области «университет» для ПР №2 и ПР №3.

Идентификаторы — UUID v5 от естественного ключа (код группы, номер зачётки, название курса),
поэтому одна и та же сущность получает один и тот же id в PostgreSQL, Redis, MongoDB, Neo4j и
Elasticsearch при любом перезапуске генератора (требование методички ПР №3: «один и тот же ID
используется во всех хранилищах»). Случайные части (ФИО) — от фиксированного зерна.
"""
from __future__ import annotations

import random
import uuid
from datetime import date, timedelta

NS = uuid.UUID('6f1c2b0e-5d4a-4a8e-9a51-2a7b3c9d0e11')


def uid(kind: str, key: str) -> str:
    return str(uuid.uuid5(NS, f'{kind}:{key}'))


SEMESTER_START = date(2026, 2, 9)          # понедельник первой недели весеннего семестра 2026
TEACHING_WEEKS = 16

UNIVERSITY = {'id': uid('university', 'РТУ МИРЭА'), 'name': 'МИРЭА — Российский технологический университет',
              'short_name': 'РТУ МИРЭА', 'website': 'https://www.mirea.ru', 'founded_year': 1947,
              'address': '119454, г. Москва, проспект Вернадского, д. 78'}

INSTITUTES = [
    {'short_name': 'ИКБ', 'name': 'Институт кибербезопасности и цифровых технологий', 'dean': 'Андреев А.В.'},
    {'short_name': 'ИИТ', 'name': 'Институт информационных технологий', 'dean': 'Сидоров С.С.'},
]
for i in INSTITUTES:
    i['id'] = uid('institute', i['short_name'])

DEPARTMENTS = [
    {'short_name': 'КИС', 'name': 'Кафедра корпоративных информационных систем', 'institute': 'ИКБ',
     'head': 'Голубев Д.А.', 'room': 'Г-412'},
    {'short_name': 'КПИ', 'name': 'Кафедра программной инженерии', 'institute': 'ИИТ',
     'head': 'Иванов И.И.', 'room': 'А-318'},
]
for d in DEPARTMENTS:
    d['id'] = uid('department', d['short_name'])

SPECIALTIES = [
    {'code': '38.03.05', 'name': 'Бизнес-информатика', 'degree_level': 'bachelor', 'duration_years': 4,
     'prefix': 'БСБО', 'departments': [('КИС', True)]},
    {'code': '09.03.04', 'name': 'Программная инженерия', 'degree_level': 'bachelor', 'duration_years': 4,
     'prefix': 'ИКБО', 'departments': [('КПИ', True), ('КИС', False)]},
]
for s in SPECIALTIES:
    s['id'] = uid('specialty', s['code'])

# Курсы 6-го семестра (весна 2026) для групп набора 2023 года.
# (название, часов всего, лекции, практики, лабы, курс по выбору, тег спецдисциплины кафедры, ключевые термины, описание)
COURSES_SPEC = [
    ('Проектирование архитектуры ПО', 144, 32, 16, 32, False, True,
     ['микросервис', 'монолит', 'API Gateway', 'C4', 'DFD', 'масштабирование'],
     'Курс посвящён проектированию архитектуры программных систем: монолитной и микросервисной архитектуре, '
     'шлюзам API, нотациям C4 и DFD, полиглотному хранению данных и масштабированию. Студенты проектируют '
     'систему из нескольких сервисов и обосновывают выбор хранилищ.'),
    ('Большие данные и потоковая обработка', 108, 32, 0, 32, False, True,
     ['Kafka', 'CDC', 'партиционирование', 'пакетная обработка', 'потоковая обработка'],
     'Изучаются пакетная и потоковая обработка больших данных, брокер сообщений Kafka, захват изменений данных (CDC) '
     'и партиционирование таблиц и топиков. Рассматриваются задержка, пропускная способность и гарантии доставки.'),
    ('Распределённые системы', 108, 32, 16, 0, False, True,
     ['репликация', 'консистентность', 'кворум', 'очередь сообщений'],
     'Рассматриваются модели консистентности, репликация и кворумы, теорема CAP, распределённые транзакции и '
     'очереди сообщений. Разбираются отказы узлов и сетевые разделения.'),
    ('Хранилища данных и OLAP', 108, 32, 16, 0, False, True,
     ['звезда', 'снежинка', 'куб данных', 'DWH', 'медленно меняющиеся размерности'],
     'Курс о построении корпоративных хранилищ данных: схемы «звезда» и «снежинка», многомерные кубы OLAP, '
     'загрузка ETL и медленно меняющиеся измерения.'),
    ('Информационная безопасность', 72, 16, 16, 0, False, False,
     ['DMZ', 'периметр', 'аутентификация', 'JWT', 'шифрование'],
     'Основы защиты информационных систем: аутентификация и авторизация, токены JWT, шифрование данных, '
     'сегментация сети и демилитаризованная зона.'),
    ('NoSQL и полиглотное хранение', 72, 16, 0, 16, True, True,
     ['ключ-значение', 'документ', 'граф', 'полнотекстовый поиск', 'Redis', 'MongoDB', 'Neo4j'],
     'Курс по выбору о нереляционных базах данных: хранилища ключ-значение (Redis), документные (MongoDB), '
     'графовые (Neo4j) и поисковые (Elasticsearch). Разбирается, как разместить данные одной системы в нескольких '
     'хранилищах по принципу полиглотного хранения.'),
    ('Бизнес-аналитика', 72, 16, 16, 0, True, False,
     ['BI', 'дашборд', 'метрика', 'KPI'],
     'Курс по выбору о методах бизнес-аналитики: ключевые показатели эффективности, построение дашбордов, '
     'метрики продукта и визуализация данных для принятия решений.'),
]

LAST_M = ['Иванов', 'Петров', 'Смирнов', 'Кузнецов', 'Соколов', 'Лебедев', 'Козлов', 'Новиков', 'Морозов',
          'Волков', 'Алексеев', 'Павлов', 'Семёнов', 'Голубев', 'Виноградов', 'Богданов', 'Воробьёв', 'Фёдоров',
          'Михайлов', 'Беляев', 'Тарасов', 'Белов', 'Комаров', 'Орлов', 'Киселёв', 'Макаров', 'Андреев']
FIRST_M = ['Александр', 'Дмитрий', 'Максим', 'Сергей', 'Андрей', 'Алексей', 'Артём', 'Илья', 'Кирилл',
           'Михаил', 'Никита', 'Матвей', 'Роман', 'Егор', 'Иван', 'Денис', 'Евгений', 'Даниил']
FIRST_F = ['Анна', 'Мария', 'Елена', 'Дарья', 'Алина', 'Ирина', 'Екатерина', 'Полина', 'Ольга',
           'Виктория', 'Татьяна', 'Юлия', 'Ксения', 'Софья', 'Валерия', 'Вероника']
MID_M = ['Александрович', 'Дмитриевич', 'Сергеевич', 'Андреевич', 'Алексеевич', 'Иванович', 'Михайлович',
         'Николаевич', 'Павлович', 'Романович', 'Викторович', 'Олегович']
MID_F = ['Александровна', 'Дмитриевна', 'Сергеевна', 'Андреевна', 'Алексеевна', 'Ивановна', 'Михайловна',
         'Николаевна', 'Павловна', 'Романовна', 'Викторовна', 'Олеговна']
TRANSLIT = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                    ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p', 'r',
                     's', 't', 'u', 'f', 'kh', 'ts', 'ch', 'sh', 'shch', '', 'y', '', 'e', 'yu', 'ya']))


def translit(s: str) -> str:
    return ''.join(TRANSLIT.get(c, c) for c in s.lower())


# Группы: (имя, специальность, год набора, куратор, число студентов)
GROUPS_SPEC = [
    ('БСБО-01-23', '38.03.05', 2023, 'Комарова Е.В.', 25),
    ('БСБО-02-23', '38.03.05', 2023, 'Орлов П.С.', 6),
]

TEACHERS = {
    'Проектирование архитектуры ПО': 'Беляев А.Н.', 'Большие данные и потоковая обработка': 'Тарасова О.И.',
    'Распределённые системы': 'Макаров В.Г.', 'Хранилища данных и OLAP': 'Киселёва Н.П.',
    'Информационная безопасность': 'Андреев С.М.', 'NoSQL и полиглотное хранение': 'Беляев А.Н.',
    'Бизнес-аналитика': 'Фёдорова М.А.',
}
ROOMS = ['А-101', 'А-205', 'Б-310', 'В-112', 'Г-412', 'Г-415', 'Д-220']
# Слоты расписания: день недели (0 = пн) и время пары
SLOTS = [(0, '09:00', '10:30'), (0, '10:40', '12:10'), (1, '12:40', '14:10'), (2, '09:00', '10:30'),
         (3, '10:40', '12:10'), (4, '14:20', '15:50'), (4, '16:20', '17:50')]


def build(seed: int = 2026) -> dict:
    rnd = random.Random(seed)
    spec_by_code = {s['code']: s for s in SPECIALTIES}

    courses = []
    for n, (name, total, lec, pr, lab, elective, special, terms, descr) in enumerate(COURSES_SPEC):
        courses.append({
            'id': uid('course', name), 'name': name, 'specialty_code': '38.03.05',
            'specialty_id': spec_by_code['38.03.05']['id'], 'department': 'КИС', 'semester': 6,
            'total_hours': total, 'lecture_hours': lec, 'practice_hours': pr, 'lab_hours': lab,
            'is_elective': elective, 'dept_special': special, 'terms': terms, 'description': descr,
            'teacher': TEACHERS[name], 'room': ROOMS[n], 'slot': SLOTS[n],
            'tags': (['спецдисциплина кафедры'] if special else []) + (['курс по выбору'] if elective else []),
        })

    groups, students = [], []
    for g_i, (gname, scode, year, curator, count) in enumerate(GROUPS_SPEC, start=1):
        g = {'id': uid('group', gname), 'name': gname, 'specialty_code': scode,
             'specialty_id': spec_by_code[scode]['id'], 'enrollment_year': year, 'curator': curator,
             'course_year': 2026 - year}
        groups.append(g)
        used = set()
        for k in range(1, count + 1):
            card = f'23Б0{g_i}{k:02d}'
            if gname == 'БСБО-01-23' and k == 1:   # сам студент — первый в списке группы
                last, first, mid, female = 'Судовский', 'Андрей', 'Леонидович', False
            else:
                while True:
                    female = rnd.random() < 0.45
                    last = rnd.choice(LAST_M)
                    if female:
                        last = last[:-2] + 'ая' if last.endswith('ий') else last + 'а'
                    first = rnd.choice(FIRST_F if female else FIRST_M)
                    mid = rnd.choice(MID_F if female else MID_M)
                    if (last, first) not in used:
                        break
            used.add((last, first))
            students.append({
                'id': uid('student', card), 'student_card_number': card, 'group': gname, 'group_id': g['id'],
                'last_name': last, 'first_name': first, 'patronymic': mid,
                'email': f'{card.replace("Б", "b").lower()}@edu.mirea.ru',
                'phone': f'+7 9{rnd.randint(10, 99)} {rnd.randint(100, 999)}-{rnd.randint(10, 99)}-{rnd.randint(10, 99)}',
                'enrollment_date': f'{year}-09-01', 'status': 'active',
                # курсы по выбору: у каждого студента один или оба (жребий с фиксированным зерном)
                'electives': rnd.choices([['NoSQL и полиглотное хранение'], ['Бизнес-аналитика'],
                                          ['NoSQL и полиглотное хранение', 'Бизнес-аналитика']],
                                         weights=[0.45, 0.35, 0.2])[0],
                'presence_rate': round(rnd.uniform(0.55, 0.98), 2),
            })
    lectures, schedule = [], []
    for c in courses:
        weeks = c['lecture_hours'] // 2
        day, start, end = c['slot']
        for n in range(1, weeks + 1):
            lec = {'id': uid('lecture', f'{c["name"]}#{n}'), 'course_id': c['id'], 'course_name': c['name'],
                   'order_number': n, 'lecture_type': 'lecture', 'duration_minutes': 90,
                   'title': f'Лекция {n}. {c["terms"][(n - 1) % len(c["terms"])].capitalize()}'
                            if n > 1 else f'Лекция 1. Введение в дисциплину «{c["name"]}»'}
            lectures.append(lec)
            week_start = SEMESTER_START + timedelta(weeks=n - 1)
            for g in groups:
                schedule.append({
                    'id': uid('schedule', f'{lec["id"]}|{g["name"]}'), 'lecture_id': lec['id'], 'group_id': g['id'],
                    'group': g['name'], 'course_name': c['name'], 'order_number': n,
                    'scheduled_date': (week_start + timedelta(days=day)).isoformat(),
                    'week_start_date': week_start.isoformat(), 'start_time': start, 'end_time': end,
                    'classroom': c['room'], 'teacher_name': c['teacher'],
                    'status': 'completed' if week_start + timedelta(days=day) < date(2026, 6, 1) else 'scheduled'})
    return {'university': UNIVERSITY, 'institutes': INSTITUTES, 'departments': DEPARTMENTS,
            'specialties': SPECIALTIES, 'courses': courses, 'groups': groups, 'students': students,
            'lectures': lectures, 'schedule': schedule}


if __name__ == '__main__':
    ds = build()
    for k, v in ds.items():
        print(k, len(v) if isinstance(v, list) else 1)
    for s in [x for x in ds['students'] if x['group'] == 'БСБО-01-23'][:5]:
        print(s['student_card_number'], s['last_name'], s['first_name'], s['patronymic'], s['electives'])
