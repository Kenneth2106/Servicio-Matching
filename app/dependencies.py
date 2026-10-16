"""Ensamblaje de dependencias (un solo lugar para cambiar mocks por clientes reales)."""
from functools import lru_cache

from app.clients.mock_clients import (MockGruposClient, MockMateriasClient,
                                      MockNotificacionesClient, MockUsuariosClient)
from app.services.matching_service import MatchingService
from app.store import MatchStore


@lru_cache
def get_service() -> MatchingService:
    return MatchingService(
        usuarios=MockUsuariosClient(),
        materias=MockMateriasClient(),
        grupos=MockGruposClient(),
        notificaciones=MockNotificacionesClient(),
        store=MatchStore(),
    )
