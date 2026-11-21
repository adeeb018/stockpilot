from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from fastapi import HTTPException
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.auth import AuthSession
from app.models.identity import Organization, OrganizationMember, Permission, Role, RolePermission, User
from app.schemas.auth import RegisterRequest, TokenResponse
DEFAULT_ADMIN_PERMISSIONS = ["product.create", "product.read", "product.update", "warehouse.create",
"warehouse.read", "warehouse.update", "inventory.read", "inventory.adjust", "inventory.reserve",
"order.create", "order.read", "order.cancel", "order.fulfill", "analytics.read", "member.manage", "role.manage"]
class AuthService:
    def __init__(self, db: AsyncSession):
        self.db, self.settings = db, get_settings()
    async def register(self, data: RegisterRequest) -> tuple[User, UUID]:
        email = str(data.email).lower()
        result = await self.db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(409, detail={"code": "EMAIL_ALREADY_EXISTS", "message": "Email already registered"})
        result = await self.db.execute(select(Organization).where(Organization.slug == data.organization_slug))
        if result.scalar_one_or_none():
            raise HTTPException(409, detail={"code": "ORGANIZATION_SLUG_TAKEN", "message": "Organization slug already exists"})
        organization = Organization(name=data.organization_name, slug=data.organization_slug)
        user = User(email=email, password_hash=hash_password(data.password), full_name=data.full_name)
        self.db.add_all([organization, user])
        await self.db.flush()
        role = Role(organization_id=organization.id, name="Owner", description="Organization owner")
        self.db.add(role)
        await self.db.flush()
        self.db.add(OrganizationMember(organization_id=organization.id, user_id=user.id, role_id=role.id))
        for code in DEFAULT_ADMIN_PERMISSIONS:
            result = await self.db.execute(select(Permission).where(Permission.code == code))
            permission = result.scalar_one_or_none()
            if permission is None:
                permission = Permission(code=code, description=f"Permission to {code.replace('.', ' ')}")
                self.db.add(permission)
                await self.db.flush()
            self.db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        await self.db.commit()
        await self.db.refresh(user)
        return user, organization.id
    async def _issue_tokens(self, user_id: UUID, organization_id: UUID,
                            session: AuthSession | None = None) -> TokenResponse:
        now = datetime.now(timezone.utc)
        access_delta, refresh_delta = timedelta(minutes=self.settings.access_token_minutes), timedelta(days=self.settings.refresh_token_days)
        refresh_jti = uuid4()
        if session is None:
            session = AuthSession(user_id=user_id, organization_id=organization_id, token_family_id=uuid4(),
                                  current_refresh_jti=str(refresh_jti), expires_at=now + refresh_delta)
            self.db.add(session)
            await self.db.flush()
        else:
            session.current_refresh_jti, session.expires_at = str(refresh_jti), now + refresh_delta
        access, _ = create_token(subject=user_id, session_id=session.id, organization_id=organization_id,
                                 token_type="access", expires_delta=access_delta)
        refresh, _ = create_token(subject=user_id, session_id=session.id, organization_id=organization_id,
                                  token_type="refresh", expires_delta=refresh_delta, jti=refresh_jti)
        await self.db.commit()
        return TokenResponse(access_token=access, refresh_token=refresh, expires_in=int(access_delta.total_seconds()))
    async def login(self, email: str, password: str, organization_id: UUID) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == email.lower(), User.is_active.is_(True)))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(401, detail={"code": "INVALID_CREDENTIALS", "message": "Email or password is incorrect"})
        result = await self.db.execute(select(OrganizationMember.id)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .where(OrganizationMember.user_id == user.id, OrganizationMember.organization_id == organization_id,
                   OrganizationMember.is_active.is_(True), Organization.is_active.is_(True)))
        if result.scalar_one_or_none() is None:
            raise HTTPException(403, detail={"code": "NOT_ORGANIZATION_MEMBER", "message": "User is not an active member of this organization"})
        return await self._issue_tokens(user.id, organization_id)
    async def refresh(self, refresh_token: str) -> TokenResponse:
        invalid = HTTPException(401, detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid"})
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise invalid
            user_id, session_id, org_id, token_jti = UUID(payload["sub"]), UUID(payload["sid"]), UUID(payload["org"]), payload["jti"]
        except (JWTError, ValueError, KeyError, TypeError):
            raise invalid
        result = await self.db.execute(select(AuthSession).where(AuthSession.id == session_id).with_for_update())
        session, now = result.scalar_one_or_none(), datetime.now(timezone.utc)
        if session is None or session.revoked_at is not None or session.expires_at <= now:
            raise invalid
        if session.user_id != user_id or session.organization_id != org_id or session.current_refresh_jti != token_jti:
            session.revoked_at = now
            await self.db.commit()
            raise invalid
        result = await self.db.execute(select(OrganizationMember.id)
            .join(User, User.id == OrganizationMember.user_id)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .where(OrganizationMember.user_id == user_id, OrganizationMember.organization_id == org_id,
                   OrganizationMember.is_active.is_(True), User.is_active.is_(True), Organization.is_active.is_(True)))
        if result.scalar_one_or_none() is None:
            session.revoked_at = now
            await self.db.commit()
            raise invalid
        return await self._issue_tokens(user_id, org_id, session)
    async def revoke_session(self, session: AuthSession) -> None:
        session.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()
