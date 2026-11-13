"""Ensamblaje de los clientes del servicio."""
from fastapi import Request

from app.clients.postgres_clients import (PostgresGruposClient, PostgresMateriasClient,
                                         PostgresUsuariosClient)
from app.errors import ServicioNoDisponible
from app.services.matching_service import MatchingService
from app.store import MatchStore


def get_service(request: Request) -> MatchingService:
    service = getattr(request.app.state, "matching_service", None)
    if service is None:
        raise ServicioNoDisponible(
            "base_de_datos", "Configura DATABASE_URL para habilitar el matching"
        )
    return service


def crear_service(pool) -> MatchingService:
    return MatchingService(
        usuarios=PostgresUsuariosClient(pool),
        materias=PostgresMateriasClient(pool),
        grupos=PostgresGruposClient(pool),
        store=MatchStore(),
    )
