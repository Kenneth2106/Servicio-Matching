"""Schemas Pydantic: definen la forma de los datos del contrato (Pasos 3, 6 y 8)."""
from typing import Literal
from pydantic import BaseModel, Field

Modalidad = Literal["presencial", "virtual"]
Nivel = Literal["principiante", "intermedio", "avanzado"]


# ---------- Entradas (datos que llegan de otros servicios) ----------
class PerfilEstudiante(BaseModel):  # 3.1 Usuarios e Intereses
    usuario_id: int = Field(gt=0)
    nombre: str
    habilidades_ofrece: list[int]
    habilidades_necesita: list[int]
    nivel: Nivel | None = None


class Materia(BaseModel):  # 3.2 Materias
    materia_id: int = Field(gt=0)
    nombre: str
    categoria: str | None = None


class Disponibilidad(BaseModel):  # 3.3 Grupos
    usuario_id: int = Field(gt=0)
    dias_disponibles: list[str]
    modalidad: Modalidad


# ---------- Salida hacia Notificaciones y Chat ----------
class ResultadoMatch(BaseModel):  # 3.4
    match_id: int = Field(gt=0)
    usuario_id: int = Field(gt=0)
    usuario_match_id: int = Field(gt=0)
    habilidad_id: int = Field(gt=0)
    porcentaje_match: float = Field(ge=0, le=100)


# ---------- Respuestas de la API (Paso 6) ----------
class Coincidencia(BaseModel):
    match_id: int
    usuario_match_id: int
    nombre_match: str
    habilidad: str
    porcentaje_match: float = Field(ge=0, le=100)
    compatibilidad_parcial: bool = False  # True si Grupos no estaba disponible


class RespuestaMatching(BaseModel):
    usuario_id: int
    coincidencias: list[Coincidencia]


class Criterios(BaseModel):
    habilidad: bool
    disponibilidad: bool | None  # None = no evaluado (Grupos caído)
    modalidad: bool | None
    nivel: bool


class DetalleMatch(BaseModel):
    match_id: int
    usuario_id: int
    usuario_match_id: int
    habilidad: str
    criterios: Criterios
    porcentaje_match: float = Field(ge=0, le=100)
    compatibilidad_parcial: bool = False
