"""FastAPI应用入口：CORS配置、路由注册、启动初始化"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routes import (car, project, model, build, export, variant, quality, workflow, modify)


def create_app() -> FastAPI:
    app = FastAPI(
        title="EVOLUTION AI - 汽车A级曲面开发平台",
        description="基于NURBS引擎的汽车A级曲面开发全流程解决方案",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(project.router, prefix="/api/v1", tags=["项目管理"])
    app.include_router(model.router, prefix="/api/v1", tags=["模型管理"])
    app.include_router(workflow.router, prefix="/api/v1", tags=["工作流"])
    app.include_router(quality.router, prefix="/api/v1", tags=["质量检查"])
    app.include_router(car.router, tags=["车身生成"])
    app.include_router(build.router, tags=["模型构建"])
    app.include_router(export.router, tags=["模型导出"])
    app.include_router(variant.router, tags=["模型变体"])
    app.include_router(modify.router, tags=["模型修改"])

    @app.on_event("startup")
    def startup():
        init_db()
        settings.models_path.mkdir(parents=True, exist_ok=True)
        settings.reports_path.mkdir(parents=True, exist_ok=True)
        settings.exports_path.mkdir(parents=True, exist_ok=True)

    @app.get("/api/v1/health")
    def health_check():
        return {"status": "healthy", "service": "EVOLUTION AI"}

    @app.get("/api/v1/i18n/config")
    def get_i18n_config():
        return {
            "default_language": settings.DEFAULT_LANGUAGE,
            "supported_languages": settings.supported_languages_list,
            "current_language": settings.DEFAULT_LANGUAGE,
        }

    return app


app = create_app()
