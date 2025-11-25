from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.saved_prompts.api.schemas import (
    CreateSavedPromptRequest,
    UpdateSavedPromptRequest,
    SavedPromptResponse,
)
from app.saved_prompts.application.use_cases.create_saved_prompt import (
    CreateSavedPromptUseCase,
)
from app.saved_prompts.application.use_cases.list_saved_prompts import (
    ListSavedPromptsUseCase,
)
from app.saved_prompts.application.use_cases.delete_saved_prompt import (
    DeleteSavedPromptUseCase,
)
from app.saved_prompts.application.use_cases.update_saved_prompt import (
    UpdateSavedPromptUseCase,
)
from app.saved_prompts.domain.repositories import SavedPromptRepository
from app.saved_prompts.infra.db.repositories import SQLModelSavedPromptRepository
from app.shared.infra.db.session import get_db
from app.shared.security.dependencies import get_current_user
from app.auth.infra.auth_service import JWTPayload


router = APIRouter(prefix="/saved-prompts", tags=["saved-prompts"])


def get_saved_prompt_repository(
    db: Session = Depends(get_db),
) -> SavedPromptRepository:
    """Dependency para obtener el repositorio de prompts guardados."""
    return SQLModelSavedPromptRepository(db)


@router.post("/", response_model=SavedPromptResponse, status_code=201)
async def create_saved_prompt(
    request: CreateSavedPromptRequest,
    repository: SavedPromptRepository = Depends(get_saved_prompt_repository),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Crea un nuevo prompt guardado para el usuario autenticado.

    Args:
        request: Datos del prompt a guardar
        repository: Repositorio de prompts (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        SavedPromptResponse: El prompt guardado con su ID
    """
    try:
        user_id = current_user["user_id"]
        use_case = CreateSavedPromptUseCase(repository)
        saved_prompt = use_case.execute(user_id, request.prompt_text)

        if saved_prompt.id is None:
            raise HTTPException(status_code=500, detail="Error: prompt guardado sin ID")

        return SavedPromptResponse(
            id=saved_prompt.id,
            user_id=saved_prompt.user_id,
            prompt_text=saved_prompt.prompt_text,
            created_at=saved_prompt.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al guardar el prompt: {str(e)}"
        )


@router.get("/", response_model=List[SavedPromptResponse])
async def list_saved_prompts(
    repository: SavedPromptRepository = Depends(get_saved_prompt_repository),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Lista todos los prompts guardados del usuario autenticado.

    Args:
        repository: Repositorio de prompts (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        List[SavedPromptResponse]: Lista de prompts guardados
    """
    try:
        user_id = current_user["user_id"]
        use_case = ListSavedPromptsUseCase(repository)
        saved_prompts = use_case.execute(user_id)

        return [
            SavedPromptResponse(
                id=prompt.id if prompt.id is not None else 0,
                user_id=prompt.user_id,
                prompt_text=prompt.prompt_text,
                created_at=prompt.created_at,
            )
            for prompt in saved_prompts
            if prompt.id is not None
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al listar los prompts: {str(e)}"
        )


@router.put("/{prompt_id}", response_model=SavedPromptResponse)
async def update_saved_prompt(
    prompt_id: int,
    request: UpdateSavedPromptRequest,
    repository: SavedPromptRepository = Depends(get_saved_prompt_repository),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Actualiza un prompt guardado del usuario autenticado.

    Args:
        prompt_id: ID del prompt a actualizar
        request: Datos con el nuevo texto del prompt
        repository: Repositorio de prompts (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        SavedPromptResponse: El prompt actualizado
    """
    try:
        user_id = current_user["user_id"]
        use_case = UpdateSavedPromptUseCase(repository)
        updated_prompt = use_case.execute(prompt_id, user_id, request.prompt_text)

        if updated_prompt.id is None:
            raise HTTPException(
                status_code=500, detail="Error: prompt actualizado sin ID"
            )

        return SavedPromptResponse(
            id=updated_prompt.id,
            user_id=updated_prompt.user_id,
            prompt_text=updated_prompt.prompt_text,
            created_at=updated_prompt.created_at,
        )
    except ValueError as e:
        # Determinar si es 404 (no existe) o 403 (no pertenece al usuario)
        error_msg = str(e)
        if "no existe" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "no pertenece al usuario" in error_msg:
            raise HTTPException(status_code=403, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al actualizar el prompt: {str(e)}"
        )


@router.delete("/{prompt_id}", status_code=204)
async def delete_saved_prompt(
    prompt_id: int,
    repository: SavedPromptRepository = Depends(get_saved_prompt_repository),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Elimina un prompt guardado del usuario autenticado.

    Args:
        prompt_id: ID del prompt a eliminar
        repository: Repositorio de prompts (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        None (204 No Content)
    """
    try:
        user_id = current_user["user_id"]
        use_case = DeleteSavedPromptUseCase(repository)
        use_case.execute(prompt_id, user_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar el prompt: {str(e)}"
        )
