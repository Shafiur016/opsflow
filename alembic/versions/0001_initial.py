"""Initial multi-tenant schema.

Revision ID: 0001
Revises:
"""
from alembic import op
from app.database import Base
from app import models  # noqa F401
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Creation order follows foreign-key dependencies.
    bind = op.get_bind()
    for name in ['tenants', 'users', 'incidents', 'tasks']:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)

def downgrade():
    bind = op.get_bind()
    for name in ['tasks', 'incidents', 'users', 'tenants']:
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
