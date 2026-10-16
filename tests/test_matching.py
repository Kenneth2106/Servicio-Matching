"""Pruebas de integración del Paso 11 (con mocks)."""
import pytest
from fastapi.testclient import TestClient

from app.clients.mock_clients import (MockGruposClient, MockMateriasClient,
                                      MockNotificacionesClient, MockUsuariosClient)
from app.dependencies import get_service
from app.main import app
from app.services.matching_service import MatchingService
from app.store import MatchStore


def crear_cliente(usuarios_caido=False, materias_caido=False, grupos_caido=False,
                  notif_caido=False):
    notif = MockNotificacionesClient(caido=notif_caido)
    service = MatchingService(MockUsuariosClient(usuarios_caido), MockMateriasClient(materias_caido),
                              MockGruposClient(grupos_caido), notif, MatchStore())
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False), notif


@pytest.fixture(autouse=True)
def limpiar():
    yield
    app.dependency_overrides.clear()


def test_coincidencia_cruzada_ordenada():
    c, _ = crear_cliente()
    r = c.get("/api/v1/matching/25")
    assert r.status_code == 200
    datos = r.json()["coincidencias"]
    assert datos[0]["nombre_match"] == "Carlos" and datos[0]["porcentaje_match"] == 100
    assert datos[1]["nombre_match"] == "Laura" and datos[1]["porcentaje_match"] == 75
    porcentajes = [d["porcentaje_match"] for d in datos]
    assert porcentajes == sorted(porcentajes, reverse=True)
    assert all(d["habilidad"] == "Bases de Datos" for d in datos)


def test_grupos_caido_da_compatibilidad_parcial():
    c, _ = crear_cliente(grupos_caido=True)
    r = c.get("/api/v1/matching/25")
    assert r.status_code == 200
    assert all(d["compatibilidad_parcial"] for d in r.json()["coincidencias"])


def test_usuarios_caido_da_503_no_404():
    c, _ = crear_cliente(usuarios_caido=True)
    assert c.get("/api/v1/matching/25").status_code == 503


def test_materias_caido_da_503():
    c, _ = crear_cliente(materias_caido=True)
    assert c.get("/api/v1/matching/25").status_code == 503


def test_usuario_inexistente_da_404_no_500():
    c, _ = crear_cliente()
    assert c.get("/api/v1/matching/999").status_code == 404


def test_usuario_sin_coincidencias_da_404():
    c, _ = crear_cliente()
    assert c.get("/api/v1/matching/60").status_code == 404  # Marta necesita Cálculo y nadie lo ofrece


def test_parametros_invalidos_dan_400():
    c, _ = crear_cliente()
    assert c.get("/api/v1/matching/abc").status_code == 400
    assert c.get("/api/v1/matching/0").status_code == 400
    assert c.get("/api/v1/matching/25?modalidad=online").status_code == 400
    assert c.get("/api/v1/matching/25?nivel_minimo=experto").status_code == 400


def test_filtro_modalidad():
    c, _ = crear_cliente()
    r = c.get("/api/v1/matching/25?modalidad=presencial")
    nombres = [d["nombre_match"] for d in r.json()["coincidencias"]]
    assert nombres == ["Laura"]


def test_detalle_del_match():
    c, _ = crear_cliente()
    match_id = c.get("/api/v1/matching/25").json()["coincidencias"][0]["match_id"]
    r = c.get(f"/api/v1/matching/25/detalle/{match_id}")
    assert r.status_code == 200
    d = r.json()
    assert d["criterios"] == {"habilidad": True, "disponibilidad": True,
                              "modalidad": True, "nivel": True}
    assert d["porcentaje_match"] == 100
    # El match de Ana no puede consultarlo otro usuario
    assert c.get(f"/api/v1/matching/12/detalle/{match_id}").status_code == 404
    assert c.get("/api/v1/matching/25/detalle/9999").status_code == 404


def test_notificaciones_recibe_resultado_solo_si_match_nuevo():
    c, notif = crear_cliente()
    c.get("/api/v1/matching/25")
    assert len(notif.enviados) >= 2
    assert {"match_id", "usuario_id", "usuario_match_id", "habilidad_id",
            "porcentaje_match"} == set(notif.enviados[0].model_dump())
    cantidad = len(notif.enviados)
    c.get("/api/v1/matching/25")  # misma consulta: no se re-notifica
    assert len(notif.enviados) == cantidad


def test_notificaciones_caido_no_rompe_matching():
    c, _ = crear_cliente(notif_caido=True)
    assert c.get("/api/v1/matching/25").status_code == 200


def test_health():
    c, _ = crear_cliente()
    assert c.get("/health").json()["status"] == "ok"
