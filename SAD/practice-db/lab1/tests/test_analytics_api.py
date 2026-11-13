"""Локальные проверки HTTP/JWT без СУБД. SQL отдельно проверяет verify_analytics.py."""
import os
import unittest
from unittest.mock import patch

os.environ['JWT_SECRET'] = 'test-only-secret-that-is-at-least-32-bytes'

from fastapi.testclient import TestClient
from app.common.analytical_api import create_app
from app.common.security import issue_token
from app.gateway.main import app as gateway_app
import httpx


class ApiContract(unittest.TestCase):
    def setUp(self):
        self.rooms = TestClient(create_app(2))
        self.hours = TestClient(create_app(3))
        self.headers = {'Authorization': 'Bearer ' + issue_token('teacher', 'teacher')['access_token']}
        self.p2 = dict(course_id='00000000-0000-0000-0000-000000000001',
                       semester=6, study_year=3, academic_year=2025)
        self.p3 = dict(group_name='БСБО-01-23', date_from='2026-02-09', date_to='2026-05-31')

    def test_health(self):
        for client in [self.rooms, self.hours]:
            self.assertEqual(client.get('/health').status_code, 200)

    def test_auth_required(self):
        for client, params in [(self.rooms, self.p2), (self.hours, self.p3)]:
            self.assertEqual(client.get('/report', params=params).status_code, 401)
            self.assertEqual(client.get('/report', params=params,
                             headers={'Authorization': 'Bearer broken'}).status_code, 401)

    def test_room_invalid(self):
        for overrides in [dict(course_id='bad'), dict(study_year=1), dict(semester=0), dict(academic_year=0)]:
            with self.subTest(overrides=overrides):
                self.assertEqual(self.rooms.get('/report', params={**self.p2, **overrides},
                                               headers=self.headers).status_code, 422)

    def test_hours_invalid(self):
        for overrides in [dict(date_from='2027-01-01'), dict(date_to='bad'), dict(group_name=' '), dict(tag=' ')]:
            with self.subTest(overrides=overrides):
                self.assertEqual(self.hours.get('/report', params={**self.p3, **overrides},
                                               headers=self.headers).status_code, 422)

    @patch('app.common.analytical_api.rooms_report')
    def test_rooms_trace_and_user(self, calculate):
        for flag in [False, True]:
            calculate.return_value = {'classes': [], 'trace': [{'step': 1}]}
            response = self.rooms.get('/report', params={**self.p2, 'trace': flag}, headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['requested_by'], 'teacher')
            self.assertEqual('trace' in response.json(), flag)
        self.assertEqual(calculate.call_args.args[1:], (6, 3, 2025))

    @patch('app.common.analytical_api.hours_report')
    def test_hours_defaults_and_trimming(self, calculate):
        calculate.return_value = {'group': None, 'students_courses': [], 'trace': []}
        response = self.hours.get('/report', params={**self.p3, 'group_name': ' БСБО-01-23 '},
                                  headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('trace', response.json())
        self.assertEqual(calculate.call_args.args[0], 'БСБО-01-23')
        self.assertEqual(calculate.call_args.args[-1], 'спецдисциплина кафедры')

    def test_openapi(self):
        for client in [self.rooms, self.hours]:
            operation = client.get('/openapi.json').json()['paths']['/report']['get']
            self.assertTrue(operation['security'])

    @patch('app.gateway.main.httpx.get')
    def test_gateway_forwards_token_and_params(self, get):
        client = TestClient(gateway_app)
        for number, params in [(2, self.p2), (3, self.p3)]:
            get.return_value = httpx.Response(200, json={'ok': True})
            response = client.get(f'/api/lab{number}/report', params=params, headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(get.call_args.kwargs['headers'], self.headers)
            self.assertEqual(dict(get.call_args.kwargs['params']), {k: str(v) for k, v in params.items()})
            self.assertIn(f'lab{number}:800{number}', get.call_args.args[0])

    @patch('app.gateway.main.httpx.get')
    def test_gateway_unavailable(self, get):
        get.side_effect = httpx.ConnectError('test failure')
        response = TestClient(gateway_app).get('/api/lab2/report', params=self.p2, headers=self.headers)
        self.assertEqual(response.status_code, 502)

    def test_gateway_auth_required(self):
        client = TestClient(gateway_app)
        for number, params in [(2, self.p2), (3, self.p3)]:
            self.assertEqual(client.get(f'/api/lab{number}/report', params=params).status_code, 401)


if __name__ == '__main__':
    unittest.main(verbosity=2)
