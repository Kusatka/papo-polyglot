"""Независимая проверка расчёта ЛР №1.

Берёт из ответа шлюза (trace=true) идентификаторы лекций, найденных Elasticsearch, и пересчитывает
посещаемость другим SQL-запросом напрямую в PostgreSQL — без условия на партиции и без кэша. Топ-10
сервиса и пересчёт должны совпасть построчно.  Запуск: python -P tests/verify.py [термин] [с] [по]
"""
import json, subprocess, sys, urllib.parse, urllib.request
B = 'http://localhost:8000'
term, d1, d2 = (sys.argv[1:4] + ['API Gateway', '2026-02-09', '2026-05-31'][len(sys.argv[1:4]):])

tok = json.loads(urllib.request.urlopen(urllib.request.Request(
    B + '/auth/login', data=urllib.parse.urlencode({'username': 'teacher', 'password': 'teacher-pass'}).encode())).read())['access_token']
q = urllib.parse.urlencode({'term': term, 'date_from': d1, 'date_to': d2, 'trace': 'true'})
rep = json.loads(urllib.request.urlopen(urllib.request.Request(B + '/api/lab1/report?' + q,
                                                               headers={'Authorization': 'Bearer ' + tok})).read())
ids = rep['trace'][0]['details']['lecture_ids']
service = [(x['student']['student_card_number'], x['attended'], x['total'], x['attendance_pct']) for x in rep['students']]

sql = f"""
SELECT st.student_card_number || '|' || sum(CASE WHEN a.is_present THEN 1 ELSE 0 END) || '|' || count(*) || '|' ||
       round(100.0 * sum(CASE WHEN a.is_present THEN 1 ELSE 0 END) / count(*), 1)
FROM students st
JOIN attendance a ON a.student_id = st.id
JOIN schedule s   ON s.id = a.schedule_id
WHERE s.lecture_id IN ({', '.join("'" + i + "'" for i in ids)})
  AND s.scheduled_date BETWEEN '{d1}' AND '{d2}'
GROUP BY st.id, st.student_card_number
ORDER BY sum(CASE WHEN a.is_present THEN 1 ELSE 0 END)::numeric / count(*), count(*) DESC, st.id
LIMIT 10;"""
out = subprocess.run(['docker', 'exec', '-i', 'practice01-postgres', 'psql', '-U', 'admin', '-d', 'university_system',
                      '-tA'], input=sql, capture_output=True, text=True, encoding='utf-8').stdout.split()
direct = [(c, int(a), int(t), float(p)) for c, a, t, p in (r.split('|') for r in out)]
print(f'термин: {term}; период {d1}…{d2}; лекций из Elasticsearch: {len(ids)}')
print(f'{"№":>2}  {"сервис (зачётка посещ/всего %)":<34} {"прямой SQL":<34} совпадает')
ok = True
for i, (a, b) in enumerate(zip(service, direct), start=1):
    same = a == b
    ok &= same
    print(f'{i:>2}  {a[0]} {a[1]:>2}/{a[2]:<3} {a[3]:>5}%{"":13} {b[0]} {b[1]:>2}/{b[2]:<3} {b[3]:>5}%{"":13} {"да" if same else "НЕТ"}')
print('ИТОГ:', 'расчёт сервиса подтверждён' if ok and len(service) == len(direct) else 'РАСХОЖДЕНИЕ')
sys.exit(0 if ok else 1)
