"""Excepciones propias y handlers que traducen todo a los códigos del contrato (Paso 7)."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

log = logging.getLogger("matching")


class ErrorServicio(Exception):
    status_code = 500
    error = "error_interno"

    def __init__(self, detalle: str = ""):
        self.detalle = detalle
        super().__init__(detalle)


class UsuarioNoEncontrado(ErrorServicio):
    status_code = 404
    error = "usuario_no_encontrado"


class SinCoincidencias(ErrorServicio):
    status_code = 404
    error = "sin_coincidencias"


class MatchNoEncontrado(ErrorServicio):
    status_code = 404
    error = "match_no_encontrado"


class ServicioNoDisponible(ErrorServicio):
    status_code = 503
    error = "servicio_no_disponible"

    def __init__(self, servicio: str, detalle: str = ""):
        self.servicio = servicio
        super().__init__(detalle or f"El servicio '{servicio}' no está disponible")


def _respuesta(status: int, error: str, detalle: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": error, "detalle": detalle})


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErrorServicio)
    async def _error_servicio(request: Request, exc: ErrorServicio):
        if exc.status_code >= 500:
            log.error("%s: %s", exc.error, exc.detalle)
        return _respuesta(exc.status_code, exc.error, exc.detalle)

    # FastAPI responde 422 por defecto; el contrato pide 400.
    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        detalle = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        return _respuesta(400, "solicitud_incorrecta", detalle)

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception):
        log.exception("Error inesperado calculando coincidencias")
        return _respuesta(500, "error_interno", "Error interno del servicio de Matching")
