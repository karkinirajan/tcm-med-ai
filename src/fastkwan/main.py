import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import NotConfigured, Settings
from .routes import protected, public
from .services import Services


def create_app(settings=None, services=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        yield
        app.state.services.close()

    app = FastAPI(
        title="FastKwan",
        description="Traditional Chinese Medicine (TCM) AI API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.services = services or Services(settings)
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    @app.exception_handler(NotConfigured)
    async def not_configured(request: Request, error: NotConfigured):
        return JSONResponse({"detail": str(error)}, status_code=503)

    app.include_router(public)
    app.include_router(protected)
    return app


def run():
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


app = create_app()
