from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import TokenResponseDTO, UserCreateDTO, UserLoginDTO, UserResponseDTO
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=UserResponseDTO, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreateDTO, auth_service: AuthService = Depends(get_auth_service)):
    """Cria um novo usuário do sistema."""
    user = await auth_service.register(data)
    return user


@router.post("/login", response_model=TokenResponseDTO)
async def login(data: UserLoginDTO, auth_service: AuthService = Depends(get_auth_service)):
    """Autentica o usuário e retorna um token JWT."""
    return await auth_service.login(data)


@router.get("/me", response_model=UserResponseDTO)
async def me(current_user: User = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado."""
    return current_user
