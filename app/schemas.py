from typing import Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class TenantRegister(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=120)
    tenant_slug: str = Field(pattern=r'^[a-z][a-z0-9-]{2,59}$')
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

class Login(BaseModel):
    tenant_slug: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: Literal['admin', 'member'] = 'member'

class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    role: str

class IncidentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default='', max_length=10000)
    severity: Literal['low', 'medium', 'high', 'critical'] = 'medium'

class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=10000)
    severity: Literal['low', 'medium', 'high', 'critical'] | None = None
    status: Literal['open', 'investigating', 'resolved'] | None = None

class IncidentView(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    status: str
    created_at: datetime

class TaskCreate(BaseModel):
    incident_id: int
    title: str = Field(min_length=2, max_length=160)

class TaskUpdate(BaseModel):
    status: Literal['todo', 'in_progress', 'done']

class TaskView(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    status: str
    created_at: datetime
