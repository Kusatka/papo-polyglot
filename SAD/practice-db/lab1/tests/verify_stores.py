"""Проверка загрузки ПР3 во все пять СУБД целевого Docker-стенда, только чтение."""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'common'))
import dataset3


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, encoding='utf-8').stdout.strip()


def main():
    # Пароли нужны только клиентам в локальном одноразовом стенде, в вывод не попадают.
    env = dict(line.split('=', 1) for line in (root / 'pr1' / '.env').read_text().splitlines()
               if line.strip() and not line.startswith('#'))
    ds = dataset3.build()
    counts = {}
    for table, key in [('students', 'students'), ('lectures', 'lectures'),
                       ('lecture_courses', 'courses'), ('schedule', 'schedule')]:
        count = int(command('docker', 'exec', 'practice01-postgres', 'psql', '-U', env['POSTGRES_USER'],
                            '-d', 'university_system', '-tA', '-v', 'ON_ERROR_STOP=1',
                            '-c', f'SELECT count(*) FROM {table}'))
        assert count == len(ds[key]), (table, count, len(ds[key]))
        counts['PostgreSQL.' + table] = count
    mongo = ['docker', 'exec', 'practice01-mongodb', 'mongosh', '--quiet', '-u', env['MONGO_USER'],
             '-p', env['MONGO_PASSWORD'], '--authenticationDatabase', 'admin', 'university_system', '--eval']
    for collection, expected in [('lecture_materials', len(ds['lectures'])), ('student_groups', len(ds['groups']))]:
        count = int(command(*mongo, f'db.{collection}.countDocuments()'))
        assert count == expected, (collection, count, expected)
        counts['MongoDB.' + collection] = count
    expected_nodes = {'University': 1, 'Institute': len(ds['institutes']), 'Department': len(ds['departments']),
                      'Specialty': len(ds['specialties']), 'LectureCourse': len(ds['courses']),
                      'Group': len(ds['groups']), 'Student': len(ds['students'])}
    for label, expected in expected_nodes.items():
        output = command('docker', 'exec', 'practice01-neo4j', 'cypher-shell', '-u', 'neo4j',
                         '-p', env['NEO4J_PASSWORD'], '--format', 'plain',
                         f'MATCH (n:{label}) RETURN count(n) AS total')
        count = int(output.splitlines()[-1])
        assert count == expected, (label, count, expected)
        counts['Neo4j.' + label] = count
    with urllib.request.urlopen('http://localhost:9200/lectures/_count', timeout=15) as response:
        count = json.load(response)['count']
    assert count == len(ds['lectures']), count
    counts['Elasticsearch.lectures'] = count
    cached = [s for s in ds['students'] if s['group'] == 'БСБО-01-23']
    for student in cached:
        value = command('docker', 'exec', 'practice01-redis', 'redis-cli', '-a', env['REDIS_PASSWORD'],
                        '--no-auth-warning', '-n', '2', '--raw', 'HGET', f'student:{student["id"]}', 'id')
        assert value == student['id'], ('Redis missing card', student['id'])
    counts['Redis.student_cards_checked'] = len(cached)
    print(json.dumps({'status': 'passed', 'counts': counts}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
