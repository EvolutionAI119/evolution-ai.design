from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.routes import router
from app.api.modify_routes import router as modify_router
from app.api.learning_routes import router as learning_router
from app.api.car_routes import router as car_router
from app.api.build_routes import router as build_router
from app.api.export_routes import router as export_router
from app.api.variant_routes import router as variant_router
from app.config.settings import settings
from app.models.database import init_db
from app.utils.logger import logger


def create_app() -> FastAPI:
    app = FastAPI(
        title="EVOLUTION AI - 汽车A级曲面开发平台",
        description="基于AI的汽车A级曲面开发全流程解决方案",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    app.include_router(router, prefix="/api/v1")
    app.include_router(modify_router)
    app.include_router(learning_router, prefix="/api/v1/learning")
    app.include_router(car_router)
    app.include_router(build_router)
    app.include_router(export_router)
    app.include_router(variant_router)

    @app.on_event("startup")
    def startup():
        init_db()
        settings.models_path.mkdir(parents=True, exist_ok=True)
        settings.reports_path.mkdir(parents=True, exist_ok=True)
        settings.exports_path.mkdir(parents=True, exist_ok=True)
        logger.info("EVOLUTION AI service started")

    @app.on_event("shutdown")
    def shutdown():
        logger.info("EVOLUTION AI service stopped")

    return app


app = create_app()