"""Clientes SIMULADOS con datos de prueba. Reemplazar por clientes httpx cuando los otros
servicios estén listos (misma interfaz definida en base.py)."""
import logging
from app.config import servicios_simulados_caidos
from app.errors import ServicioNoDisponible, UsuarioNoEncontrado
from app.schemas import PerfilEstudiante, Materia, Disponibilidad, ResultadoMatch

log = logging.getLogger("matching")


class _Simulado:
    nombre = ""

    def __init__(self, caido: bool = False):
        self._caido = caido

    def _verificar(self) -> None:
        if self._caido or self.nombre in servicios_simulados_caidos():
            raise ServicioNoDisponible(self.nombre)


# ---------------- Datos de prueba ----------------
MATERIAS = [
    Materia(materia_id=1, nombre="Bases de Datos", categoria="Software"),
    Materia(materia_id=2, nombre="Python", categoria="Programación"),
    Materia(materia_id=3, nombre="Redes", categoria="Infraestructura"),
    Materia(materia_id=4, nombre="Cálculo", categoria="Matemáticas"),
]

PERFILES = [
    PerfilEstudiante(usuario_id=25, nombre="Ana", habilidades_ofrece=[2],
                     habilidades_necesita=[1], nivel="intermedio"),
    PerfilEstudiante(usuario_id=12, nombre="Carlos", habilidades_ofrece=[1],
                     habilidades_necesita=[2], nivel="intermedio"),
    PerfilEstudiante(usuario_id=31, nombre="Laura", habilidades_ofrece=[1, 3],
                     habilidades_necesita=[2], nivel="intermedio"),
    PerfilEstudiante(usuario_id=40, nombre="Pedro", habilidades_ofrece=[3],
                     habilidades_necesita=[1], nivel="principiante"),
    PerfilEstudiante(usuario_id=50, nombre="Sofía", habilidades_ofrece=[1],
                     habilidades_necesita=[3], nivel="avanzado"),
    # Marta necesita Cálculo y nadie lo ofrece -> sirve para probar el 404 "sin coincidencias"
    PerfilEstudiante(usuario_id=60, nombre="Marta", habilidades_ofrece=[],
                     habilidades_necesita=[4], nivel="intermedio"),
]

DISPONIBILIDAD = [
    Disponibilidad(usuario_id=25, dias_disponibles=["lunes", "miércoles"], modalidad="virtual"),
    Disponibilidad(usuario_id=12, dias_disponibles=["lunes", "viernes"], modalidad="virtual"),
    Disponibilidad(usuario_id=31, dias_disponibles=["lunes"], modalidad="presencial"),
    Disponibilidad(usuario_id=40, dias_disponibles=["jueves"], modalidad="virtual"),
    Disponibilidad(usuario_id=50, dias_disponibles=["martes"], modalidad="virtual"),
    Disponibilidad(usuario_id=60, dias_disponibles=["lunes"], modalidad="virtual"),
]


# ---------------- Mocks ----------------
class MockUsuariosClient(_Simulado):
    nombre = "usuarios"

    async def obtener_perfil(self, usuario_id: int) -> PerfilEstudiante:
        self._verificar()
        for p in PERFILES:
            if p.usuario_id == usuario_id:
                return p
        raise UsuarioNoEncontrado(f"El usuario {usuario_id} no existe")

    async def listar_perfiles(self) -> list[PerfilEstudiante]:
        self._verificar()
        return list(PERFILES)


class MockMateriasClient(_Simulado):
    nombre = "materias"

    async def listar(self) -> list[Materia]:
        self._verificar()
        return list(MATERIAS)


class MockGruposClient(_Simulado):
    nombre = "grupos"

    async def obtener_disponibilidad(self, usuario_id: int) -> Disponibilidad | None:
        self._verificar()
        return next((d for d in DISPONIBILIDAD if d.usuario_id == usuario_id), None)


class MockNotificacionesClient(_Simulado):
    nombre = "notificaciones"

    def __init__(self, caido: bool = False):
        super().__init__(caido)
        self.enviados: list[ResultadoMatch] = []

    async def enviar(self, resultado: ResultadoMatch) -> None:
        self._verificar()
        self.enviados.append(resultado)
        log.info("[MOCK Notificaciones] %s", resultado.model_dump())
