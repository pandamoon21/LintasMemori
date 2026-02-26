from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import initialize_database
from .routes import accounts_router, health_router, jobs_router, operations_router
from .routes_v2 import (
    v2_accounts_router,
    v2_actions_router,
    v2_advanced_router,
    v2_explorer_router,
    v2_jobs_router,
    v2_pipeline_router,
    v2_uploads_router,
)

app = FastAPI(title="LintasMemori API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()


app.include_router(health_router)
app.include_router(accounts_router)
app.include_router(jobs_router)
app.include_router(operations_router)

# V2 API
app.include_router(v2_accounts_router)
app.include_router(v2_explorer_router)
app.include_router(v2_actions_router)
app.include_router(v2_uploads_router)
app.include_router(v2_pipeline_router)
app.include_router(v2_jobs_router)
app.include_router(v2_advanced_router)


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse(
        {
            "name": "LintasMemori API",
            "version": "0.2.0",
            "health": "/health",
            "v2": "/api/v2",
        }
    )


static_dir = Path(settings.static_dir)
if static_dir.exists():
    app.mount("/app", StaticFiles(directory=static_dir, html=True), name="web")
