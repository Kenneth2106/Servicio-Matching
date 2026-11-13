"""Clientes de lectura para el esquema PostgreSQL compartido."""
import asyncio
import logging
import unicodedata
from typing import Any

import asyncpg

from app.errors import ServicioNoDisponible, UsuarioNoEncontrado
from app.schemas import Disponibilidad, FranjaDisponibilidad, Materia, Nivel, PerfilEstudiante

log = logging.getLogger("matching")

_NIVELES: dict[str, Nivel] = {
    "basico": "principiante",
    "principiante": "principiante",
    "intermedio": "intermedio",
    "avanzado": "avanzado",
}


class _PostgresClient:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def _fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        try:
            async with self.pool.acquire() as connection:
                return await connection.fetch(query, *args)
        except (asyncpg.PostgresError, OSError, asyncio.TimeoutError) as exc:
            log.exception("Error consultando PostgreSQL")
            raise ServicioNoDisponible("base_de_datos") from exc


def _normalizar_nivel(nivel: str) -> Nivel:
    normalizado = unicodedata.normalize("NFD", nivel.strip().lower())
    normalizado = "".join(
        caracter for caracter in normalizado
        if unicodedata.category(caracter) != "Mn"
    )
    try:
        return _NIVELES[normalizado]
    except KeyError as exc:
        raise ServicioNoDisponible(
            "base_de_datos", f"Nivel no reconocido en usuario_materia: {nivel}"
        ) from exc


def _construir_perfiles(rows: list[asyncpg.Record]) -> list[PerfilEstudiante]:
    perfiles: dict[int, dict[str, Any]] = {}
    for row in rows:
        usuario_id = row["usuario_id"]
        perfil = perfiles.setdefault(usuario_id, {
            "usuario_id": usuario_id,
            "nombre": row["nombre"],
            "habilidades_ofrece": [],
            "habilidades_necesita": [],
            "niveles_habilidades": {},
        })
        materia_id = row["materia_id"]
        if materia_id is None:
            continue
        tipo = row["tipo"]
        if tipo == "ofrece":
            perfil["habilidades_ofrece"].append(materia_id)
        elif tipo == "necesita":
            perfil["habilidades_necesita"].append(materia_id)
        if tipo in ("ofrece", "necesita") and row["nivel"]:
            perfil["niveles_habilidades"][materia_id] = _normalizar_nivel(row["nivel"])
    return [PerfilEstudiante(**perfil) for perfil in perfiles.values()]


_PERFILES_QUERY = """
    SELECT u.usuario_id,
           concat_ws(' ', u.nombre, u.apellido) AS nombre,
           um.materia_id,
           um.tipo,
           um.nivel
    FROM public.usuarios AS u
    LEFT JOIN public.usuario_materia AS um ON um.usuario_id = u.usuario_id
    {where_clause}
    ORDER BY u.usuario_id, um.materia_id
"""


class PostgresUsuariosClient(_PostgresClient):
    async def obtener_perfil(self, usuario_id: int) -> PerfilEstudiante:
        query = _PERFILES_QUERY.format(where_clause="WHERE u.usuario_id = $1")
        rows = await self._fetch(query, usuario_id)
        if not rows:
            raise UsuarioNoEncontrado(f"El usuario {usuario_id} no existe")
        return _construir_perfiles(rows)[0]

    async def listar_perfiles(self) -> list[PerfilEstudiante]:
        query = _PERFILES_QUERY.format(where_clause="")
        return _construir_perfiles(await self._fetch(query))


class PostgresMateriasClient(_PostgresClient):
    async def listar(self) -> list[Materia]:
        rows = await self._fetch("""
            SELECT DISTINCT ON (materia_id) materia_id, nombre, carrera
            FROM public.materias
            ORDER BY materia_id, id
        """)
        return [
            Materia(
                materia_id=row["materia_id"],
                nombre=row["nombre"],
                categoria=row["carrera"],
            )
            for row in rows
        ]


class PostgresGruposClient(_PostgresClient):
    async def obtener_disponibilidad(self, usuario_id: int) -> Disponibilidad | None:
        rows = await self._fetch("""
            SELECT dia_semana, hora_inicio, hora_fin, modalidad
            FROM public.disponibilidad
            WHERE usuario_id = $1
            ORDER BY dia_semana, hora_inicio, disponibilidad_id
        """, usuario_id)
        if not rows:
            return None
        return Disponibilidad(
            usuario_id=usuario_id,
            franjas=[
                FranjaDisponibilidad(
                    dia_semana=row["dia_semana"],
                    hora_inicio=row["hora_inicio"],
                    hora_fin=row["hora_fin"],
                    modalidad=row["modalidad"],
                )
                for row in rows
            ],
        )
