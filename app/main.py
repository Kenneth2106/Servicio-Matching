import logging
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.dependencies import crear_service
from app.errors import registrar_handlers
from app.routers import matching

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_url = os.getenv("DATABASE_URL")
    app.state.db_pool = None
    app.state.matching_service = None
    if database_url:
        pool = await asyncpg.create_pool(database_url, ssl="require")
        app.state.db_pool = pool
        app.state.matching_service = crear_service(pool)
    try:
        yield
    finally:
        if app.state.db_pool is not None:
            await app.state.db_pool.close()


app = FastAPI(title="StudyMatch - Servicio de Matching", version="1.0", lifespan=lifespan)
registrar_handlers(app)
app.include_router(matching.router)


@app.middleware("http")
async def permitir_frontend_registrado(request, call_next):
    response = await call_next(request)
    origen = os.getenv("STUDYMATCH_FRONTEND_ORIGIN", "http://localhost:4200").strip().rstrip("/")
    response.headers["Content-Security-Policy"] = f"frame-ancestors {origen}"
    return response


@app.get("/config.js", include_in_schema=False)
async def configuracion_frontend():
    configuracion = {
        "matchingApiBase": os.getenv("STUDYMATCH_MATCHING_API_BASE", "").strip().rstrip("/"),
        "frontendOrigin": os.getenv(
            "STUDYMATCH_FRONTEND_ORIGIN", "http://localhost:4200"
        ).strip().rstrip("/"),
    }
    return Response(
        content=f"window.STUDYMATCH_CONFIG = {json.dumps(configuracion)};",
        media_type="application/javascript",
    )


@app.get("/health", tags=["salud"])
async def health():
    return {"status": "ok", "servicio": "matching", "version_contrato": "1.0"}


app.mount(
    "/",
    StaticFiles(directory=Path(__file__).parent / "static", html=True),
    name="frontend",
)
