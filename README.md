# StudyMatch – Servicio de Matching (contrato v1.0)

Microservicio FastAPI. Usa **datos de prueba (mocks)** y almacenamiento en memoria
mientras los demás servicios y la base de datos no estén disponibles.

## Ejecutar
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Documentación interactiva: http://localhost:8000/docs

## Probar
```bash
curl http://localhost:8000/api/v1/matching/25
curl http://localhost:8000/api/v1/matching/25/detalle/101
curl "http://localhost:8000/api/v1/matching/25?modalidad=virtual&nivel_minimo=intermedio"
python -m pytest -q
```

## Simular caídas de otros servicios (Paso 11)
```bash
SIMULAR_CAIDA=grupos   uvicorn app.main:app      # -> compatibilidad parcial
SIMULAR_CAIDA=usuarios uvicorn app.main:app      # -> 503
```
(Windows PowerShell: `$env:SIMULAR_CAIDA="grupos"; uvicorn app.main:app`)

## Usuarios de prueba
| id | nombre | ofrece | necesita |
|----|--------|--------|----------|
| 25 | Ana | Python | Bases de Datos |
| 12 | Carlos | Bases de Datos | Python |
| 31 | Laura | Bases de Datos, Redes | Python |
| 40 | Pedro | Redes | Bases de Datos |
| 50 | Sofía | Bases de Datos | Redes |
| 60 | Marta | – | Cálculo (nadie lo ofrece → 404) |

## Cuando lleguen los servicios reales
1. Crear `app/clients/http_clients.py` con clases `httpx` que cumplan las interfaces de `clients/base.py`.
2. Cambiar los mocks por esos clientes en `app/dependencies.py`.
3. Cambiar `app/store.py` por el repositorio de la BD (mismos métodos `guardar` / `obtener`).
