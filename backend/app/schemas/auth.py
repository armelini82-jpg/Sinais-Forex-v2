from pydantic import BaseModel, EmailStr, Field


class UserCreateDTO(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLoginDTO(BaseModel):
    username: str
    password: str


class TokenResponseDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponseDTO(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True
