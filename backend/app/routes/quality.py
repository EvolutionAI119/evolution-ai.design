"""质量检查与拓扑优化API路由"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db, ModelFile, QualityReport
from ..schemas import (TopologyOptimizationRequest, QualityCheckRequest,
                       QualityReportResponse, DataHandoverRequest)
from ..config import settings

router = APIRouter()


@router.post("/topology/optimize/")
def optimize_topology(request: TopologyOptimizationRequest, db: Session = Depends(get_db)):
    """拓扑优化（简化版：返回统计信息）"""
    model = db.query(ModelFile).filter(ModelFile.id == request.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {
        "model_id": request.model_id, "status": "optimized",
        "target_faces": request.target_faces, "min_quad_ratio": request.min_quad_ratio,
        "original_faces": 32000, "optimized_faces": request.target_faces,
        "quad_ratio": 0.82, "timestamp": datetime.now().isoformat(),
    }


@router.post("/quality/check/")
def check_quality(request: QualityCheckRequest, db: Session = Depends(get_db)):
    """质量检查（简化版：生成评分报告）"""
    model = db.query(ModelFile).filter(ModelFile.id == request.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    result = {
        "score": 92.5, "passed": True,
        "checks": {"continuity_g0": True, "continuity_g1": True, "continuity_g2": True,
                   "curvature_quality": 0.95, "surface_smoothness": 0.88},
        "issues": [],
        "timestamp": datetime.now().isoformat(),
    }
    db_report = QualityReport(
        project_id=model.project_id, model_id=model.id,
        overall_score=result["score"], passed=result["passed"],
        report_data=str(result))
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return {**result, "report_id": db_report.id}


@router.get("/quality/reports/", response_model=List[QualityReportResponse])
def get_quality_reports(project_id: Optional[int] = None, model_id: Optional[int] = None,
                        db: Session = Depends(get_db)):
    query = db.query(QualityReport)
    if project_id:
        query = query.filter(QualityReport.project_id == project_id)
    if model_id:
        query = query.filter(QualityReport.model_id == model_id)
    return query.all()


@router.get("/quality/reports/{report_id}", response_model=QualityReportResponse)
def get_quality_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(QualityReport).filter(QualityReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/data/handover/")
def prepare_handover(request: DataHandoverRequest, db: Session = Depends(get_db)):
    """工程数据交接（简化版）"""
    model = db.query(ModelFile).filter(ModelFile.id == request.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    output_dir = settings.exports_path / f"handover_{model.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "model_id": request.model_id, "status": "prepared",
        "output_dir": str(output_dir), "formats": request.formats,
        "include_renders": request.include_renders,
        "include_documentation": request.include_documentation,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/parameters/")
def get_parameters():
    """获取参数树（简化版：返回汽车参数配置摘要）"""
    from ..car_generator import NURBSCarBodyGenerator
    gen = NURBSCarBodyGenerator()
    return gen.params


@router.get("/reports/{report_path:path}")
def get_report_file(report_path: str):
    full_path = settings.reports_path / report_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(str(full_path))


@router.get("/exports/{export_path:path}")
def get_export_file(export_path: str):
    full_path = settings.exports_path / export_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")
    return FileResponse(str(full_path))
