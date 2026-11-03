import base64
import csv
import hashlib
import io
import json

from sqlalchemy import func, select
from app.models.entities import AuditLog, Department, Employee, JobRole, Organization, OutboxEvent, Role, Unit, UserRole
from app.services import people_exports
from app.services.seed import demo_id
from test_phase2 import context, headers, user_for


def unpack(response):
    assert response.status_code == 200, response.text
    result = response.json()
    content = base64.b64decode(result['content'], validate=True)
    assert content.startswith(b'\xef\xbb\xbf')
    assert len(content) == result['byte_length']
    assert hashlib.sha256(content).hexdigest() == result['sha256']
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline=''))
    assert reader.fieldnames == list(people_exports.COLUMNS)
    rows = list(reader)
    assert len(rows) == result['row_count']
    return result, rows


def test_people_export_matches_all_pages_filters_order_and_audit(context):
    user_for(context, 'directory-reader', 'manager')
    auth = headers(context, 'directory-reader'); client = context['client']
    with context['factory'].begin() as s:
        person = s.get(Employee, demo_id('hh-0001'))
        person.name = ' =SUM(1,2), Pessoa fictícia\nAção'
        person.status = 'inactive'
        department = person.department_id
        initial_events = s.scalar(select(func.count()).select_from(OutboxEvent))
    for selection in ({}, {'department_id': department, 'sort': 'registration', 'descending': True},
                      {'search': 'SUM(1,2)', 'status': 'inactive'}, {'search': 'sem-resultado-1042'}):
        result, rows = unpack(client.post('/api/v1/employees/export', headers=auth, json=selection))
        expected = []
        page = 1
        while True:
            response = client.get('/api/v1/employees', headers=auth, params=selection | {'page_number': page, 'page_size': 100})
            assert response.status_code == 200
            data = response.json(); expected.extend(data['items'])
            if len(expected) >= data['total']:
                break
            page += 1
        assert [r['id'] for r in rows] == [r['id'] for r in expected]
        for row, source in zip(rows, expected):
            assert row['registration'] == source['registration']
            assert row['name'] == ("'" + source['name'] if source['name'].startswith(' =') else source['name'])
        assert 'base_salary_cents' not in result['columns'] and 'preferences' not in result['columns']
        assert 'evidence' not in result['columns'] and 'validation_status' not in result['columns']
        with context['factory']() as s:
            record = s.scalar(select(AuditLog).where(AuditLog.entity_id == result['export_id']))
            assert record.action == 'people.export' and record.actor_id
            assert record.details['sha256'] == result['sha256'] and record.details['row_count'] == len(rows)
            assert record.details['search_used'] == bool(selection.get('search'))
            assert 'SUM' not in json.dumps(record.details) and 'Ação' not in json.dumps(record.details, ensure_ascii=False)
            assert s.scalar(select(func.count()).select_from(OutboxEvent)) == initial_events
    assert unpack(client.post('/api/v1/employees/export', headers=auth, json={}))[0]['row_count'] == 350


def test_people_export_enforces_tenant_and_own_permission_unit_scope(context):
    user_id = user_for(context, 'scoped-export', 'manager', demo_id('horizonte-main'))
    with context['factory'].begin() as s:
        other = Unit(organization_id=context['org'], name='Unidade fora do escopo'); s.add(other); s.flush()
        dept = Department(organization_id=context['org'], unit_id=other.id, name='Outro setor', group='Operações'); s.add(dept); s.flush()
        s.add(Employee(organization_id=context['org'], unit_id=other.id, department_id=dept.id, job_role_id=demo_id('director'), name='Pessoa restrita', registration='RESTRITA'))
        analyst = s.scalar(select(Role).where(Role.name == 'analyst'))
        s.add(UserRole(organization_id=context['org'], user_id=user_id, role_id=analyst.id))
        org = Organization(slug='export-other', name='Organização fictícia externa', segment='services'); s.add(org); s.flush()
        foreign = Unit(organization_id=org.id, name='Unidade de outra organização'); s.add(foreign); s.flush()
        fd = Department(organization_id=org.id, unit_id=foreign.id, name='Setor externo', group='Operações')
        role = JobRole(organization_id=org.id, name='Função externa'); s.add_all([fd, role]); s.flush()
        s.add(Employee(organization_id=org.id, unit_id=foreign.id, department_id=fd.id, job_role_id=role.id, name='Outra organização', registration='TENANT'))
        other_id, foreign_id = other.id, foreign.id
    auth = headers(context, 'scoped-export'); client = context['client']
    assert client.get('/api/v1/units', headers=auth).json()['total'] == 2
    result, rows = unpack(client.post('/api/v1/employees/export', headers=auth, json={}))
    assert result['row_count'] == 350
    assert {r['unit_id'] for r in rows} == {demo_id('horizonte-main')}
    for unit in (other_id, foreign_id):
        assert unpack(client.post('/api/v1/employees/export', headers=auth, json={'unit_id': unit}))[1] == []
    admin_result, admin_rows = unpack(client.post('/api/v1/employees/export', headers=headers(context), json={}))
    assert admin_result['row_count'] == 351 and 'TENANT' not in {r['registration'] for r in admin_rows}


def test_people_export_rejects_unauthorized_and_unsupported_fields(context):
    client = context['client']
    assert client.post('/api/v1/employees/export', json={}).status_code == 401
    for role in ('demo', 'finance', 'analyst'):
        user_for(context, 'no-export-'+role, role)
        assert client.post('/api/v1/employees/export', headers=headers(context, 'no-export-'+role), json={}).status_code == 403
    auth = headers(context)
    for selection in ({'include_salary': True}, {'organization_id': 'other'}, {'page_size': 15},
                      {'sort': '__dict__'}, {'status': 'all'}, {'search': 'x'*121}, {'unit_id': ''}):
        assert client.post('/api/v1/employees/export', headers=auth, json=selection).status_code == 422


def test_people_export_limits_fail_without_partial_file_or_success_audit(context, monkeypatch):
    client = context['client']; auth = headers(context)
    monkeypatch.setattr(people_exports, 'MAX_ROWS', 2)
    response = client.post('/api/v1/employees/export', headers=auth, json={})
    assert response.status_code == 422 and response.json()['code'] == 'PEOPLE_EXPORT_LIMIT'
    assert 'content' not in response.json()
    monkeypatch.setattr(people_exports, 'MAX_ROWS', 20000)
    monkeypatch.setattr(people_exports, 'MAX_BYTES', 50)
    response = client.post('/api/v1/employees/export', headers=auth, json={})
    assert response.status_code == 422 and 'content' not in response.json()
    with context['factory']() as s:
        assert s.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == 'people.export')) == 0
    monkeypatch.setattr(people_exports, 'MAX_BYTES', 8*1024*1024)
    assert unpack(client.post('/api/v1/employees/export', headers=auth, json={}))[0]['row_count'] == 350
