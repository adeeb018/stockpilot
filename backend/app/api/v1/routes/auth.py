from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import AuthContext, get_current_context
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService
router = APIRouter(prefix="/auth", tags=["authentication"])
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user, organization_id = await AuthService(db).register(payload)
    return {"id": str(user.id), "email": user.email, "full_name": user.full_name,
            "organization_id": str(organization_id),
            "message": "Organization and owner account created"}
@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).login(payload.email, payload.password, payload.organization_id)
@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).refresh(payload.refresh_token)
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(context: AuthContext = Depends(get_current_context), db: AsyncSession = Depends(get_db)):
    await AuthService(db).revoke_session(context.session)
@router.get("/me", response_model=UserResponse)
async def me(context: AuthContext = Depends(get_current_context)):
    return UserResponse(id=context.user.id, email=context.user.email, full_name=context.user.full_name,
                        organization_id=context.organization.id, role=context.role.name,
                        permissions=sorted(context.permissions))
