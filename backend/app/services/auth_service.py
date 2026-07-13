"""
Serviço de autenticação: cadastro de usuários e emissão de tokens JWT.
"""
from app.core.exceptions import AuthenticationError, ForexRadarError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponseDTO, UserCreateDTO, UserLoginDTO


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self._user_repo = user_repository

    async def register(self, data: UserCreateDTO) -> User:
        existing = await self._user_repo.get_by_username(data.username)
        if existing:
            raise ForexRadarError("Nome de usuário já está em uso.", status_code=409)

        existing_email = await self._user_repo.get_by_email(data.email)
        if existing_email:
            raise ForexRadarError("E-mail já está em uso.", status_code=409)

        user = User(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        return await self._user_repo.create(user)

    async def login(self, data: UserLoginDTO) -> TokenResponseDTO:
        user = await self._user_repo.get_by_username(data.username)
        if not user or not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Usuário ou senha inválidos.")
        if not user.is_active:
            raise AuthenticationError("Usuário inativo.")

        token = create_access_token(subject=user.username)
        return TokenResponseDTO(access_token=token)
