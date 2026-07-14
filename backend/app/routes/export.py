"""模型导出与下载API路由"""
import time
import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, ModelFile
from ..car_generator import NURBSCarBodyGenerator as CarBodyGenerator
from ..schemas import ModelExportRequest, ModelExportResponse
from ..config import settings

router = APIRouter(prefix="/api/v1/export", tags=["模型导出"])

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
        invalid = [f for f in request.formats if f.lower() not in SUPPORTED_FORMATS]
        if invalid:
            raise HTTPException(status_code=400,
                                detail=f"Unsupported formats: {invalid}. Supported: {list(SUPPORTED_FORMATS)}")
        export_dir = settings.exports_path / f"model_{request.model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        export_dir.mkdir(parents=True, exist_ok=True)
        exported_files = []
        generator = CarBodyGenerator()
        for fmt in request.formats:
            fl = fmt.lower()
            info = SUPPORTED_FORMATS[fl]
            out_name = f"{Path(model.filename).stem}{info['ext']}"
            out_path = export_dir / out_name
            if fl == "json":
                car = generator.generate_complete_car()
                out_path.write_text(json.dumps(car, ensure_ascii=False, indent=2), encoding="utf-8")
            elif fl in ("stl", "obj", "glb", "gltf"):
                method = {"glb": generator.export_glb, "gltf": generator.export_glb,
                          "stl": generator.export_stl, "obj": generator.export_obj}[fl]
                method(str(out_path))
            elif fl in ("step", "stp", "iges", "igs"):
                generator.export_step(str(out_path))
            exported_files.append({
                "format": fl, "filename": out_name, "path": str(out_path),
                "size": out_path.stat().st_size if out_path.exists() else 0,
                "mime_type": info["mime"]})
        elapsed = (time.time() - start) * 1000
        return ModelExportResponse(model_id=request.model_id, files=exported_files,
                                   export_time_ms=round(elapsed, 2))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{model_id}/{format}")
async def download_export(model_id: int, format: str, db: Session = Depends(get_db)):
    """下载导出的模型文件"""
    fl = format.lower()
    if fl not in SUPPORTED_FORMATS:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported format: {format}. Supported: {list(SUPPORTED_FORMATS)}")
    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    info = SUPPORTED_FORMATS[fl]
    filename = f"{Path(model.filename).stem}{info['ext']}"
    if settings.exports_path.exists():
        for export_dir in sorted(settings.exports_path.iterdir(), reverse=True):
            if export_dir.is_dir() and export_dir.name.startswith(f"model_{model_id}"):
                fp = export_dir / filename
                if fp.exists():
                    return FileResponse(path=str(fp), media_type=info["mime"], filename=filename)
    raise HTTPException(status_code=404, detail="Exported file not found. Run POST /api/v1/export/ first.")


@router.get("/formats")
async def list_export_formats():
    """列出所有支持的导出格式"""
    return {"formats": [{"key": k, "extension": v["ext"], "mime_type": v["mime"],
                         "description": v["description"]} for k, v in SUPPORTED_FORMATS.items()]}


@router.get("/history/{model_id}")
async def get_export_history(model_id: int):
    """获取模型的导出历史"""
    history = []
    if settings.exports_path.exists():
        for export_dir in sorted(settings.exports_path.iterdir(), reverse=True):
            if export_dir.is_dir() and export_dir.name.startswith(f"model_{model_id}"):
                files = [{"filename": f.name, "size": f.stat().st_size,
                          "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()}
                         for f in export_dir.iterdir() if f.is_file()]
                history.append({"directory": export_dir.name, "files": files})
    return {"model_id": model_id, "exports": history}
