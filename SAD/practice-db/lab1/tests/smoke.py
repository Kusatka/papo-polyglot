"""Быстрая проверка ЛР №1 через шлюз: python -P tests/smoke.py [термин] [с] [по]"""
import json, sys, urllib.request, urllib.parse, urllib.error
B = 'http://localhost:8000'
term, d1, d2 = (sys.argv[1:4] + ['партиционирование', '2026-02-09', '2026-04-05'][len(sys.argv[1:4]):])


def req(path, data=None, token=None):
    h = {'Authorization': 'Bearer ' + token} if token else {}
    if data:
        data = urllib.parse.urlencode(data).encode(); h['Content-Type'] = 'application/x-www-form-urlencoded'
    try:
        with urllib.request.urlopen(urllib.request.Request(B + path, data=data, headers=h)) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


q = '/api/lab1/report?' + urllib.parse.urlencode({'term': term, 'date_from': d1, 'date_to': d2, 'trace': 'true'})
print('без токена:', req(q))
s, t = req('/auth/login', {'username': 'teacher', 'password': 'teacher-pass'})
s, r = req(q, token=t['access_token'])
print('отчёт:', s)
if s != 200:
    print(r); sys.exit(1)
print(json.dumps({k: v for k, v in r.items() if k in ('term', 'period', 'lectures_found', 'scope')}, ensure_ascii=False))
for st in r['trace']:
    print(st['step'], st['store'], '|', st['action'], '|', st['result'], '|', st['ms'], 'мс')
for x in r['students']:
    print(x['rank'], x['student']['student_card_number'], x['student']['full_name'], x['student']['group'],
          f"{x['attended']}/{x['total']}", x['attendance_pct'], x['term_in_courses'])
