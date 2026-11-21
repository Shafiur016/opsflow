"""Optional Redis read-through cache, scoped by tenant. Disabled unless REDIS_URL set."""
import json
import os

def _client():
    if not os.getenv('REDIS_URL'):
        return None
    try:
        import redis
        return redis.from_url(os.environ['REDIS_URL'], socket_connect_timeout=0.25, socket_timeout=0.25)
    except ImportError:
        return None

def read_incident(tenant_id: int, incident_id: int) -> dict | None:
    client = _client()
    if client is None:
        return None
    try:
        value = client.get(f'opsflow:tenant:{tenant_id}:incident:{incident_id}')
        return json.loads(value) if value else None
    except Exception:  # cache is best-effort; database remains source of truth
        return None

def write_incident(tenant_id: int, incident_id: int, data: dict):
    client = _client()
    if client:
        try:
            client.setex(f'opsflow:tenant:{tenant_id}:incident:{incident_id}', 60, json.dumps(data))
        except Exception:
            pass

def invalidate_incident(tenant_id: int, incident_id: int):
    client = _client()
    if client:
        try:
            client.delete(f'opsflow:tenant:{tenant_id}:incident:{incident_id}')
        except Exception:
            pass
