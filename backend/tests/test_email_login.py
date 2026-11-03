from sqlalchemy import select
from app.models.entities import User
from test_phase2 import context, headers, PASSWORD


def test_email_identifier_registration_login_and_normalized_duplicate(context):
    client = context['client']; auth = headers(context)
    body = {'username':' Operador+Chronos@Example.Test ', 'password':PASSWORD, 'role':'admin'}
    created = client.post('/api/v1/users', headers=auth, json=body)
    assert created.status_code == 201 and created.json()['username'] == 'operador+chronos@example.test'
    assert PASSWORD not in created.text and 'password_hash' not in created.text
    token = client.post('/api/v1/auth/login', json={'organization':'horizonte', 'username':'OPERADOR+CHRONOS@EXAMPLE.TEST','password':PASSWORD})
    assert token.status_code == 200
    me = client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+token.json()['access_token']})
    assert me.status_code == 200 and me.json()['username'] == 'operador+chronos@example.test'
    assert me.json()['permissions']['users:write'] is None
    assert client.post('/api/v1/users',headers=auth,json=body|{'username':'operador+chronos@example.test'}).status_code == 409
    for name in ('invalid user@example.test', '<script>@example.test', 'x'*81):
        assert client.post('/api/v1/users', headers=auth,json=body|{'username':name}).status_code == 422
    with context['factory']() as session:
        assert len(session.scalars(select(User).where(User.username=='operador+chronos@example.test')).all()) == 1
