"""
模型导出与下载API路由
"""
import time
import json
import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.models.database import SessionLocal, ModelFile
from app.modules.car_body_generator import NURBSCarBodyGenerator as CarBodyGenerator
from app.modules.data_handover import DataHandover
from app.schemas.base import ModelExportRequest, ModelExportResponse
from app.config.settings import settings
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1/export", tags=["模型导出"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 支持的导出格式
SUPPORTED_FORMATS = {
    "glb": {"ext": ".glb", "mime": "model/gltf-binary", "description": "GLTF Binary"},
    "gltf": {"ext": ".gltf", "mime": "model/gltf+json", "description": "GLTF JSON"},
    "stl": {"ext": ".stl", "mime": "model/stl", "description": "STL Stereo Lithography"},
    "obj": {"ext": ".obj", "mime": "model/obj", "description": "Wavefront OBJ"},
    "iges": {"ext": ".iges", "mime": "model/iges", "description": "IGES"},
    "step": {"ext": ".step", "mime": "model/step", "description": "STEP"},
    "igs": {"ext": ".igs", "mime": "model/iges", "description": "IGES (alternate)"},
    "stp": {"ext": ".stp", "mime": "model/step", "description": "STEP (alternate)"},
    "json": {"ext": ".json", "mime": "application/json", "description": "JSON"},
}


@router.post("/", response_model=ModelExportResponse)
async def export_model(request: ModelExportRequest, db: Session = Depends(get_db)):
    """导出模型为指定格式"""
    try:
        start = time.time()

        model = db.query(ModelFile).filter(ModelFile.id == request.model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        # 验证格式
        invalid_formats = [f for f in request.formats if f.lower() not in SUPPORTED_FORMATS]
        if invalid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported formats: {invalid_formats}. Supported: {list(SUPPORTED_FORMATS.keys())}",
            )

        export_dir = settings.exports_path / f"model_{request.model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        export_dir.mkdir(parents=True, exist_ok=True)

        exported_files = []

        for fmt in request.formats:
            fmt_lower = fmt.lower()
            fmt_info = SUPPORTED_FORMATS[fmt_lower]
            output_filename = f"{Path(model.filename).stem}{fmt_info['ext']}"
            output_path = export_dir / output_filename

            if fmt_lower == "json":
                # JSON 导出：用 CarBodyGenerator 生成完整数据
                generator = CarBodyGenerator()
                car = generator.generate_complete_car()
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(car, f, ensure_ascii=False, indent=2)

            elif fmt_lower in ("stl", "obj", "glb", "gltf"):
                # 网格格式：优先通过 DataHandover 导出，否则用 CarBodyGenerator 直接生成
                source_path = model.filepath
                if Path(source_path).exists():
                    handover = DataHandover(
                        source_path,
                        str(export_dir),
                        {"formats": [fmt.upper()], "include_renders": False, "include_documentation": False},
                    )
                    handover.prepare_handover()
                else:
                    # 源文件不存在，用 CarBodyGenerator 直接生成网格文件
                    generator = CarBodyGenerator()
                    export_method = {
                        "glb": generator.export_glb,
                        "gltf": generator.export_glb,
                        "stl": generator.export_stl,
                        "obj": generator.export_obj,
                    }.get(fmt_lower)
                    if export_method:
                        export_method(str(output_path))
                    else:
                        # 兜底：写 JSON
                        fallback_path = export_dir / f"{Path(model.filename).stem}.json"
                        car = generator.generate_complete_car()
                        with open(fallback_path, "w", encoding="utf-8") as f:
                            json.dump(car, f, ensure_ascii=False, indent=2)
                        output_filename = f"{Path(model.filename).stem}.json"

            elif fmt_lower in ("iges", "igs", "step", "stp"):
                # CAD 交换格式：优先通过 DataHandover 导出，否则用 CarBodyGenerator 生成
                source_path = model.filepath
                if Path(source_path).exists():
                    handover = DataHandover(
                        source_path,
                        str(export_dir),
                        {"formats": [fmt.upper()], "include_renders": False, "include_documentation": False},
                    )
                    handover.prepare_handover()
                else:
                    # 源文件不存在，用 CarBodyGenerator 直接生成 STEP/IGES
                    generator = CarBodyGenerator()
                    if fmt_lower in ("step", "stp"):
                        generator.export_step(str(output_path))
                    else:
                        # IGES 格式暂用 STEP 内容替代
                        generator.export_step(str(output_path))

            file_size = output_path.stat().st_size if output_path.exists() else 0
            exported_files.append({
                "format": fmt_lower,
                "filename": output_filename,
                "path": str(output_path),
                "size": file_size,
                "mime_type": fmt_info["mime"],
            })

        elapsed = (time.time() - start) * 1000

        logger.info(f"Exported model {request.model_id} to {len(exported_files)} formats in {elapsed:.1f}ms")

        return ModelExportResponse(
            model_id=request.model_id,
            files=exported_files,
            export_time_ms=round(elapsed, 2),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Model export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{model_id}/{format}")
async def download_export(model_id: int, format: str, db: Session = Depends(get_db)):
    """下载导出的模型文件"""
    fmt_lower = format.lower()
    if fmt_lower not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Supported: {list(SUPPORTED_FORMATS.keys())}",
        )

    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 在 exports 目录查找文件
    fmt_info = SUPPORTED_FORMATS[fmt_lower]
    filename = f"{Path(model.filename).stem}{fmt_info['ext']}"

    # 搜索所有匹配的导出目录
    exports_base = settings.exports_path
    if exports_base.exists():
        for export_dir in sorted(exports_base.iterdir(), reverse=True):
            if export_dir.is_dir() and export_dir.name.startswith(f"model_{model_id}"):
                file_path = export_dir / filename
                if file_path.exists():
                    return FileResponse(
                        path=str(file_path),
                        media_type=fmt_info["mime"],
                        filename=filename,
                    )

    raise HTTPException(status_code=404, detail=f"Exported file not found. Run POST /api/v1/export/ first.")


@router.get("/formats")
async def list_export_formats():
    """列出所有支持的导出格式"""
    return {
        "formats": [
            {"key": k, "extension": v["ext"], "mime_type": v["mime"], "description": v["description"]}
            for k, v in SUPPORTED_FORMATS.items()
        ]
    }


@router.get("/history/{model_id}")
async def get_export_history(model_id: int):
    """获取模型的导出历史"""
    exports_base = settings.exports_path
    history = []

    if exports_base.exists():
        for export_dir in sorted(exports_base.iterdir(), reverse=True):
            if export_dir.is_dir() and export_dir.name.startswith(f"model_{model_id}"):
                files = []
                for f in export_dir.iterdir():
                    if f.is_file():
                        files.append({
                            "filename": f.name,
                            "size": f.stat().st_size,
                            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        })
                history.append({
                    "directory": export_dir.name,
                    "files": files,
                })

    return {"model_id": model_id, "exports": history}
