from typing import List

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_operation_repository, get_operation_service
from app.repositories.operation_repository import OperationRepository
from app.schemas.operation import OperationCreateDTO, OperationResponseDTO
from app.services.operation_service import OperationService

router = APIRouter(prefix="/operations", tags=["Operações"])


@router.get("", response_model=List[OperationResponseDTO])
async def list_operations(
    limit: int = Query(default=50, ge=1, le=500),
    operation_repo: OperationRepository = Depends(get_operation_repository),
):
    """Lista as operações mais recentes (abertas e fechadas)."""
    operations = await operation_repo.list_recent(limit=limit)
    return operations


@router.post("", response_model=OperationResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_operation(
    data: OperationCreateDTO,
    operation_service: OperationService = Depends(get_operation_service),
):
    """
    Confirma que o usuário entrou em um sinal, com o lote (e opcionalmente o
    preço de entrada real) informados. A partir daqui, o sistema monitora o
    preço real do par e fecha a operação sozinho quando bater TP ou SL —
    sem precisar de acesso à conta/corretora do usuário.
    """
    return await operation_service.open_from_signal(data)
