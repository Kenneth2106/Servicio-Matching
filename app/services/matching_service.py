"""Lógica de negocio del matching."""
import logging
import unicodedata

from app.clients.base import UsuariosClient, MateriasClient, GruposClient
from app.errors import ServicioNoDisponible, SinCoincidencias
from app.schemas import (Coincidencia, Disponibilidad, FranjaDisponibilidad, Nivel,
                         PerfilEstudiante, RespuestaMatching)
from app.store import MatchStore

log = logging.getLogger("matching")

ORDEN_NIVEL: dict[Nivel, int] = {"principiante": 1, "intermedio": 2, "avanzado": 3}


def _normalizar_dia(dia: str) -> str:
    """'Miércoles' y 'miercoles' deben ser el mismo día."""
    sin_tildes = unicodedata.normalize("NFD", dia.strip().lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")


def _nivel_para_habilidad(perfil: PerfilEstudiante, habilidad_id: int) -> Nivel | None:
    return perfil.niveles_habilidades.get(habilidad_id, perfil.nivel)


def _franjas_se_solapan(a: FranjaDisponibilidad, b: FranjaDisponibilidad) -> bool:
    return (
        _normalizar_dia(a.dia_semana) == _normalizar_dia(b.dia_semana)
        and a.hora_inicio < b.hora_fin
        and b.hora_inicio < a.hora_fin
    )


def evaluar_criterios(solicitante: PerfilEstudiante, candidato: PerfilEstudiante,
                      habilidad_id: int,
                      disp_sol: Disponibilidad | None, disp_can: Disponibilidad | None,
                      usar_disponibilidad: bool) -> dict:
    """Cada criterio vale lo mismo. None = no evaluado (Grupos caído)."""
    criterios: dict[str, bool | None] = {
        "habilidad": (habilidad_id in candidato.habilidades_ofrece
                      and habilidad_id in solicitante.habilidades_necesita),
        # Un tutor debe tener nivel igual o superior al de quien aprende.
        "nivel": bool(
            _nivel_para_habilidad(solicitante, habilidad_id)
            and _nivel_para_habilidad(candidato, habilidad_id)
            and ORDEN_NIVEL[_nivel_para_habilidad(candidato, habilidad_id)]
            >= ORDEN_NIVEL[_nivel_para_habilidad(solicitante, habilidad_id)]
        ),
        "disponibilidad": None,
        "modalidad": None,
    }
    if usar_disponibilidad:
        if disp_sol and disp_can:
            franjas_comunes = [
                (franja_sol, franja_can)
                for franja_sol in disp_sol.franjas
                for franja_can in disp_can.franjas
                if _franjas_se_solapan(franja_sol, franja_can)
            ]
            criterios["disponibilidad"] = bool(franjas_comunes)
            criterios["modalidad"] = any(
                franja_sol.modalidad is not None
                and franja_sol.modalidad == franja_can.modalidad
                for franja_sol, franja_can in franjas_comunes
            )
        else:  # falta el registro de alguno: no hay coincidencia horaria posible
            criterios["disponibilidad"] = False
            criterios["modalidad"] = False
    return criterios


def calcular_porcentaje(criterios: dict) -> float:
    evaluados = [v for v in criterios.values() if v is not None]
    return round(sum(evaluados) / len(evaluados) * 100, 2)


class MatchingService:
    def __init__(self, usuarios: UsuariosClient, materias: MateriasClient,
                 grupos: GruposClient, store: MatchStore):
        self.usuarios = usuarios
        self.materias = materias
        self.grupos = grupos
        self.store = store

    async def buscar_coincidencias(self, usuario_id: int, modalidad: str | None = None,
                                   nivel_minimo: str | None = None) -> RespuestaMatching:
        # Paso 9: Usuarios y Materias son imprescindibles -> si fallan, 503
        solicitante = await self.usuarios.obtener_perfil(usuario_id)  # 404 si no existe
        candidatos = await self.usuarios.listar_perfiles()
        catalogo = {m.materia_id: m for m in await self.materias.listar()}

        # Paso 9: Grupos es opcional -> si falla, compatibilidad parcial
        disponibilidades: dict[int, Disponibilidad | None] = {}
        parcial = False
        try:
            for p in [solicitante, *candidatos]:
                if p.usuario_id not in disponibilidades:
                    disponibilidades[p.usuario_id] = await self.grupos.obtener_disponibilidad(p.usuario_id)
        except ServicioNoDisponible:
            log.warning("Grupos no disponible: se calcula solo por habilidad")
            parcial = True

        encontrados = []
        for habilidad_id in solicitante.habilidades_necesita:
            if habilidad_id not in catalogo:  # habilidad fuera del catálogo: se ignora
                continue
            for cand in candidatos:
                if cand.usuario_id == solicitante.usuario_id:
                    continue
                if habilidad_id not in cand.habilidades_ofrece:
                    continue
                nivel_candidato = _nivel_para_habilidad(cand, habilidad_id)
                if nivel_minimo and not (nivel_candidato and
                                         ORDEN_NIVEL[nivel_candidato] >= ORDEN_NIVEL[nivel_minimo]):
                    continue
                disp_can = disponibilidades.get(cand.usuario_id)
                # Si Grupos está caído no se puede filtrar por modalidad
                if modalidad and not parcial and not (
                    disp_can and any(f.modalidad == modalidad for f in disp_can.franjas)
                ):
                    continue
                criterios = evaluar_criterios(solicitante, cand, habilidad_id,
                                              disponibilidades.get(solicitante.usuario_id),
                                              disp_can, usar_disponibilidad=not parcial)
                encontrados.append((calcular_porcentaje(criterios), cand, habilidad_id))

        if not encontrados:
            raise SinCoincidencias(f"El usuario {usuario_id} no tiene coincidencias")

        # Mayor a menor porcentaje; desempate estable por usuario_id
        encontrados.sort(key=lambda t: (-t[0], t[1].usuario_id))

        coincidencias = []
        for porcentaje, cand, habilidad_id in encontrados:
            match_id = self.store.obtener_o_crear(
                usuario_id, cand.usuario_id, habilidad_id)
            coincidencias.append(Coincidencia(
                match_id=match_id, usuario_match_id=cand.usuario_id,
                nombre_match=cand.nombre, habilidad=catalogo[habilidad_id].nombre,
                porcentaje_match=porcentaje, compatibilidad_parcial=parcial))

        return RespuestaMatching(usuario_id=usuario_id, coincidencias=coincidencias)
