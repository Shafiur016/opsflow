from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app


def build_client():
    engine = create_engine('sqlite+pysqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    def override():
        with session_factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    return TestClient(app)


def register(client, slug, email):
    r = client.post('/auth/register-tenant', json={'tenant_name': slug.upper(), 'tenant_slug': slug, 'email': email, 'password': 'strong-password-123'})
    assert r.status_code == 201, r.text
    return r.json()['access_token']


def test_tenant_isolation_and_role_permissions():
    with build_client() as client:
        a = register(client, 'alpha', 'owner@example.com')
        b = register(client, 'beta', 'owner@example.com')
        headers_a = {'Authorization': 'Bearer ' + a}
        headers_b = {'Authorization': 'Bearer ' + b}
        incident = client.post('/incidents', headers=headers_a, json={'title': 'Alpha incident', 'severity': 'high'})
        assert incident.status_code == 201, incident.text
        incident_id = incident.json()['id']
        assert len(client.get('/incidents', headers=headers_b).json()['items']) == 0
        assert client.get(f'/incidents/{incident_id}', headers=headers_b).status_code == 404
        assert client.post('/tasks', headers=headers_a, json={'incident_id': incident_id, 'title': 'Investigate'}).status_code == 201
        assert client.post('/tasks', headers=headers_b, json={'incident_id': incident_id, 'title': 'Steal'}).status_code == 404
        assert client.post('/users', headers=headers_a, json={'email': 'member@alpha.io', 'password': 'member-password-123', 'role': 'member'}).status_code == 201
        member_login = client.post('/auth/login', json={'tenant_slug': 'alpha', 'email': 'member@alpha.io', 'password': 'member-password-123'})
        member = {'Authorization': 'Bearer ' + member_login.json()['access_token']}
        assert client.post('/users', headers=member, json={'email': 'x@alpha.io', 'password': 'password-12345', 'role': 'admin'}).status_code == 403
        assert client.post('/incidents', headers=member, json={'title': 'From member', 'severity': 'low'}).status_code == 201
        app.dependency_overrides.clear()


def test_auth_rejects_invalid_password_and_pagination():
    with build_client() as client:
        token = register(client, 'north', 'n@example.com')
        invalid = client.post('/auth/login', json={'tenant_slug': 'north', 'email': 'n@example.com', 'password': 'wrong-password'})
        assert invalid.status_code == 401
        headers = {'Authorization': 'Bearer ' + token}
        for i in range(3):
            assert client.post('/incidents', headers=headers, json={'title': f'Incident {i}', 'severity': 'low'}).status_code == 201
        page = client.get('/incidents?limit=2&offset=1', headers=headers).json()
        assert page['total'] == 3
        assert len(page['items']) == 2
        app.dependency_overrides.clear()


def test_token_rejection_and_tenant_scoped_updates():
    with build_client() as client:
        token_a = register(client, 'tenant-a', 'a@test.io')
        token_b = register(client, 'tenant-b', 'b@test.io')
        a = {'Authorization': 'Bearer ' + token_a}
        b = {'Authorization': 'Bearer ' + token_b}
        incident = client.post('/incidents', headers=a, json={'title': 'Private issue', 'severity': 'critical'}).json()
        assert client.patch(f"/incidents/{incident['id']}", headers=b, json={'status': 'resolved'}).status_code == 404
        assert client.patch(f"/incidents/{incident['id']}", headers=a, json={'status': 'resolved'}).json()['status'] == 'resolved'
        assert client.get('/auth/me', headers={'Authorization': '******'}).status_code == 401
        assert client.get('/incidents').status_code == 401
        app.dependency_overrides.clear()
