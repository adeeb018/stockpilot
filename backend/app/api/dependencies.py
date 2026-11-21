from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import decode_token
from app.models.auth import AuthSession
from app.models.identity import Organization, OrganizationMember, Role, RolePermission, Permission, User
bearer_scheme = HTTPBearer(auto_error=False)
@dataclass
class AuthContext:
    user: User
    organization: Organization
    membership: OrganizationMember
    role: Role
    permissions: set[str]
    session: AuthSession
async def get_current_context(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
                              db: AsyncSession = Depends(get_db)) -> AuthContext:
    unauthorized = HTTPException(401, detail={"code": "INVALID_AUTHENTICATION", "message": "Invalid or expired credentials"},
                                 headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise unauthorized
        user_id, session_id, organization_id = UUID(payload["sub"]), UUID(payload["sid"]), UUID(payload["org"])
    except (JWTError, ValueError, KeyError, TypeError):
        raise unauthorized
    result = await db.execute(select(AuthSession).where(
        AuthSession.id == session_id, AuthSession.user_id == user_id,
        AuthSession.organization_id == organization_id, AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > datetime.now(timezone.utc)))
    session = result.scalar_one_or_none()
    if session is None:
        raise unauthorized
    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None:
        raise unauthorized
    result = await db.execute(select(OrganizationMember, Organization, Role)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .where(OrganizationMember.user_id == user_id, OrganizationMember.organization_id == organization_id,
               OrganizationMember.is_active.is_(True), Organization.is_active.is_(True)))
    row = result.one_or_none()
    if row is None:
        raise unauthorized
    membership, organization, role = row
    result = await db.execute(select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id))
    return AuthContext(user, organization, membership, role, set(result.scalars().all()), session)
def require_permission(permission_code: str):
    async def dependency(context: AuthContext = Depends(get_current_context)) -> AuthContext:
        if permission_code not in context.permissions:
            raise HTTPException(403, detail={"code": "PERMISSION_DENIED", "message": "Insufficient permissions"})
        return context
    return dependency
