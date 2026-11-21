# OpsFlow — Multi-Tenant SaaS Incident Backend

FastAPI REST API for organizations, incidents and tasks. Implements JWT login, tenant-scoped queries, owner/admin/member roles, PostgreSQL migrations, optional Redis read-through caching and Celery event notifications.

## Quick start (Python 3.11+)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# Swagger UI: http://localhost:8000/docs
pytest -q
```

Local development defaults to SQLite and disables optional Redis/Celery integrations. For the complete PostgreSQL + Redis + Celery stack:

```bash
cp .env.example .env
# Edit database password and JWT secret.
docker compose up --build
```

## Example flow

```bash
curl -X POST http://localhost:8000/auth/register-tenant -H 'Content-Type: application/json' \
  -d '{"tenant_name":"Acme","tenant_slug":"acme","email":"owner@example.com","password":"replace-with-strong-password"}'
# Copy `access_token` into TOKEN
curl -X POST http://localhost:8000/incidents -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"title":"API latency spike","severity":"high"}'
```

## Security model and limitations

- Tenant ID always comes from a signed token; request clients cannot choose a tenant for writes or reads.
- Members create/manage incidents and tasks; only owner/admin can create users.
- Salted PBKDF2-SHA256 passwords, signed 8-hour JWT, per-tenant uniqueness; secrets must be set for production.
- Demo-quality authorization: no SSO, MFA, login throttling, audit retention, invitation confirmation, nor permission limits on *individual* incidents. Add these before production deployment.
- Notifications are currently **structured worker logs**, not delivered email; `ENABLE_NOTIFICATIONS=1` requires a Celery worker. Redis cache is best-effort with 60-second TTL.
- Production infrastructure should use TLS, managed secrets, restricted network policies, monitoring and backups.

## Architecture

`API → SQLAlchemy → PostgreSQL`, with `API → Redis cache`, and `API → Redis broker → Celery worker` in Docker mode. Alembic migration `0001_initial` supplies the schema.
