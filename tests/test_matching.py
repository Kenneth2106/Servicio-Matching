"""Pruebas de integración del Paso 11 (con mocks)."""
import pytest
from fastapi.testclient import TestClient
import asyncio
from datetime import time

from app.clients.mock_clients import MockGruposClient, MockMateriasClient, MockUsuariosClient
from app.clients.postgres_clients import (PostgresGruposClient, PostgresMateriasClient,
                                          PostgresUsuariosClient)
from app.dependencies import get_service
from app.main import app
from app.schemas import Disponibilidad, FranjaDisponibilidad, PerfilEstudiante
from app.services.matching_service import MatchingService, evaluar_criterios
from app.store import MatchStore


def crear_cliente(usuarios_caido=False, materias_caido=False, grupos_caido=False):
    service = MatchingService(MockUsuariosClient(usuarios_caido), MockMateriasClient(materias_caido),
                              MockGruposClient(grupos_caido), MatchStore())
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def limpiar():
    yield
    app.dependency_overrides.clear()


def test_coincidencia_cruzada_ordenada():
    c = crear_cliente()
    r = c.get("/api/v1/matching/25")
    assert r.status_code == 200
    assert set(r.json()) == {"usuario_id", "coincidencias"}
    datos = r.json()["coincidencias"]
    assert datos[0]["nombre_match"] == "Carlos" and datos[0]["porcentaje_match"] == 100
    assert datos[1]["nombre_match"] == "Laura" and datos[1]["porcentaje_match"] == 75
    assert set(datos[0]) == {
        "match_id", "usuario_match_id", "nombre_match", "habilidad",
        "porcentaje_match", "compatibilidad_parcial",
    }
    porcentajes = [d["porcentaje_match"] for d in datos]
    assert porcentajes == sorted(porcentajes, reverse=True)
    assert all(d["habilidad"] == "Bases de Datos" for d in datos)


def test_grupos_caido_da_compatibilidad_parcial():
    c = crear_cliente(grupos_caido=True)
    r = c.get("/api/v1/matching/25")
    assert r.status_code == 200
    assert all(d["compatibilidad_parcial"] for d in r.json()["coincidencias"])


def test_usuarios_caido_da_503_no_404():
    c = crear_cliente(usuarios_caido=True)
    assert c.get("/api/v1/matching/25").status_code == 503


def test_materias_caido_da_503():
    c = crear_cliente(materias_caido=True)
    assert c.get("/api/v1/matching/25").status_code == 503


def test_usuario_inexistente_da_404_no_500():
    c = crear_cliente()
    assert c.get("/api/v1/matching/999").status_code == 404


def test_usuario_sin_coincidencias_da_404():
    c = crear_cliente()
    assert c.get("/api/v1/matching/60").status_code == 404  # Marta necesita Cálculo y nadie lo ofrece


def test_parametros_invalidos_dan_400():
    c = crear_cliente()
    assert c.get("/api/v1/matching/abc").status_code == 400
    assert c.get("/api/v1/matching/0").status_code == 400
    assert c.get("/api/v1/matching/25?modalidad=online").status_code == 400
    assert c.get("/api/v1/matching/25?nivel_minimo=experto").status_code == 400


def test_filtro_modalidad():
    c = crear_cliente()
    r = c.get("/api/v1/matching/25?modalidad=presencial")
    nombres = [d["nombre_match"] for d in r.json()["coincidencias"]]
    assert nombres == ["Laura"]


def test_detalle_no_disponible_sin_tabla_matching():
    c = crear_cliente()
    assert c.get("/api/v1/matching/25/detalle/101").status_code == 404


def test_health():
    c = crear_cliente()
    assert c.get("/health").json()["status"] == "ok"


def test_disponibilidad_exige_dia_y_solapamiento_real():
    solicitante = PerfilEstudiante(
        usuario_id=1, nombre="A", habilidades_ofrece=[],
        habilidades_necesita=[2], nivel="principiante",
    )
    candidato = PerfilEstudiante(
        usuario_id=2, nombre="B", habilidades_ofrece=[2],
        habilidades_necesita=[], nivel="intermedio",
    )
    disp_sol = Disponibilidad(usuario_id=1, franjas=[
        FranjaDisponibilidad(dia_semana="miércoles", hora_inicio=time(10), hora_fin=time(11),
                             modalidad="virtual"),
    ])
    sin_solapamiento = Disponibilidad(usuario_id=2, franjas=[
        FranjaDisponibilidad(dia_semana="miercoles", hora_inicio=time(11), hora_fin=time(12),
                             modalidad="virtual"),
    ])
    criterios = evaluar_criterios(solicitante, candidato, 2, disp_sol, sin_solapamiento, True)
    assert criterios["disponibilidad"] is False
    assert criterios["modalidad"] is False


def test_solapamiento_con_modalidad_distinta_suma_solo_disponibilidad():
    solicitante = PerfilEstudiante(
        usuario_id=1, nombre="A", habilidades_ofrece=[],
        habilidades_necesita=[2], niveles_habilidades={2: "intermedio"},
    )
    candidato = PerfilEstudiante(
        usuario_id=2, nombre="B", habilidades_ofrece=[2],
        habilidades_necesita=[], niveles_habilidades={2: "avanzado"},
    )
    disp_sol = Disponibilidad(usuario_id=1, franjas=[
        FranjaDisponibilidad(dia_semana="lunes", hora_inicio=time(10), hora_fin=time(11),
                             modalidad="virtual"),
    ])
    disp_can = Disponibilidad(usuario_id=2, franjas=[
        FranjaDisponibilidad(dia_semana="lunes", hora_inicio=time(10, 30), hora_fin=time(11, 30),
                             modalidad="presencial"),
    ])
    criterios = evaluar_criterios(solicitante, candidato, 2, disp_sol, disp_can, True)
    assert criterios["disponibilidad"] is True
    assert criterios["modalidad"] is False
    assert criterios["nivel"] is True


class _FakeConnection:
    async def fetch(self, query, *args):
        if "FROM public.usuarios AS u" in query:
            if "WHERE u.usuario_id = $1" in query:
                return [
                    {"usuario_id": args[0], "nombre": "Ana Ruiz", "materia_id": 7,
                     "tipo": "necesita", "nivel": "basico"},
                ]
            return [
                {"usuario_id": 8, "nombre": "Luis", "materia_id": 7,
                 "tipo": "ofrece", "nivel": "avanzado"},
            ]
        if "FROM public.materias" in query:
            return [{"materia_id": 7, "nombre": "Cálculo", "carrera": "Ingeniería"}]
        if "FROM public.disponibilidad" in query:
            return [
                {"dia_semana": "lunes", "hora_inicio": time(9), "hora_fin": time(10),
                 "modalidad": None},
                {"dia_semana": "lunes", "hora_inicio": time(11), "hora_fin": time(12),
                 "modalidad": "virtual"},
            ]
        raise AssertionError(f"Consulta no esperada: {query}")


class _FakeAcquire:
    async def __aenter__(self):
        return _FakeConnection()

    async def __aexit__(self, _exc_type, _exc_value, _traceback):
        return False


class _FakePool:
    def acquire(self):
        return _FakeAcquire()


def test_clientes_postgres_convierten_el_esquema_a_modelos():
    async def verificar():
        pool = _FakePool()
        usuario = await PostgresUsuariosClient(pool).obtener_perfil(25)
        perfiles = await PostgresUsuariosClient(pool).listar_perfiles()
        materias = await PostgresMateriasClient(pool).listar()
        disponibilidad = await PostgresGruposClient(pool).obtener_disponibilidad(25)

        assert usuario.niveles_habilidades == {7: "principiante"}
        assert perfiles[0].habilidades_ofrece == [7]
        assert perfiles[0].niveles_habilidades == {7: "avanzado"}
        assert materias[0].nombre == "Cálculo"
        assert len(disponibilidad.franjas) == 2
        assert disponibilidad.franjas[0].modalidad is None

    asyncio.run(verificar())
