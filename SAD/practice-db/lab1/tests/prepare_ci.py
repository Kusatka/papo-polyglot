"""Создаёт окружение одноразового CI-стенда. Не заменяет существующие .env."""
import base64
import hashlib
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[2]
paths = [root / 'pr1' / '.env', root / 'lab1' / '.env']
if any(p.exists() for p in paths):
    raise RuntimeError('CI setup требует чистый checkout без существующих .env')
infrastructure = '''REDIS_PASSWORD=mypassword
MONGO_USER=admin
MONGO_PASSWORD=secret
ME_USER=admin
ME_PASSWORD=admin
NEO4J_PASSWORD=mysecretpassword
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret
POSTGRES_DB=practice_db
POSTGRES_HOST_PORT=5433
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=admin
'''
salt = secrets.token_bytes(16)
digest = hashlib.pbkdf2_hmac('sha256', b'teacher-pass', salt, 200_000)
hashed = 'pbkdf2_sha256:200000:' + base64.b64encode(salt).decode() + ':' + base64.b64encode(digest).decode()
application = f'''JWT_SECRET={secrets.token_hex(32)}
JWT_TTL_MIN=60
GATEWAY_USERS=teacher|teacher|{hashed}
LAB1_URL=http://lab1:8001
ES_URL=http://elasticsearch:9200
PG_DSN=postgresql://admin:secret@postgres:5432/university_system
REDIS_URL=redis://:mypassword@redis:6379/2
'''
paths[0].write_text(infrastructure, encoding='utf-8')
paths[1].write_text(application, encoding='utf-8')
print('Created ephemeral CI environment; JWT secret is not printed')
