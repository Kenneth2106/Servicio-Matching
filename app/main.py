import logging
import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app.dependencies import crear_service
from app.errors import registrar_handlers
from app.routers import matching

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


@app.get("/health", tags=["salud"])
async def health():
    return {"status": "ok", "servicio": "matching", "version_contrato": "1.0"}
