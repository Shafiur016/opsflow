from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .database import Base, engine, get_db
from .models import Tenant, User, Incident, Task
from .schemas import TenantRegister, Login, Token, UserCreate, UserView, IncidentCreate, IncidentUpdate, IncidentView, TaskCreate, TaskUpdate, TaskView
from .security import access_token, hash_password, verify_password, current_user, require_admin
from . import cache, notifications

@asynccontextmanager
async def lifespan(app: FastAPI):
    # In production run `alembic upgrade head` instead of relying on create_all.
    if engine.dialect.name == 'sqlite':
        Base.metadata.create_all(engine)
    yield

app = FastAPI(title='OpsFlow | Multi-Tenant Incident Platform', version='1.0.0', lifespan=lifespan)

@app.get('/healthz')
def health():
    return {'status': 'ok'}

@app.post('/auth/register-tenant', response_model=Token, status_code=201)
def register(body: TenantRegister, db: Session = Depends(get_db)):
    if db.scalar(select(Tenant).where(Tenant.slug == body.tenant_slug)):
        raise HTTPException(409, 'Tenant slug already registered')
    tenant = Tenant(name=body.tenant_name, slug=body.tenant_slug)
    db.add(tenant)
    db.flush()
    user = User(tenant_id=tenant.id, email=str(body.email).lower(), password_hash=hash_password(body.password), role='owner')
    db.add(user)
    db.commit()
    db.refresh(user)
    return Token(access_token=access_token(user))

@app.post('/auth/login', response_model=Token)
def login(body: Login, db: Session = Depends(get_db)):
    tenant = db.scalar(select(Tenant).where(Tenant.slug == body.tenant_slug))
    user = db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == str(body.email).lower())) if tenant else None
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, 'Invalid credentials')
    return Token(access_token=access_token(user))

@app.get('/auth/me', response_model=UserView)
def me(user: User = Depends(current_user)):
    return user

@app.post('/users', response_model=UserView, status_code=201)
def add_user(body: UserCreate, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.tenant_id == user.tenant_id, User.email == str(body.email).lower())):
        raise HTTPException(409, 'User already exists in this tenant')
    created = User(tenant_id=user.tenant_id, email=str(body.email).lower(), password_hash=hash_password(body.password), role=body.role)
    db.add(created); db.commit(); db.refresh(created)
    return created

@app.post('/incidents', response_model=IncidentView, status_code=201)
def create_incident(body: IncidentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = Incident(tenant_id=user.tenant_id, **body.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item

@app.get('/incidents')
def list_incidents(status: str | None = None, severity: str | None = None,
                   limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    criteria = [Incident.tenant_id == user.tenant_id]
    if status: criteria.append(Incident.status == status)
    if severity: criteria.append(Incident.severity == severity)
    total = db.scalar(select(func.count()).select_from(Incident).where(*criteria))
    items = db.scalars(select(Incident).where(*criteria).order_by(Incident.id.desc()).offset(offset).limit(limit)).all()
    return {'total': total, 'limit': limit, 'offset': offset,
            'items': [IncidentView.model_validate(item).model_dump(mode='json') for item in items]}

def _incident(db: Session, tenant_id: int, incident_id: int) -> Incident:
    item = db.scalar(select(Incident).where(Incident.id == incident_id, Incident.tenant_id == tenant_id))
    if not item: raise HTTPException(404, 'Incident not found')
    return item

@app.get('/incidents/{incident_id}', response_model=IncidentView)
def get_incident(incident_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cached = cache.read_incident(user.tenant_id, incident_id)
    if cached:
        return cached
    data = IncidentView.model_validate(_incident(db, user.tenant_id, incident_id)).model_dump(mode='json')
    cache.write_incident(user.tenant_id, incident_id, data)
    return data

@app.patch('/incidents/{incident_id}', response_model=IncidentView)
def update_incident(incident_id: int, body: IncidentUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    incident = _incident(db, user.tenant_id, incident_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(incident, key, value)
    db.commit(); db.refresh(incident)
    cache.invalidate_incident(user.tenant_id, incident_id)
    return incident

@app.post('/tasks', response_model=TaskView, status_code=201)
def create_task(body: TaskCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _incident(db, user.tenant_id, body.incident_id)
    task = Task(tenant_id=user.tenant_id, incident_id=body.incident_id, title=body.title)
    db.add(task); db.commit(); db.refresh(task)
    notifications.enqueue_notification(user.tenant_id, task.id, task.status)
    return task

@app.get('/tasks', response_model=list[TaskView])
def list_tasks(incident_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    criteria = [Task.tenant_id == user.tenant_id]
    if incident_id is not None: criteria.append(Task.incident_id == incident_id)
    return db.scalars(select(Task).where(*criteria).order_by(Task.id.desc()).limit(100)).all()

@app.patch('/tasks/{task_id}', response_model=TaskView)
def update_task(task_id: int, body: TaskUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == user.tenant_id))
    if not task: raise HTTPException(404, 'Task not found')
    task.status = body.status
    db.commit(); db.refresh(task)
    notifications.enqueue_notification(user.tenant_id, task.id, task.status)
    return task
