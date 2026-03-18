from __future__ import annotations

from fastapi import FastAPI

from app.api.router import api_router

APP_NAME = "VoltIQ Backend"
APP_VERSION = "0.1.0-step9"


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict[str, str]:
        return {
            "service": "voltiq-backend",
            "status": "ok",
            "version": APP_VERSION,
        }

    app.include_router(api_router)
    return app


app = create_app()
