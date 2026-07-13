from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import shutil

from app.models.database import SessionLocal, Project, ModelFile, Workflow, WorkflowStep, QualityReport
from app.schemas.base import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ModelFileCreate, ModelFileResponse,
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    WorkflowStepResponse,
    TopologyOptimizationRequest,
    QualityCheckRequest,
    DataHandoverRequest,
    QualityReportResponse
)
from app.modules.topology_optimizer import TopologyOptimizer
from app.modules.quality_checker import QualityChecker
from app.modules.data_handover import DataHandover
from app.modules.parameterization import ParameterManager
from app.config.settings import settings
from app.utils.logger import logger

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/projects/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = Project(name=project.name, description=project.description)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    logger.info(f"Created project: {project.name}")
    return db_project


@router.get("/projects/", response_model=List[ProjectResponse])
def get_projects(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Project)
    if status:
        query = query.filter(Project.status == status)
    return query.all()


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project: ProjectUpdate, db: Session = Depends(get_db)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.name:
        db_project.name = project.name
    if project.description:
        db_project.description = project.description
    if project.status:
        db_project.status = project.status

    db_project.updated_at = datetime.now()
    db.commit()
    db.refresh(db_project)
    return db_project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}


@router.post("/models/upload/", response_model=ModelFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_model(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions_list:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}")

    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {settings.MAX_FILE_SIZE / 1024 / 1024}MB")

    file_path = settings.models_path / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_model = ModelFile(
        project_id=project_id,
        filename=file.filename,
        filepath=str(file_path),
        file_type=file_ext[1:].upper(),
        file_size=file.size
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)

    logger.info(f"Uploaded model: {file.filename} to project {project_id}")
    return db_model


@router.get("/models/", response_model=List[ModelFileResponse])
def get_models(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(ModelFile)
    if project_id:
        query = query.filter(ModelFile.project_id == project_id)
    return query.all()


@router.get("/models/{model_id}", response_model=ModelFileResponse)
def get_model(model_id: int, db: Session = Depends(get_db)):
    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.delete("/models/{model_id}")
def delete_model(model_id: int, db: Session = Depends(get_db)):
    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if Path(model.filepath).exists():
        Path(model.filepath).unlink()

    db.delete(model)
    db.commit()
    return {"message": "Model deleted successfully"}


@router.post("/topology/optimize/")
def optimize_topology(request: TopologyOptimizationRequest, db: Session = Depends(get_db)):
    model = db.query(ModelFile).filter(ModelFile.id == request.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    config = {
        'target_faces': request.target_faces,
        'min_quad_ratio': request.min_quad_ratio,
        'fix_normals': request.fix_normals,
        'merge_vertices': request.merge_vertices
    }

    optimizer = TopologyOptimizer(config)
    try:
        result = optimizer.process(model.filepath)
        return result
    except Exception as e:
        logger.error(f"Topology optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality/check/")
def check_quality(request: QualityCheckRequest, db: Session = Depends(get_db)):
    model = db.query(ModelFile).filter(ModelFile.id == request.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    config = {
        'output': {
            'generate_html': request.generate_html,
            'generate_json': request.generate_json
        }
    }

    checker = QualityChecker(model.filepath, config)
    try:
        result = checker.run_all_checks()

        db_report = QualityReport(
            project_id=model.project_id,
            model_id=model.id,
            overall_score=result['score'],
            passed=result['passed'],
            report_data=str(result),
            report_path=result.get('report_path')
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)

        return {**result, 'report_id': db_report.id}
    except Exception as e:
        logger.error(f"Quality check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality/reports/", response_model=List[QualityReportResponse])
def get_quality_reports(project_id: Optional[int] = None, model_id: Optional[int] = None, db: Session = Depends(get_db)):
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
    model = db.query(ModelFile).filter(ModelFile.id == request.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    output_dir = settings.exports_path / f"handover_{model.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    config = {
        'formats': request.formats,
        'include_renders': request.include_renders,
        'include_documentation': request.include_documentation
    }

    handover = DataHandover(model.filepath, str(output_dir), config)
    try:
        result = handover.prepare_handover()
        return result
    except Exception as e:
        logger.error(f"Data handover failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters/")
def get_parameters(project_id: Optional[int] = None):
    pm = ParameterManager(project_id)
    return pm.get_param_tree()


@router.get("/parameters/{param_name}")
def get_parameter(param_name: str, project_id: Optional[int] = None):
    pm = ParameterManager(project_id)
    param = pm.get_parameter(param_name)
    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")
    return param.to_dict()


@router.put("/parameters/{param_name}")
def update_parameter(param_name: str, value: Any, project_id: Optional[int] = None):
    pm = ParameterManager(project_id)
    success = pm.update_parameter(param_name, value)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to update parameter {param_name}")
    return {"message": f"Parameter {param_name} updated successfully", "value": value}


@router.post("/parameters/validate/")
def validate_parameters(project_id: Optional[int] = None):
    pm = ParameterManager(project_id)
    result = pm.validate_parameters()
    return result


@router.post("/workflows/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(workflow: WorkflowCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == workflow.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_workflow = Workflow(name=workflow.name, project_id=workflow.project_id, type=workflow.type)
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    logger.info(f"Created workflow: {workflow.name}")
    return db_workflow


@router.get("/workflows/", response_model=List[WorkflowResponse])
def get_workflows(project_id: Optional[int] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Workflow)
    if project_id:
        query = query.filter(Workflow.project_id == project_id)
    if status:
        query = query.filter(Workflow.status == status)
    return query.all()


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.post("/workflows/{workflow_id}/execute")
def execute_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow.status == "running":
        raise HTTPException(status_code=400, detail="Workflow is already running")

    workflow.status = "running"
    db.commit()

    steps_config = {
        "full": [
            {"name": "拓扑优化", "type": "topology"},
            {"name": "质量检查", "type": "quality"},
            {"name": "工程数据交接", "type": "handover"}
        ],
        "topology": [
            {"name": "拓扑优化", "type": "topology"}
        ],
        "quality": [
            {"name": "质量检查", "type": "quality"}
        ],
        "handover": [
            {"name": "工程数据交接", "type": "handover"}
        ]
    }

    steps = steps_config.get(workflow.type, [])
    project_models = db.query(ModelFile).filter(ModelFile.project_id == workflow.project_id).all()
    model_id = project_models[0].id if project_models else None

    for idx, step_config in enumerate(steps):
        step = WorkflowStep(
            workflow_id=workflow.id,
            model_id=model_id,
            step_name=step_config["name"],
            step_type=step_config["type"],
            status="pending",
            progress=0.0
        )
        db.add(step)

    db.commit()

    for step in workflow.steps:
        step.status = "running"
        step.started_at = datetime.now()
        step.progress = 30.0
        db.commit()

        if step.step_type == "topology":
            step.progress = 60.0
            db.commit()
            try:
                if model_id:
                    config = {'target_faces': 30000, 'min_quad_ratio': 0.75, 'fix_normals': True, 'merge_vertices': True}
                    optimizer = TopologyOptimizer(config)
                    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
                    if model and model.filepath:
                        result = optimizer.process(model.filepath)
                        step.output_data = str(result)
                    else:
                        step.output_data = '{"status": "skipped", "reason": "no model file"}'
                else:
                    step.output_data = '{"status": "skipped", "reason": "no model in project"}'
            except Exception as e:
                step.error_message = str(e)
                step.status = "failed"
                workflow.status = "failed"
                step.completed_at = datetime.now()
                db.commit()
                return {"message": f"Workflow failed at step {step.step_name}", "error": str(e)}

        elif step.step_type == "quality":
            step.progress = 60.0
            db.commit()
            try:
                if model_id:
                    config = {'output': {'generate_html': True, 'generate_json': True}}
                    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
                    if model and model.filepath:
                        checker = QualityChecker(model.filepath, config)
                        result = checker.run_all_checks()
                        step.output_data = str(result)
                    else:
                        step.output_data = '{"status": "skipped", "reason": "no model file"}'
                else:
                    step.output_data = '{"status": "skipped", "reason": "no model in project"}'
            except Exception as e:
                step.error_message = str(e)
                step.status = "failed"
                workflow.status = "failed"
                step.completed_at = datetime.now()
                db.commit()
                return {"message": f"Workflow failed at step {step.step_name}", "error": str(e)}

        elif step.step_type == "handover":
            step.progress = 60.0
            db.commit()
            try:
                if model_id:
                    output_dir = settings.exports_path / f"handover_{workflow.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    config = {'formats': ["IGES", "STEP"], 'include_renders': True, 'include_documentation': True}
                    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
                    if model and model.filepath:
                        handover = DataHandover(model.filepath, str(output_dir), config)
                        result = handover.prepare_handover()
                        step.output_data = str(result)
                    else:
                        step.output_data = '{"status": "skipped", "reason": "no model file"}'
                else:
                    step.output_data = '{"status": "skipped", "reason": "no model in project"}'
            except Exception as e:
                step.error_message = str(e)
                step.status = "failed"
                workflow.status = "failed"
                step.completed_at = datetime.now()
                db.commit()
                return {"message": f"Workflow failed at step {step.step_name}", "error": str(e)}

        step.progress = 100.0
        step.status = "completed"
        step.completed_at = datetime.now()
        db.commit()

    workflow.status = "completed"
    workflow.completed_at = datetime.now()
    db.commit()

    logger.info(f"Workflow {workflow.name} executed successfully")
    return {"message": "Workflow executed successfully", "workflow_id": workflow_id}


@router.get("/workflows/{workflow_id}/steps")
def get_workflow_steps(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    result = []
    for step in workflow.steps:
        step_dict = step.__dict__.copy()
        step_dict.pop('_sa_instance_state', None)
        if step_dict.get('output_data') and isinstance(step_dict['output_data'], str):
            try:
                step_dict['output_data'] = eval(step_dict['output_data'])
            except:
                step_dict['output_data'] = None
        result.append(step_dict)
    
    return result


@router.put("/workflows/{workflow_id}")
def update_workflow(workflow_id: int, workflow_update: WorkflowUpdate, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow_update.status:
        workflow.status = workflow_update.status

    db.commit()
    db.refresh(workflow)
    return workflow


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    db.delete(workflow)
    db.commit()
    return {"message": "Workflow deleted successfully"}


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


@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "EVOLUTION AI"}


@router.get("/i18n/config")
def get_i18n_config():
    return {
        "default_language": settings.DEFAULT_LANGUAGE,
        "supported_languages": settings.supported_languages_list,
        "current_language": settings.DEFAULT_LANGUAGE
    }