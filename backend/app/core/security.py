from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from jose import jwt
from pwdlib import PasswordHash
from app.core.config import get_settings
password_hash = PasswordHash.recommended()
def hash_password(password: str) -> str:
    return password_hash.hash(password)
def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)
def create_token(*, subject: UUID, session_id: UUID, organization_id: UUID,
                 token_type: str, expires_delta: timedelta, jti: UUID | None = None) -> tuple[str, str]:
    settings = get_settings()
    token_id = str(jti or uuid4())
    now = datetime.now(timezone.utc)
    payload = {"sub": str(subject), "sid": str(session_id), "org": str(organization_id),
               "type": token_type, "jti": token_id, "iat": int(now.timestamp()),
               "exp": int((now + expires_delta).timestamp())}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), token_id
def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
