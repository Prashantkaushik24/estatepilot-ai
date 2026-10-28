import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine

logging.basicConfig(level=logging.INFO)
s = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if s.AUTO_CREATE_TABLES and s.DATABASE_URL.startswith("sqlite"):
        import app.models  # noqa
        Base.metadata.create_all(engine)
    if s.SEED_DEMO:
        from app.db.seed import seed_if_empty
        seed_if_empty()
    yield


app = FastAPI(title="EstatePilot AI API", version=s.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def _health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        dbs = "ok"
    except Exception:
        dbs = "error"
    return {"status": "ok" if dbs == "ok" else "degraded", "db": dbs, "version": s.APP_VERSION, "demo_mode": s.DEMO_MODE,
            "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}


app.get("/health", tags=["health"])(_health)
app.get("/api/v1/health", tags=["health"])(_health)
app.include_router(api_router, prefix="/api/v1")
