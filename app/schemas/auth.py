from pydantic import BaseModel, EmailStr, Field


class _BaseSchema(BaseModel):
    model_config = {"from_attributes": True}


class UserCreate(_BaseSchema):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\-]+$")
    senha: str = Field(min_length=8)


class UserLogin(_BaseSchema):
    username: str
    senha: str


class UserResponse(_BaseSchema):
    email: str
    username: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str
