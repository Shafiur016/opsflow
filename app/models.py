from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, UniqueConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def now_utc():
    return datetime.now(timezone.utc)

class Tenant(Base):
    __tablename__ = 'tenants'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)

class User(Base):
    __tablename__ = 'users'
    __table_args__ = (UniqueConstraint('tenant_id', 'email'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(12), default='member')

class Incident(Base):
    __tablename__ = 'incidents'
    __table_args__ = (Index('ix_incidents_tenant_status', 'tenant_id', 'status'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default='')
    severity: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(15), default='open')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class Task(Base):
    __tablename__ = 'tasks'
    __table_args__ = (Index('ix_tasks_tenant_incident', 'tenant_id', 'incident_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id'), index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey('incidents.id'))
    title: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(15), default='todo')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
