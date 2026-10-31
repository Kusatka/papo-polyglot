"""ПР №1, самостоятельное задание 1: смена паролей во всех конфигурациях стенда и проверка служб.

  python -P selfwork/rotate_passwords.py new        перейти на пароли из selfwork/new_passwords.env
  python -P selfwork/rotate_passwords.py original   вернуть пароли методички (их используют ПР №2–3 и ЛР №1)
  python -P selfwork/rotate_passwords.py check      проверить текущие пароли без изменений

Смена в работающих службах не теряет данные: пароль меняется командой самой СУБД (ALTER USER,
changeUserPassword, ALTER CURRENT USER, CONFIG SET requirepass, пароль пользователя pgAdmin), затем новые
значения пишутся в pr1/.env и lab1/.env, и docker compose пересоздаёт контейнеры с изменённой конфигурацией.
Переменные *_INITDB_*, NEO4J_AUTH и PGADMIN_DEFAULT_* действуют только при первом запуске на пустом томе,
поэтому одной правки .env для уже инициализированных томов недостаточно.
Проверка: вход новым паролем проходит, старым — отклоняется; веб-интерфейсы и шлюз ЛР №1 работают.
"""
import http.cookiejar
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PR1 = Path(__file__).resolve().parent.parent
LAB1 = PR1.parent / 'lab1'
ORIGINAL = {'REDIS_PASSWORD': 'mypassword', 'MONGO_PASSWORD': 'secret', 'ME_PASSWORD': 'admin',
            'NEO4J_PASSWORD': 'mysecretpassword', 'POSTGRES_PASSWORD': 'secret', 'PGADMIN_PASSWORD': 'admin'}


def read_env(path):
    return {m.group(1): m.group(2) for m in re.finditer(r'^([A-Z_0-9]+)=(.*)$', path.read_text(encoding='utf-8'), re.M)}


def write_env(path, updates):
    text = path.read_text(encoding='utf-8')
    for k, v in updates.items():
        text = re.sub(rf'^{k}=.*$', f'{k}={v}', text, flags=re.M)
    path.write_text(text, encoding='utf-8')


def sh(*cmd, cwd=None):
    r = subprocess.run(list(cmd), capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd)
    return r.returncode, (r.stdout + r.stderr).strip()


def ex(container, *cmd, workdir=None):
    return sh('docker', 'exec', *(['-w', workdir] if workdir else []), container, *cmd)


def step(name, rc_out):
    rc, out = rc_out
    print(f'  {"ok " if rc == 0 else "ОШИБКА"} {name}' + ('' if rc == 0 else f': {out[-300:]}'))
    if rc != 0:
        sys.exit(1)


# ---------------------------------------------------------------- проверки входа
def chk_redis(pw):
    rc, out = ex('practice01-redis', 'redis-cli', '-a', pw, '--no-auth-warning', 'PING')
    return 'отказ: WRONGPASS' if 'WRONGPASS' in out else (out.splitlines()[-1] if out else str(rc))


def chk_pg(pw):
    # по сети Docker, как подключаются клиенты (внутри контейнера локальный вход без пароля — trust)
    rc, out = sh('docker', 'run', '--rm', '--network', 'practice01_default', 'postgres:16-alpine', 'psql',
                 f'postgresql://admin:{pw}@postgres:5432/university_system', '-tAc', 'SELECT current_user')
    return 'ok: ' + out if rc == 0 else ('отказ: password authentication failed' if 'password authentication' in out else out[-60:])


def chk_mongo(pw):
    rc, out = ex('practice01-mongodb', 'mongosh', '--quiet', '-u', 'admin', '-p', pw, '--authenticationDatabase',
                 'admin', '--eval', 'db.runCommand({ping: 1}).ok')
    return 'ok: ' + out.splitlines()[-1] if rc == 0 else 'отказ: Authentication failed'


def chk_neo4j(pw):
    rc, out = ex('practice01-neo4j', 'cypher-shell', '-u', 'neo4j', '-p', pw, '--format', 'plain', 'RETURN 1 AS ok')
    return 'ok: ' + out.splitlines()[-1] if rc == 0 else 'отказ: unauthorized'


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def chk_pgadmin(pw):
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), _NoRedirect)
    token = re.search(r'"csrfToken":\s*"([^"]+)"', op.open('http://localhost:8083/login').read().decode()).group(1)
    data = urllib.parse.urlencode({'email': 'admin@example.com', 'password': pw, 'csrf_token': token,
                                   'language': 'en', 'internal_button': 'Login'}).encode()
    try:
        op.open(urllib.request.Request('http://localhost:8083/authenticate/login', data=data))
        loc = ''
    except urllib.error.HTTPError as e:
        loc = e.headers.get('Location', '')
    return 'ok: вход, /browser/' if loc.startswith('/browser') else 'отказ: возврат на /login'


def chk_mongo_express(pw):
    rc, out = sh('curl.exe', '-s', '-u', f'admin:{pw}', '-o', 'NUL', '-w', '%{http_code}', 'http://localhost:8082/db/admin/')
    return {'200': 'ok: HTTP 200', '401': 'отказ: HTTP 401'}.get(out, out)


def chk_commander():
    rc, out = ex('practice01-redis', 'redis-cli', '-a', read_env(PR1 / '.env')['REDIS_PASSWORD'], '--no-auth-warning',
                 'CLIENT', 'LIST')
    return f'подключений redis-commander: {out.count("name=redis-commander")}'


def chk_gateway():
    b = 'http://localhost:8000'
    tok = json.loads(urllib.request.urlopen(urllib.request.Request(b + '/auth/login', data=urllib.parse.urlencode(
        {'username': 'teacher', 'password': 'teacher-pass'}).encode()), timeout=20).read())['access_token']
    q = urllib.parse.urlencode({'term': 'Kafka', 'date_from': '2026-02-09', 'date_to': '2026-05-31', 'trace': 'true'})
    r = json.loads(urllib.request.urlopen(urllib.request.Request(b + '/api/lab1/report?' + q,
                                                                 headers={'Authorization': 'Bearer ' + tok}), timeout=30).read())
    return f'отчёт: {len(r["students"])} студентов, шаги: ' + ' → '.join(t['store'] for t in r['trace'][:3])


def verify(cur, old):
    rows = [('Redis', 'redis-cli PING', chk_redis(cur['REDIS_PASSWORD']), chk_redis(old['REDIS_PASSWORD'])),
            ('PostgreSQL', 'psql по сети Docker', chk_pg(cur['POSTGRES_PASSWORD']), chk_pg(old['POSTGRES_PASSWORD'])),
            ('MongoDB', 'mongosh ping', chk_mongo(cur['MONGO_PASSWORD']), chk_mongo(old['MONGO_PASSWORD'])),
            ('Neo4j', 'cypher-shell RETURN 1', chk_neo4j(cur['NEO4J_PASSWORD']), chk_neo4j(old['NEO4J_PASSWORD'])),
            ('pgAdmin', 'вход в веб-интерфейс', chk_pgadmin(cur['PGADMIN_PASSWORD']), chk_pgadmin(old['PGADMIN_PASSWORD'])),
            ('mongo-express', 'basic auth :8082', chk_mongo_express(cur['ME_PASSWORD']), chk_mongo_express(old['ME_PASSWORD'])),
            ('Redis Commander', 'CLIENT LIST в Redis', chk_commander(), '—'),
            ('Шлюз ЛР №1', 'отчёт через PG и Redis', chk_gateway(), '—')]
    if cur == old:
        rows = [(a, b, c, '—') for a, b, c, _ in rows]
    w = [max(len(r[i]) for r in rows + [('Служба', 'Проверка', 'Текущий пароль', 'Прежний пароль')]) for i in range(4)]
    print()
    for r in [('Служба', 'Проверка', 'Текущий пароль', 'Прежний пароль')] + rows:
        print('  '.join(str(x).ljust(w[i]) for i, x in enumerate(r)))


def wait_healthy(cwd, timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        rc, out = sh('docker', 'compose', 'ps', '--format', '{{.Name}} {{.Status}}', cwd=cwd)
        bad = [l for l in out.splitlines() if '(health: starting)' in l or 'unhealthy' in l or 'Restarting' in l]
        if rc == 0 and out and not bad:
            return round(time.time() - t0)
        time.sleep(3)
    raise SystemExit(f'не дождался готовности в {cwd}: {bad}')


def rotate(target):
    cur = {k: v for k, v in read_env(PR1 / '.env').items() if k in ORIGINAL}
    if cur == target:
        print('пароли уже такие'); return cur
    print('1. Смена паролей в работающих службах:')
    step('PostgreSQL: ALTER USER admin WITH PASSWORD', ex('practice01-postgres', 'psql', '-U', 'admin', '-d', 'postgres',
         '-v', 'ON_ERROR_STOP=1', '-c', f"ALTER USER admin WITH PASSWORD '{target['POSTGRES_PASSWORD']}'"))
    step('MongoDB: changeUserPassword', ex('practice01-mongodb', 'mongosh', '--quiet', '-u', 'admin', '-p',
         cur['MONGO_PASSWORD'], '--authenticationDatabase', 'admin', '--eval',
         f"db.getSiblingDB('admin').changeUserPassword('admin', '{target['MONGO_PASSWORD']}')"))
    step('Neo4j: ALTER CURRENT USER SET PASSWORD', ex('practice01-neo4j', 'cypher-shell', '-u', 'neo4j', '-p',
         cur['NEO4J_PASSWORD'], '-d', 'system',
         f"ALTER CURRENT USER SET PASSWORD FROM '{cur['NEO4J_PASSWORD']}' TO '{target['NEO4J_PASSWORD']}'"))
    step('Redis: CONFIG SET requirepass', ex('practice01-redis', 'redis-cli', '-a', cur['REDIS_PASSWORD'],
         '--no-auth-warning', 'CONFIG', 'SET', 'requirepass', target['REDIS_PASSWORD']))
    step('pgAdmin: пароль пользователя admin@example.com',
         sh('docker', 'cp', str(Path(__file__).with_name('pgadmin_set_password.py')),
            'practice01-pgadmin:/tmp/pgadmin_set_password.py'))
    step('pgAdmin: запись нового хеша', ex('practice01-pgadmin', '/venv/bin/python3', '/tmp/pgadmin_set_password.py',
         'admin@example.com', target['PGADMIN_PASSWORD'], workdir='/pgadmin4'))
    print('2. Новые значения в конфигурации:')
    write_env(PR1 / '.env', target)
    print('  ok  pr1/.env: ' + ', '.join(target))
    write_env(LAB1 / '.env', {
        'PG_DSN': f"postgresql://admin:{target['POSTGRES_PASSWORD']}@postgres:5432/university_system",
        'REDIS_URL': f"redis://:{target['REDIS_PASSWORD']}@redis:6379/2"})
    print('  ok  lab1/.env: PG_DSN, REDIS_URL')
    print('3. Пересоздание контейнеров с изменённой конфигурацией:')
    rc, out = sh('docker', 'compose', 'up', '-d', cwd=PR1)
    changed = sorted({m for m in re.findall(r'Container (\S+)\s+Recreate', out)})
    print('  ok  стенд ПР №1, пересозданы: ' + ', '.join(c.replace('practice01-', '') for c in changed))
    print(f'  ok  все службы healthy через {wait_healthy(PR1)} с')
    sh('docker', 'compose', 'up', '-d', cwd=LAB1)
    print(f'  ok  шлюз и сервис ЛР №1 пересозданы, healthy через {wait_healthy(LAB1)} с')
    return cur


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if mode == 'check':
        cur = {k: v for k, v in read_env(PR1 / '.env').items() if k in ORIGINAL}
        verify(cur, cur)
    else:
        target = ORIGINAL if mode == 'original' else {k: v for k, v in read_env(Path(__file__).with_name(
            'new_passwords.env')).items() if k in ORIGINAL}
        old = rotate(target)
        print('4. Проверка входа:')
        verify(target, old)
