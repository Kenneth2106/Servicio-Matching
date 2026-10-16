import logging
from fastapi import FastAPI

from app.errors import registrar_handlers
from app.routers import matching

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="StudyMatch - Servicio de Matching", version="1.0")
registrar_handlers(app)
app.include_router(matching.router)


@app.get("/health", tags=["salud"])
async def health():
    return {"status": "ok", "servicio": "matching", "version_contrato": "1.0"}
