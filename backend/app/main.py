from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.runs import router as runs_router
from app.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


settings = get_settings()

app = FastAPI(
    title="AI-Game-Generator-Agent",
    description=(
        "LangGraph game builder: clarify → GameSpec → design → code → test → deploy."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(runs_router, prefix="/api")
