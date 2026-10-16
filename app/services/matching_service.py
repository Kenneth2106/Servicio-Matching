"""Lógica de negocio del matching."""
import logging
import unicodedata

from app.clients.base import UsuariosClient, MateriasClient, GruposClient, NotificacionesClient
from app.errors import ServicioNoDisponible, SinCoincidencias, MatchNoEncontrado
from app.schemas import (Coincidencia, Criterios, DetalleMatch, Disponibilidad,
                         PerfilEstudiante, RespuestaMatching, ResultadoMatch)
from app.store import MatchStore

log = logging.getLogger("matching")

ORDEN_NIVEL = {"principiante": 1, "intermedio": 2, "avanzado": 3}


def _normalizar_dia(dia: str) -> str:
    """'Miércoles' y 'miercoles' deben ser el mismo día."""
    sin_tildes = unicodedata.normalize("NFD", dia.strip().lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")


def evaluar_criterios(solicitante: PerfilEstudiante, candidato: PerfilEstudiante,
                      habilidad_id: int,
                      disp_sol: Disponibilidad | None, disp_can: Disponibilidad | None,
                      usar_disponibilidad: bool) -> dict:
    """Cada criterio vale lo mismo. None = no evaluado (Grupos caído)."""
    criterios: dict[str, bool | None] = {
        "habilidad": (habilidad_id in candidato.habilidades_ofrece
                      and habilidad_id in solicitante.habilidades_necesita),
        # Un tutor debe tener nivel igual o superior al de quien aprende.
        "nivel": bool(solicitante.nivel and candidato.nivel
                      and ORDEN_NIVEL[candidato.nivel] >= ORDEN_NIVEL[solicitante.nivel]),
        "disponibilidad": None,
        "modalidad": None,
    }
    if usar_disponibilidad:
        if disp_sol and disp_can:
            dias_a = {_normalizar_dia(d) for d in disp_sol.dias_disponibles}
            dias_b = {_normalizar_dia(d) for d in disp_can.dias_disponibles}
            criterios["disponibilidad"] = bool(dias_a & dias_b)
            criterios["modalidad"] = disp_sol.modalidad == disp_can.modalidad
        else:  # falta el registro de alguno: no hay coincidencia horaria posible
            criterios["disponibilidad"] = False
            criterios["modalidad"] = False
    return criterios


def calcular_porcentaje(criterios: dict) -> float:
    evaluados = [v for v in criterios.values() if v is not None]
    return round(sum(evaluados) / len(evaluados) * 100, 2)


class MatchingService:
    def __init__(self, usuarios: UsuariosClient, materias: MateriasClient,
                 grupos: GruposClient, notificaciones: NotificacionesClient,
                 store: MatchStore):
        self.usuarios = usuarios
        self.materias = materias
        self.grupos = grupos
        self.notificaciones = notificaciones
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
                if nivel_minimo and not (cand.nivel and
                                         ORDEN_NIVEL[cand.nivel] >= ORDEN_NIVEL[nivel_minimo]):
                    continue
                disp_can = disponibilidades.get(cand.usuario_id)
                # Si Grupos está caído no se puede filtrar por modalidad
                if modalidad and not parcial and not (disp_can and disp_can.modalidad == modalidad):
                    continue
                criterios = evaluar_criterios(solicitante, cand, habilidad_id,
                                              disponibilidades.get(solicitante.usuario_id),
                                              disp_can, usar_disponibilidad=not parcial)
                encontrados.append((calcular_porcentaje(criterios), cand, habilidad_id, criterios))

        if not encontrados:
            raise SinCoincidencias(f"El usuario {usuario_id} no tiene coincidencias")

        # Mayor a menor porcentaje; desempate estable por usuario_id
        encontrados.sort(key=lambda t: (-t[0], t[1].usuario_id))

        coincidencias = []
        for porcentaje, cand, habilidad_id, criterios in encontrados:
            match, es_nuevo = self.store.guardar(
                usuario_id=usuario_id, usuario_match_id=cand.usuario_id,
                habilidad_id=habilidad_id, habilidad=catalogo[habilidad_id].nombre,
                criterios=criterios, porcentaje_match=porcentaje,
                compatibilidad_parcial=parcial)
            if es_nuevo:
                await self._notificar(match.match_id, usuario_id, cand.usuario_id,
                                      habilidad_id, porcentaje)
            coincidencias.append(Coincidencia(
                match_id=match.match_id, usuario_match_id=cand.usuario_id,
                nombre_match=cand.nombre, habilidad=match.habilidad,
                porcentaje_match=porcentaje, compatibilidad_parcial=parcial))

        return RespuestaMatching(usuario_id=usuario_id, coincidencias=coincidencias)

    async def detalle(self, usuario_id: int, match_id: int) -> DetalleMatch:
        m = self.store.obtener(match_id)
        if m is None or m.usuario_id != usuario_id:
            raise MatchNoEncontrado(f"El match {match_id} no existe para el usuario {usuario_id}")
        return DetalleMatch(
            match_id=m.match_id, usuario_id=m.usuario_id, usuario_match_id=m.usuario_match_id,
            habilidad=m.habilidad, criterios=Criterios(**m.criterios),
            porcentaje_match=m.porcentaje_match,
            compatibilidad_parcial=m.compatibilidad_parcial)

    async def _notificar(self, match_id, usuario_id, usuario_match_id, habilidad_id, porcentaje):
        """Si Notificaciones falla, el matching NO debe fallar: solo se registra."""
        try:
            await self.notificaciones.enviar(ResultadoMatch(
                match_id=match_id, usuario_id=usuario_id, usuario_match_id=usuario_match_id,
                habilidad_id=habilidad_id, porcentaje_match=porcentaje))
        except Exception as exc:
            log.error("No se pudo notificar el match %s: %s", match_id, exc)
