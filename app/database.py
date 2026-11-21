import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./opsflow.db')
options = {'connect_args': {'check_same_thread': False}} if DATABASE_URL.startswith('sqlite') else {'pool_pre_ping': True}
engine = create_engine(DATABASE_URL, **options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    with SessionLocal() as db:
        yield db
