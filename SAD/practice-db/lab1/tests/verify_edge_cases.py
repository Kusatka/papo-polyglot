"""Граничные случаи ЛР3 на одноразовом PostgreSQL 127.0.0.1:55439.

Тест временно меняет данные и восстанавливает их в finally. Не запускать на рабочей БД.
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

dsn = os.environ['PG_DSN']
info = conninfo_to_dict(dsn)
if info.get('host') != '127.0.0.1' or info.get('port') != '55439' or info.get('user') != 'papo_test':
    raise RuntimeError('Этот тест разрешён только на изолированном кластере papo_test:55439')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.common.analytics import HOURS_SQL, hours_report


def report(group, student, course):
    rows = hours_report(group, date(2026, 2, 9), date(2026, 5, 31), 'спецдисциплина кафедры')['students_courses']
    return next((r for r in rows if r['student']['id'] == str(student) and r['course']['id'] == str(course)), None)


def main():
    with psycopg.connect(dsn, autocommit=True) as conn:
        candidate = conn.execute("""
            SELECT a.id, a.week_start_date, a.student_id, s.id, s.status, g.name, c.id
            FROM attendance a JOIN schedule s ON s.id=a.schedule_id
            JOIN student_groups g ON g.id=s.group_id
            JOIN lectures l ON l.id=s.lecture_id JOIN lecture_courses c ON c.id=l.course_id
            WHERE a.is_present AND l.lecture_type='lecture'
              AND l.tags @> ARRAY['спецдисциплина кафедры']::text[]
              AND c.is_elective AND s.status <> 'cancelled'
            ORDER BY a.id LIMIT 1
        """).fetchone()
        assert candidate, 'Для теста нужна посещённая лекция выборной спецдисциплины'
        mark_id, week, student, schedule, original_status, group, course = candidate
        baseline = report(group, student, course)
        checks = []
        original = None
        columns = None
        try:
            cursor = conn.execute('DELETE FROM attendance WHERE id=%s AND week_start_date=%s RETURNING *',
                                  (mark_id, week))
            columns = [c.name for c in cursor.description]
            original = cursor.fetchone()
            changed = report(group, student, course)
            assert changed['planned_hours'] == baseline['planned_hours']
            assert changed['attended_hours'] == baseline['attended_hours'] - 2
            checks.append('missing_mark_preserves_plan_and_removes_two_attended_hours')
        finally:
            if original:
                conn.execute(sql.SQL('INSERT INTO attendance ({}) VALUES ({})').format(
                    sql.SQL(',').join(map(sql.Identifier, columns)),
                    sql.SQL(',').join(sql.Placeholder() for _ in columns)), original)
        try:
            conn.execute("UPDATE schedule SET status='cancelled' WHERE id=%s", (schedule,))
            changed = report(group, student, course)
            assert changed['planned_hours'] == baseline['planned_hours'] - 2
            assert changed['attended_hours'] == baseline['attended_hours'] - 2
            checks.append('cancelled_class_removes_two_planned_and_attended_hours')
        finally:
            conn.execute('UPDATE schedule SET status=%s WHERE id=%s', (original_status, schedule))
        chosen_at = conn.execute('SELECT chosen_at FROM student_electives WHERE student_id=%s AND course_id=%s',
                                 (student, course)).fetchone()[0]
        try:
            conn.execute('DELETE FROM student_electives WHERE student_id=%s AND course_id=%s', (student, course))
            assert report(group, student, course) is None
            checks.append('unselected_elective_excluded_even_with_historical_marks')
        finally:
            conn.execute('INSERT INTO student_electives(student_id,course_id,chosen_at) VALUES (%s,%s,%s)',
                         (student, course, chosen_at))
        restored = report(group, student, course)
        assert restored == baseline, 'После теста данные не восстановлены'
        plan = conn.execute('EXPLAIN (FORMAT JSON) ' + HOURS_SQL,
                            dict(group_name=group, tag='спецдисциплина кафедры',
                                 date_from=date(2026, 3, 11), date_to=date(2026, 3, 18),
                                 week_from=date(2026, 3, 9))).fetchone()[0]
        def relations(node):
            result = {node['Relation Name']} if 'Relation Name' in node else set()
            for child in node.get('Plans', []):
                result.update(relations(child))
            return result
        partitions = {name for name in relations(plan[0]['Plan']) if name.startswith('attendance_')}
        assert partitions and partitions <= {'attendance_w2026_03_09', 'attendance_w2026_03_16'}, partitions
        checks.append('explain_reads_only_two_weeks_in_report_period')
        result = {'status': 'passed', 'scope': 'native PostgreSQL 18; temporary data mutations',
                  'checks': checks, 'restored': True, 'attendance_partitions': sorted(partitions)}
        output = Path(__file__).resolve().parents[1] / 'evidence' / 'verify_edge_cases.json'
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
