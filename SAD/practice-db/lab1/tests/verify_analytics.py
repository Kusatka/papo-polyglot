"""Независимая сверка ЛР2–3: Python-циклы по снимку таблиц вместо SQL агрегатов сервиса.

Запуск с хоста: python tests/verify_analytics.py. Нужны Docker и работающий gateway.
Ничего не меняет в БД. Любая ошибка команды/HTTP/расхождение завершает тест с ошибкой.
"""
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = 'http://localhost:8000'


def api(path, params=None, token=None, data=None, expected=200):
    url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, data=data,
                                 headers={'Authorization': 'Bearer ' + token} if token else {})
    try:
        response = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as exc:
        response = exc
    assert response.code == expected, (path, response.code, response.read().decode())
    return json.load(response)


def snapshot(table):
    # Имена таблиц — константы теста, пользовательский ввод в SQL не включается.
    sql = f"SELECT coalesce(json_agg(t), '[]') FROM {table} t;"
    result = subprocess.run(['docker', 'exec', 'practice01-postgres', 'psql', '-U', 'admin',
                             '-d', 'university_system', '-tA', '-v', 'ON_ERROR_STOP=1', '-c', sql],
                            capture_output=True, text=True, encoding='utf-8', check=True)
    return json.loads(result.stdout)


def main(output_name='verify_analytics.json'):
    tables = {t: snapshot(t) for t in ('students', 'student_groups', 'lecture_courses',
                                      'lectures', 'student_electives', 'schedule', 'attendance')}
    token = api('/auth/login', data=urllib.parse.urlencode(
        {'username': 'teacher', 'password': 'teacher-pass'}).encode())['access_token']
    courses = {c['id']: c for c in tables['lecture_courses']}
    groups = {g['id']: g for g in tables['student_groups']}
    lectures = {l['id']: l for l in tables['lectures']}
    choices = {(e['student_id'], e['course_id']) for e in tables['student_electives']}
    cases = []
    for course in courses.values():
        params = dict(course_id=course['id'], semester=6, study_year=3, academic_year=2025, trace=True)
        report = api('/api/lab2/report', params, token)
        listeners = {s['id'] for s in tables['students'] if s['status'] == 'active'
                     and groups[s['group_id']]['specialty_id'] == course['specialty_id']
                     and groups[s['group_id']]['enrollment_year'] == 2023
                     and (not course['is_elective'] or (s['id'], course['id']) in choices)}
        wanted = {l['id']: len(listeners) for l in lectures.values() if l['course_id'] == course['id']}
        actual = {r['lecture']['id']: r['listeners'] for r in report['classes']}
        assert actual == wanted, ('lab2', course['name'], actual, wanted)
        assert all(r['course']['id'] == course['id'] and 'tech_requirements' in r['lecture']
                   for r in report['classes'])
        cases.append({'lab': 2, 'course': course['name'], 'classes': len(actual), 'listeners': len(listeners)})

    present = {(a['schedule_id'], a['student_id']) for a in tables['attendance'] if a['is_present']}
    for group in groups.values():
        for start, end in [('2026-02-09', '2026-05-31'), ('2026-03-11', '2026-03-18'),
                           ('2027-01-01', '2027-01-31')]:
            params = dict(group_name=group['name'], date_from=start, date_to=end, trace=True)
            report = api('/api/lab3/report', params, token)
            wanted = {}
            for student in tables['students']:
                if student['group_id'] != group['id']:
                    continue
                for course in courses.values():
                    if course['specialty_id'] != group['specialty_id']:
                        continue
                    if course['is_elective'] and (student['id'], course['id']) not in choices:
                        continue
                    lids = {l['id'] for l in lectures.values() if l['course_id'] == course['id']
                            and l['lecture_type'] == 'lecture' and 'спецдисциплина кафедры' in l['tags']}
                    if not lids:
                        continue
                    planned = {s['id'] for s in tables['schedule'] if s['lecture_id'] in lids
                               and s['group_id'] == group['id'] and s['status'] != 'cancelled'
                               and start <= s['scheduled_date'] <= end}
                    attended = {sid for sid in planned if (sid, student['id']) in present}
                    wanted[(student['id'], course['id'])] = (2 * len(planned), 2 * len(attended))
            actual = {(r['student']['id'], r['course']['id']): (r['planned_hours'], r['attended_hours'])
                      for r in report['students_courses']}
            assert actual == wanted, ('lab3', group['name'], start)
            assert report['group']['id'] == group['id']
            cases.append({'lab': 3, 'group': group['name'], 'from': start, 'to': end, 'rows': len(actual)})

    p2 = dict(course_id=next(iter(courses)), semester=6, study_year=3, academic_year=2025)
    p3 = dict(group_name='БСБО-01-23', date_from='2026-02-09', date_to='2026-05-31')
    for number, params in [(2, p2), (3, p3)]:
        api(f'/api/lab{number}/report', params, expected=401)
        api(f'/api/lab{number}/report', params, 'invalid-token', expected=401)
    api('/api/lab2/report', {**p2, 'course_id': 'bad'}, token, expected=422)
    api('/api/lab2/report', {**p2, 'study_year': 1}, token, expected=422)
    api('/api/lab3/report', {**p3, 'date_from': '2027-01-01'}, token, expected=422)
    empty = api('/api/lab3/report', {**p3, 'group_name': 'unknown'}, token)
    assert empty['group'] is None and empty['students_courses'] == []
    empty = api('/api/lab3/report', {**p3, 'tag': 'unknown'}, token)
    assert empty['students_courses'] == []
    result = {'status': 'passed', 'method': 'Python loops over database snapshot', 'cases': cases,
              'negative_checks': 9}
    output = Path(__file__).resolve().parents[1] / 'evidence' / output_name
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
