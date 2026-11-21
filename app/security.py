import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User

bearer = HTTPBearer(auto_error=False)

def secret() -> str:
    value = os.getenv('JWT_SECRET')
    if not value and os.getenv('ENVIRONMENT') == 'production':
        raise RuntimeError('JWT_SECRET is required in production')
    return value or 'dev-only-change-this-secret-before-deploying'

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 420_000)
    return f'{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}'

def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_b64, digest_b64 = encoded.split('$', 1)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 420_000)
        return hmac.compare_digest(expected, actual)
    except (ValueError, TypeError):
        return False

def access_token(user: User) -> str:
    payload = {'sub': str(user.id), 'tenant_id': user.tenant_id, 'exp': datetime.now(timezone.utc) + timedelta(hours=8)}
    return jwt.encode(payload, secret(), algorithm='HS256')

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(401, 'Missing bearer token')
    try:
        payload = jwt.decode(credentials.credentials, secret(), algorithms=['HS256'])
        user_id, tenant_id = int(payload['sub']), int(payload['tenant_id'])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(401, 'Invalid or expired token')
    user = db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise HTTPException(401, 'Invalid identity')
    return user

def require_admin(user: User = Depends(current_user)) -> User:
    if user.role not in ('owner', 'admin'):
        raise HTTPException(403, 'Requires tenant administrator')
    return user
