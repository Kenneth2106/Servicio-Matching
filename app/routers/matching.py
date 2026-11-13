"""Endpoints del contrato (Paso 4)."""
from fastapi import APIRouter, Depends, Path

from app.dependencies import get_service
from app.schemas import Modalidad, Nivel, RespuestaMatching
from app.services.matching_service import MatchingService

router = APIRouter(prefix="/api/v1/matching", tags=["matching"])


@router.get("/{usuario_id}", response_model=RespuestaMatching)
async def buscar_coincidencias(
    usuario_id: int = Path(gt=0),
    modalidad: Modalidad | None = None,
    nivel_minimo: Nivel | None = None,
    service: MatchingService = Depends(get_service),
):
    return await service.buscar_coincidencias(usuario_id, modalidad, nivel_minimo)
