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

Para desarrollo local puedes crear un archivo `.env` en la raíz del proyecto:

```env
DATABASE_URL=postgresql://USUARIO:CLAVE@HOST:5432/BASE
```

La aplicación carga ese archivo al iniciar. `.env` está excluido de Git: no lo
fuerces al repositorio ni compartas su contenido. Una variable `DATABASE_URL`
configurada directamente en el entorno tiene prioridad sobre el valor de `.env`.
La conexión a PostgreSQL requiere SSL.

En el servidor de despliegue también habrá que configurar `DATABASE_URL` de forma
segura. Un `.env` que solo exista en esta máquina no se copia al servidor con
`git clone`. Sin la variable, `/health` seguirá disponible pero el endpoint de
matching responderá `503`.

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

## Interfaz integrada con StudyMatch

La interfaz del módulo está en `app/static` y se sirve desde la misma aplicación
FastAPI. En desarrollo se abre en http://localhost:8000; el Frontend anfitrión
debe incrustar esa URL en su iframe. El módulo envía `LISTO` y `ACTIVIDAD`,
recibe `SESION` y limpia la pantalla al recibir `CERRAR_SESION`. El token se
mantiene solo en memoria y se envía al API Gateway como Bearer.

Configura estas variables en el entorno de ejecución o en `.env`:

```env
STUDYMATCH_FRONTEND_ORIGIN=http://localhost:4200
STUDYMATCH_MATCHING_API_BASE=https://<URL-DEL-GATEWAY>/api/v1/matching
```

`STUDYMATCH_MATCHING_API_BASE` es la ruta base del endpoint de Matching a través
del Gateway; la interfaz agrega `/{usuario_id}` y los filtros `modalidad` y
`nivel_minimo`. Si el Gateway usa otra ruta, configura esa ruta exacta. La
interfaz no consulta directamente el servicio de Render cuando esta variable no
está definida.

En Render configura las mismas variables en Environment. Usa el origen exacto
del Frontend publicado para `STUDYMATCH_FRONTEND_ORIGIN`; ese valor se usa en
`frame-ancestors` y en la validación de `postMessage`. El API Gateway debe
permitir CORS desde el origen público de esta interfaz (el dominio del módulo
que carga el iframe) y aceptar el encabezado `Authorization`.
El Gateway también debe incluir sus encabezados CORS en respuestas de error
(incluidos los `401`) para que el módulo pueda notificar una sesión inválida.

Las coincidencias se vuelven a consultar al aplicar o limpiar filtros; el
`match_id` continúa siendo generado en memoria por el servicio y no representa
un registro persistido.

## Ejecutar matching

Con `DATABASE_URL` configurada:

```bash
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/api/v1/matching/25
curl "http://localhost:8000/api/v1/matching/25?modalidad=virtual&nivel_minimo=intermedio"
```
