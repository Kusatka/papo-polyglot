"""Расширенный набор данных ПР №3: вся предметная область методических указаний.

Основа — dataset.build() из ПР №2: группы БСБО-01-23 / БСБО-02-23, их студенты и 7 курсов 38.03.05
сохраняются с теми же UUID и ФИО. Добавляются направление 09.03.04 (группы ИКБО-01-23, ИКБО-02-23 и их
курсы), занятия трёх типов (лекция, практика, лабораторная), материалы занятий, расписание на 16 недель
весеннего семестра 2026 года и сведения для лабораторных работ: теги занятий, требования к технике,
кафедра — владелец курса, выбор курсов студентами.
"""
from __future__ import annotations

import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataset as base  # noqa: E402
from dataset import uid  # noqa: E402

ICBO_COURSES = [
    # (название, часов, лекции, практики, лабы, по выбору, спецдисциплина кафедры, кафедра, термины, описание)
    ('Проектирование архитектуры ПО', 144, 32, 16, 32, False, True, 'КПИ',
     ['микросервис', 'монолит', 'API Gateway', 'C4', 'DFD', 'масштабирование'],
     'Принципы проектирования архитектуры программных систем: монолит и микросервисы, шлюз API, нотации C4 и DFD, '
     'выбор хранилищ данных.'),
    ('Тестирование программного обеспечения', 108, 32, 0, 32, False, True, 'КПИ',
     ['модульное тестирование', 'интеграционное тестирование', 'покрытие', 'CI/CD', 'мок-объект'],
     'Методы и уровни тестирования программ, автоматизация тестирования, непрерывная интеграция и метрики покрытия.'),
    ('Компьютерные сети', 108, 32, 16, 0, False, False, 'КПИ',
     ['TCP/IP', 'маршрутизация', 'DNS', 'HTTP', 'VLAN'],
     'Стек протоколов TCP/IP, адресация и маршрутизация, прикладные протоколы и сегментация сетей.'),
    ('Машинное обучение', 72, 16, 0, 16, True, False, 'КПИ',
     ['регрессия', 'классификация', 'признак', 'переобучение', 'нейронная сеть'],
     'Курс по выбору: постановка задач машинного обучения, модели регрессии и классификации, оценка качества.'),
    ('Разработка мобильных приложений', 72, 16, 0, 16, True, False, 'КПИ',
     ['Android', 'Kotlin', 'жизненный цикл активности', 'REST API', 'офлайн-режим'],
     'Курс по выбору: архитектура мобильного приложения, работа с сетью и локальным хранилищем.'),
]

TECH = {
    'lecture': ['Мультимедийный проектор и экран', 'Проектор, микрофон', 'Не требуется'],
    'practice': ['Компьютерный класс с доступом в Интернет, проектор', 'Интерактивная панель, ноутбуки студентов'],
    'lab': ['Компьютерный класс с ОС Linux и установленным Docker', 'Компьютерный класс, рабочие станции не менее 16 ГБ ОЗУ, Docker',
            'Компьютерный класс с IDE и доступом к серверу СУБД'],
}
MATERIAL_SENTENCES = [
    'На занятии рассматривается понятие «{term}» и его роль в современных информационных системах.',
    'Подробно разбирается, как {term} влияет на архитектуру и производительность решения.',
    'Приводятся практические примеры применения подхода «{term}» в корпоративной среде.',
    'Обсуждаются достоинства и ограничения, связанные с использованием «{term}».',
    'Студенты учатся проектировать компоненты с учётом требований к «{term}».',
    'Рассматривается связь темы «{term}» с дисциплиной «{course}» и смежными разделами.',
]
TYPE_RU = {'lecture': 'Лекция', 'practice': 'Практическое занятие', 'lab': 'Лабораторная работа'}
SLOT_TIMES = [('09:00', '10:30'), ('10:40', '12:10'), ('12:40', '14:10'), ('14:20', '15:50'), ('16:20', '17:50')]
SPECIAL_TAG = 'спецдисциплина кафедры'


def build(seed: int = 2026) -> dict:
    ds = base.build()                         # то же, что в ПР №2 (те же UUID и ФИО)
    rnd = random.Random(seed + 3)
    spec = {s['code']: s for s in base.SPECIALTIES}

    courses = []
    for c in ds['courses']:                   # курсы 38.03.05 из ПР №2 — кафедра КИС
        courses.append(dict(c, department='КИС', department_id=uid('department', 'КИС')))
    for n, (name, total, lec, pr, lab, el, special, dept, terms, descr) in enumerate(ICBO_COURSES):
        courses.append({
            'id': uid('course', f'{name}|09.03.04'), 'name': name, 'specialty_code': '09.03.04',
            'specialty_id': spec['09.03.04']['id'], 'department': dept, 'department_id': uid('department', dept),
            'semester': 6, 'total_hours': total, 'lecture_hours': lec, 'practice_hours': pr, 'lab_hours': lab,
            'is_elective': el, 'dept_special': special, 'terms': terms, 'description': descr,
            'teacher': ['Ковалёв Д.С.', 'Ильина Т.В.', 'Гусев П.А.', 'Титова Е.Н.', 'Кузьмин А.Р.'][n],
            'room': ['А-118', 'В-301', 'В-215', 'Б-104', 'Б-110'][n],
            'tags': ([SPECIAL_TAG] if special else []) + (['курс по выбору'] if el else []),
        })

    groups = list(ds['groups']) + [
        {'id': uid('group', g), 'name': g, 'specialty_code': '09.03.04', 'specialty_id': spec['09.03.04']['id'],
         'enrollment_year': 2023, 'curator': cur, 'course_year': 3}
        for g, cur in (('ИКБО-01-23', 'Ковалёв Д.С.'), ('ИКБО-02-23', 'Ильина Т.В.'))]
    students = [dict(s) for s in ds['students']]
    icbo_el = [c['name'] for c in courses if c['specialty_code'] == '09.03.04' and c['is_elective']]
    for g_i, (gname, count) in enumerate((('ИКБО-01-23', 24), ('ИКБО-02-23', 22)), start=3):
        used = set()
        for k in range(1, count + 1):
            while True:
                female = rnd.random() < 0.4
                last = rnd.choice(base.LAST_M)
                if female:
                    last = last[:-2] + 'ая' if last.endswith('ий') else last + 'а'
                first = rnd.choice(base.FIRST_F if female else base.FIRST_M)
                mid = rnd.choice(base.MID_F if female else base.MID_M)
                if (last, first) not in used:
                    break
            used.add((last, first))
            card = f'23Б0{g_i}{k:02d}'
            students.append({
                'id': uid('student', card), 'student_card_number': card, 'group': gname,
                'group_id': uid('group', gname), 'last_name': last, 'first_name': first, 'patronymic': mid,
                'email': f'{card.replace("Б", "b").lower()}@edu.mirea.ru',
                'phone': f'+7 9{rnd.randint(10, 99)} {rnd.randint(100, 999)}-{rnd.randint(10, 99)}-{rnd.randint(10, 99)}',
                'enrollment_date': '2023-09-01', 'status': 'active',
                'electives': rnd.choices([icbo_el[:1], icbo_el[1:], icbo_el], weights=[0.45, 0.35, 0.2])[0],
                'presence_rate': round(rnd.uniform(0.55, 0.98), 2)})

    # Занятия курса: лекции, практики и лабораторные в порядке номеров (чередуются по неделям)
    lectures, materials = [], []
    for c in courses:
        kinds = (['lecture'] * (c['lecture_hours'] // 2) + ['practice'] * (c['practice_hours'] // 2)
                 + ['lab'] * (c['lab_hours'] // 2))
        # равномерно перемешиваем типы: лекция обычно идёт перед практикой/лабой той же темы
        order = sorted(kinds, key=lambda k: 0)
        lec_n = sum(1 for k in kinds if k == 'lecture')
        other = [k for k in kinds if k != 'lecture']
        seq, oi = [], 0
        for i in range(lec_n):
            seq.append('lecture')
            take = round((i + 1) * len(other) / lec_n) - oi
            seq.extend(other[oi:oi + take]); oi += take
        crnd = random.Random(c['id'])
        for n, kind in enumerate(seq, start=1):
            term = c['terms'][(n - 1) % len(c['terms'])]
            title = (f'Введение в дисциплину «{c["name"]}»' if n == 1 else
                     f'{TYPE_RU[kind]}: {term}' if kind != 'lecture' else f'{term.capitalize()}: принципы и применение')
            lid = uid('lecture', f'{c["id"]}#{n}')
            special = c['dept_special'] and kind == 'lecture'
            tags = sorted({term} | ({SPECIAL_TAG} if c['dept_special'] else set()))
            text = ' '.join(crnd.choice(MATERIAL_SENTENCES).format(term=t, course=c['name'])
                            for t in [term] + crnd.sample(c['terms'], k=min(2, len(c['terms']))))
            lectures.append({
                'id': lid, 'course_id': c['id'], 'course_name': c['name'], 'specialty_code': c['specialty_code'],
                'department': c['department'], 'order_number': n, 'lecture_type': kind, 'title': title,
                'annotation': f'{TYPE_RU[kind]} по теме «{term}» курса «{c["name"]}».',
                'tech_requirements': crnd.choice(TECH[kind]), 'tags': tags, 'duration_minutes': 90,
                'content_text': text, 'teacher': c['teacher'], 'dept_special': c['dept_special'], 'special': special})
            mats = [{'type': 'text', 'title': f'Конспект: {title}', 'content_text': text}]
            if kind == 'lecture':
                mats.append({'type': 'presentation', 'title': f'Слайды к занятию {n}',
                             'file_url': f'/files/{c["id"][:8]}/lecture_{n:02d}.pdf',
                             'file_size_mb': round(crnd.uniform(0.8, 6.5), 1), 'pages': crnd.randint(15, 60)})
            if kind == 'lab':
                mats.append({'type': 'code_sample', 'title': f'Пример к работе {n}', 'language': crnd.choice(['python', 'sql', 'yaml']),
                             'code': '# заготовка кода к лабораторной работе', 'runnable': True})
            if kind == 'practice' or crnd.random() < 0.3:
                mats.append({'type': 'exercise', 'title': 'Вопросы для самопроверки',
                             'questions': [{'q': f'Что такое «{term}»?', 'difficulty': 'easy'},
                                           {'q': f'Когда применять «{term}» и когда нет?', 'difficulty': 'medium'}]})
            for m_i, m in enumerate(mats, start=1):
                materials.append(dict(m, id=uid('material', f'{lid}#{m_i}'), lecture_id=lid))

    # Расписание: занятия курса равномерно распределены по 16 неделям семестра, для каждой группы направления
    schedule = []
    days_by_course = {}
    for c_i, c in enumerate(courses):
        days_by_course[c['id']] = (c_i % 5, c_i % 4)
    for g in groups:
        g_courses = [c for c in courses if c['specialty_code'] == g['specialty_code']]
        for c in g_courses:
            ls = [x for x in lectures if x['course_id'] == c['id']]
            day, slot = days_by_course[c['id']]
            per_week = {}
            for i, lec in enumerate(ls):
                week = i * base.TEACHING_WEEKS // len(ls)
                k = per_week.get(week, 0); per_week[week] = k + 1
                ws = base.SEMESTER_START + timedelta(weeks=week)
                d = ws + timedelta(days=(day + 2 * k) % 5)
                start, end = SLOT_TIMES[(slot + k) % len(SLOT_TIMES)]
                schedule.append({
                    'id': uid('schedule', f'{lec["id"]}|{g["name"]}'), 'lecture_id': lec['id'], 'group_id': g['id'],
                    'group': g['name'], 'course_id': c['id'], 'course_name': c['name'], 'lecture_type': lec['lecture_type'],
                    'order_number': lec['order_number'], 'scheduled_date': d.isoformat(), 'week_start_date': ws.isoformat(),
                    'start_time': start, 'end_time': end,
                    'classroom': c['room'] if lec['lecture_type'] == 'lecture' else f'К-{200 + (day * 7 + slot) % 30}',
                    'teacher_name': c['teacher'],
                    'status': 'completed' if d <= date(2026, 5, 31) else 'scheduled'})

    return {'university': base.UNIVERSITY, 'institutes': base.INSTITUTES, 'departments': base.DEPARTMENTS,
            'specialties': base.SPECIALTIES, 'courses': courses, 'groups': groups, 'students': students,
            'lectures': lectures, 'materials': materials, 'schedule': schedule}


if __name__ == '__main__':
    ds = build()
    for k, v in ds.items():
        print(k, len(v) if isinstance(v, list) else 1)
    from collections import Counter
    print(Counter(x['lecture_type'] for x in ds['lectures']))
    print(Counter(x['week_start_date'] for x in ds['schedule'] if x['group'] == 'БСБО-01-23').most_common(3))
    print(min(x['scheduled_date'] for x in ds['schedule']), max(x['scheduled_date'] for x in ds['schedule']))
