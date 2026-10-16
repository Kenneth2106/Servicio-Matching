"""Almacenamiento EN MEMORIA de los matches calculados.

No hay base de datos (la hace otro grupo). Cuando exista, solo se reemplaza esta clase
manteniendo los mismos métodos (guardar / obtener).
"""
from dataclasses import dataclass


@dataclass
class MatchGuardado:
    match_id: int
    usuario_id: int
    usuario_match_id: int
    habilidad_id: int
    habilidad: str
    criterios: dict
    porcentaje_match: float
    compatibilidad_parcial: bool


class MatchStore:
    def __init__(self) -> None:
        self._por_id: dict[int, MatchGuardado] = {}
        self._por_clave: dict[tuple[int, int, int], int] = {}
        self._ultimo_id = 100

    def guardar(self, *, usuario_id, usuario_match_id, habilidad_id, habilidad,
                criterios, porcentaje_match, compatibilidad_parcial) -> tuple[MatchGuardado, bool]:
        """Devuelve (match, es_nuevo). Si la pareja+habilidad ya existía, reutiliza el match_id."""
        clave = (usuario_id, usuario_match_id, habilidad_id)
        if clave in self._por_clave:
            m = self._por_id[self._por_clave[clave]]
            m.criterios = criterios
            m.porcentaje_match = porcentaje_match
            m.compatibilidad_parcial = compatibilidad_parcial
            return m, False
        self._ultimo_id += 1
        m = MatchGuardado(self._ultimo_id, usuario_id, usuario_match_id, habilidad_id,
                          habilidad, criterios, porcentaje_match, compatibilidad_parcial)
        self._por_id[m.match_id] = m
        self._por_clave[clave] = m.match_id
        return m, True

    def obtener(self, match_id: int) -> MatchGuardado | None:
        return self._por_id.get(match_id)
