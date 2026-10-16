"""Interfaces de los clientes. El servicio de matching depende de ESTO, no de HTTP ni de mocks."""
from typing import Protocol
from app.schemas import PerfilEstudiante, Materia, Disponibilidad, ResultadoMatch


class UsuariosClient(Protocol):
    async def obtener_perfil(self, usuario_id: int) -> PerfilEstudiante: ...
    async def listar_perfiles(self) -> list[PerfilEstudiante]: ...


class MateriasClient(Protocol):
    async def listar(self) -> list[Materia]: ...


class GruposClient(Protocol):
    async def obtener_disponibilidad(self, usuario_id: int) -> Disponibilidad | None: ...


class NotificacionesClient(Protocol):
    async def enviar(self, resultado: ResultadoMatch) -> None: ...
