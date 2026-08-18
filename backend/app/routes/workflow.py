"""工作流管理API路由"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db, Project, ModelFile, Workflow, WorkflowStep
from ..schemas import (WorkflowCreate, WorkflowUpdate, WorkflowResponse,
                       WorkflowStepResponse)

router = APIRouter()


@router.post("/workflows/", response_model=WorkflowResponse, status_code=201)
def create_workflow(workflow: WorkflowCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == workflow.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db_wf = Workflow(name=workflow.name, project_id=workflow.project_id, type=workflow.type)
    db.add(db_wf)
    db.commit()
    db.refresh(db_wf)
    return db_wf


@router.get("/workflows/", response_model=List[WorkflowResponse])
def get_workflows(project_id: Optional[int] = None, status: Optional[str] = None,
                  db: Session = Depends(get_db)):
    query = db.query(Workflow)
    if project_id:
        query = query.filter(Workflow.project_id == project_id)
    if status:
        query = query.filter(Workflow.status == status)
    return query.all()


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.post("/workflows/{workflow_id}/execute")
def execute_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """执行工作流（简化版：按步骤类型依次标记完成）"""
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.status == "running":
        raise HTTPException(status_code=400, detail="Workflow is already running")
    wf.status = "running"
    db.commit()
    steps_config = {
        "full": [("拓扑优化", "topology"), ("质量检查", "quality"), ("工程数据交接", "handover")],
        "topology": [("拓扑优化", "topology")],
        "quality": [("质量检查", "quality")],
        "handover": [("工程数据交接", "handover")],
    }
    steps = steps_config.get(wf.type, [])
    project_models = db.query(ModelFile).filter(ModelFile.project_id == wf.project_id).all()
    model_id = project_models[0].id if project_models else None
    for name, stype in steps:
        db.add(WorkflowStep(workflow_id=wf.id, model_id=model_id, step_name=name,
                            step_type=stype, status="pending", progress=0.0))
    db.commit()
    for step in wf.steps:
        step.status = "running"
        step.started_at = datetime.now()
        step.progress = 50.0
        db.commit()
        step.progress = 100.0
        step.status = "completed"
        step.completed_at = datetime.now()
        step.output_data = '{"status": "completed"}'
        db.commit()
    wf.status = "completed"
    wf.completed_at = datetime.now()
    db.commit()
    return {"message": "Workflow executed successfully", "workflow_id": workflow_id}


@router.get("/workflows/{workflow_id}/steps")
def get_workflow_steps(workflow_id: int, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    result = []
    for step in wf.steps:
        d = {c.name: getattr(step, c.name) for c in step.__table__.columns}
        result.append(d)
    return result


@router.put("/workflows/{workflow_id}")
def update_workflow(workflow_id: int, update: WorkflowUpdate, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if update.status:
        wf.status = update.status
    db.commit()
    db.refresh(wf)
    return wf


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(wf)
    db.commit()
    return {"message": "Workflow deleted successfully"}
