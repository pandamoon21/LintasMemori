from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import initialize_database
from .routes import accounts_router, health_router, jobs_router, operations_router

app = FastAPI(title="LintasMemori API", version="0.1.0")

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
