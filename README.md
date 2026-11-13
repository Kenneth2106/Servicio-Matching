# StudyMatch – Servicio de Matching (contrato v1.0)

Microservicio FastAPI que obtiene usuarios, materias, intereses y disponibilidad
de PostgreSQL (Neon). No crea ni requiere una tabla `matching`; `match_id` se
genera en memoria y el endpoint de detalle no está habilitado.

## Ejecutar
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Documentación interactiva: http://localhost:8000/docs

## Conectar con Neon

Define `DATABASE_URL` en el entorno de ejecución con la cadena de conexión de Neon
(incluyendo SSL). No la guardes en el repositorio ni la compartas en logs. En
Windows, configura la variable en las variables de entorno de usuario/sistema y
reinicia la terminal antes de ejecutar el servicio. Sin ella, `/health` seguirá
disponible pero el endpoint de matching responderá `503`.

El servicio consulta:

- `usuarios` y `usuario_materia` para perfiles y habilidades ofrecidas/necesitadas.
- `materias` para el catálogo.
- `disponibilidad` para franjas semanales, comparando el día y el solapamiento
  entre `hora_inicio` y `hora_fin`. La modalidad se evalúa en las franjas coincidentes.

Los niveles `basico` de la base se convierten en `principiante` para conservar
los niveles del contrato.

## Probar
```bash
python -m pytest -q
```

## Ejecutar matching

Con `DATABASE_URL` configurada:

```bash
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/api/v1/matching/25
curl "http://localhost:8000/api/v1/matching/25?modalidad=virtual&nivel_minimo=intermedio"
```
