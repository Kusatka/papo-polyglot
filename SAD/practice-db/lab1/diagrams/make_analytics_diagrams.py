"""Схемы ЛР2–3 на SVG-примитивах предыдущей работы; без внешних библиотек."""
import make_diagrams as draw
import math


class PortableSvg(draw.Svg):
    """Не полагается на SVG markers/paint-order при растеризации MuPDF."""
    def text(self, *args, **kwargs):
        kwargs['halo'] = False
        return super().text(*args, **kwargs)

    def arrow(self, pts, *args, **kwargs):
        super().arrow(pts, *args, **kwargs)
        x, y = pts[-1]
        px, py = pts[-2]
        angle = math.atan2(y - py, x - px)
        bx, by = x - 12 * math.cos(angle), y - 12 * math.sin(angle)
        dx, dy = 5 * math.sin(angle), -5 * math.cos(angle)
        self.add(f'<polygon points="{x},{y} {bx+dx},{by+dy} {bx-dx},{by-dy}" fill="#444"/>')


draw.Svg = PortableSvg


def containers():
    s = draw.Svg(1600, 850)
    s.text(800, 30, 'C4 уровень контейнеров — лабораторные работы 1–3', 22, weight='bold')
    draw.c4_box(s, 170, 220, 250, 150, 'Пользователь', '[Person]', ['Swagger UI, HTTP-клиент'], draw.C_PERSON, person=True)
    draw.boundary(s, 390, 70, 800, 710, 'Аналитическая система кафедры', '[Software System]')
    draw.c4_box(s, 790, 200, 580, 160, 'API Gateway :8000', '[Container: Python / FastAPI]',
                ['PBKDF2 → JWT; /api/lab1,2,3/report', 'Проверка JWT и маршрутизация'], draw.C_CONT)
    for x, n, desc in [(540, 1, 'Посещаемость по термину'), (790, 2, 'Вместимость аудитории'),
                       (1040, 3, 'План и посещённые часы')]:
        draw.c4_box(s, x, 510, 220, 170, f'Сервис ЛР{n}', f'[Container: FastAPI :800{n}]',
                    [desc, 'Проверка JWT'], draw.C_CONT)
        s.arrow([(x, 280), (x, 425)], 'HTTP + JWT', at=(x, 350), size=12)
    draw.c4_box(s, 1410, 510, 300, 190, 'PostgreSQL 16', '[ContainerDb]',
                ['university_system', 'Источник истины', 'Расписание и attendance'], draw.C_DB, db=True)
    s.arrow([(295, 220), (500, 220)], 'HTTP :8000', at=(390, 180))
    s.arrow([(1150, 510), (1260, 510)], 'SQL', at=(1205, 480))
    s.arrow([(790, 595), (790, 680), (1410, 680), (1410, 605)], 'SQL ЛР2', at=(1000, 655))
    s.arrow([(540, 595), (540, 720), (1500, 720), (1500, 605)], 'SQL ЛР1', at=(1010, 745))
    s.text(800, 820, 'ЛР1 также читает Elasticsearch и Redis; наружу опубликован только gateway.', 16)
    s.save('c4_analytics_container', 'C4 лабораторные 1–3')


def context(number, title, inputs, outputs):
    s = draw.Svg(1400, 540)
    s.text(700, 30, f'DFD Йордана–Коуда — контекст ЛР{number}', 22, weight='bold')
    draw.entity(s, 150, 270, 240, 170, 'Пользователь')
    draw.process(s, 700, 270, 125, '0', title)
    draw.entity(s, 1230, 270, 280, 150, ['Загрузка данных', 'кафедры ПР3'])
    s.arrow([(270, 220), (585, 220)], inputs, at=(420, 155))
    s.arrow([(585, 320), (270, 320)], outputs, at=(420, 415))
    s.arrow([(1090, 270), (825, 270)], ['Группы, студенты, курсы,', 'занятия, выбор курсов,', 'расписание и посещения'], at=(960, 180))
    s.save(f'dfd_lab{number}_context', f'Контекст ЛР{number}')


def detail(number, task, inputs, data_label, outputs):
    s = draw.Svg(1500, 800)
    s.text(750, 30, f'DFD Йордана–Коуда — уровень 1 ЛР{number}', 22, weight='bold')
    draw.entity(s, 150, 350, 240, 180, 'Пользователь')
    draw.process(s, 510, 200, 95, '1', ['Проверить пароль', 'и выдать JWT'])
    draw.process(s, 510, 520, 95, '2', ['Проверить JWT', 'и параметры'])
    draw.process(s, 950, 520, 115, '3', task)
    draw.store(s, 510, 60, 440, 'D1', 'Учётные записи (PBKDF2)')
    draw.store(s, 1180, 180, 550, 'D2', data_label)
    s.arrow([(270, 280), (415, 200)], 'Логин, пароль', at=(320, 190))
    s.arrow([(415, 230), (270, 320)], 'JWT / отказ', at=(320, 275))
    s.arrow([(510, 84), (510, 105)], 'Хеш, роль', at=(650, 115))
    s.arrow([(270, 400), (415, 520)], inputs, at=(310, 500))
    s.arrow([(605, 520), (835, 520)], ['Проверенные', 'параметры'], at=(720, 465))
    s.arrow([(1180, 204), (1005, 419)], ['Данные для', 'расчёта'], at=(1110, 310))
    s.arrow([(950, 635), (950, 720), (150, 720), (150, 440)], outputs, at=(550, 740))
    s.arrow([(445, 590), (300, 620), (240, 440)], '401 / 422', at=(305, 640))
    s.save(f'dfd_lab{number}_level1', f'Потоки ЛР{number}')


if __name__ == '__main__':
    containers()
    context(2, ['Рассчитать вместимость', 'аудитории'], ['Логин, пароль; JWT, курс,', 'семестр, годы обучения'],
            ['JWT / отказ; курс, занятия,', 'техника, слушатели, trace'])
    context(3, ['Рассчитать учебные', 'часы группы'], ['Логин, пароль; JWT,', 'группа, период, тег'],
            ['JWT / отказ; группа, студент,', 'курс, план / посещено, trace'])
    detail(2, ['Выбрать курс,', 'занятия и состав', 'слушателей'], ['JWT, курс, семестр,', 'учебный год, год обучения'],
           'PostgreSQL: курсы, занятия, группы, выбор', ['Курс, занятие, техника, число слушателей, trace'])
    detail(3, ['Посчитать план', 'и посещённые', 'часы лекций'], ['JWT, группа,', 'период, тег'],
           'PostgreSQL: студенты, расписание, attendance', ['Группа, студент, курс, плановые и посещённые часы, trace'])
    import pymupdf
    for name in ['c4_analytics_container', 'dfd_lab2_context', 'dfd_lab3_context',
                 'dfd_lab2_level1', 'dfd_lab3_level1']:
        with pymupdf.open(draw.OUT / f'{name}.svg') as document:
            document[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(draw.OUT / f'{name}.png')
    print('Created C4 and four DFD SVG/HTML/PNG')
