"""Configuración del servicio.

SIMULAR_CAIDA permite simular que otros servicios están caídos (Paso 11 del contrato).
Ejemplo:  SIMULAR_CAIDA=grupos,usuarios uvicorn app.main:app
Valores válidos: usuarios, materias, grupos, notificaciones
"""
import os


def servicios_simulados_caidos() -> set[str]:
    crudo = os.getenv("SIMULAR_CAIDA", "")
    return {s.strip().lower() for s in crudo.split(",") if s.strip()}
