from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=150)
    organization_slug: str = Field(min_length=3, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    organization_id: UUID
class RefreshRequest(BaseModel):
    refresh_token: str
class TokenResponse(BaseModel):
    token_type: str = "bearer"
    access_token: str
    refresh_token: str
    expires_in: int
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    organization_id: UUID
    role: str
    permissions: list[str]
