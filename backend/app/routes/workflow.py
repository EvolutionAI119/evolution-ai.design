"""工作流管理API路由"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db, Project, ModelFile, Workflow, WorkflowStep, TrainingTask, User
from ..schemas import (WorkflowCreate, WorkflowUpdate, WorkflowResponse,
                       WorkflowStepResponse, TrainingReviewCreate, StepReviewCreate)
from ..security import get_current_user

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


@router.post("/workflows/training-review", response_model=WorkflowResponse, status_code=201)
def create_training_review(
    payload: TrainingReviewCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """训练产出 → 预设审核工作流（需登录 Token）

    链路：训练任务完成 → 携带 Bearer Token 调用本接口 →
    在指定项目下创建 training_review 类型工作流，并预置两道人工审核步骤
    （合规性审核 compliance + 质量审核 quality_review）。
    步骤保持 pending，须经 /steps/{id}/review 逐级人工审核，不走自动执行通道。
    """
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # 归属校验：只能将本人训练产出接入审核
    task = db.query(TrainingTask).filter(
        TrainingTask.id == payload.task_id,
        TrainingTask.user_id == current.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Training task not found")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Training task is not completed")

    wf = Workflow(name=f"训练产出审核 · {task.name}"[:100],
                  project_id=project.id, type="training_review", status="pending")
    db.add(wf)
    db.commit()
    db.refresh(wf)

    # 汇总训练产出摘要，作为审核输入证据
    best_acc = None
    try:
        metrics = json.loads(task.metrics_json or "[]")
        if metrics:
            best_acc = round(max(m.get("val_acc", 0) for m in metrics), 4)
    except (ValueError, TypeError):
        pass
    audit_input = json.dumps({
        "task_id": task.id, "task_name": task.name, "dataset": task.dataset,
        "best_val_acc": best_acc, "submitted_by": current.email,
    }, ensure_ascii=False)
    for step_name, stype in (("合规性审核", "compliance"), ("质量审核", "quality_review")):
        db.add(WorkflowStep(workflow_id=wf.id, step_name=step_name, step_type=stype,
                            status="pending", progress=0.0, input_params=audit_input))
    db.commit()
    return wf


@router.post("/workflows/{workflow_id}/steps/{step_id}/review")
def review_workflow_step(
    workflow_id: int, step_id: int, review: StepReviewCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """人工审核工作流步骤（需登录 Token）：通过→completed，驳回→rejected"""
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    step = db.query(WorkflowStep).filter(
        WorkflowStep.id == step_id,
        WorkflowStep.workflow_id == workflow_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Workflow step not found")
    if step.step_type not in ("compliance", "quality_review"):
        raise HTTPException(status_code=400, detail="Step is not reviewable")
    if step.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Step already finalized")

    now = datetime.now()
    step.started_at = step.started_at or now
    verdict = json.dumps(
        {"approved": review.approved, "reviewer": current.email,
         "comment": review.comment or ""}, ensure_ascii=False)
    if review.approved:
        step.status = "completed"
        step.progress = 100.0
        step.completed_at = now
        step.output_data = verdict
    else:
        step.status = "rejected"
        step.completed_at = now
        step.output_data = verdict
        step.error_message = review.comment or "审核驳回"
    db.commit()

    # 审核状态机：任一驳回→failed；全部通过→completed；否则→running（审核中）
    steps = db.query(WorkflowStep).filter(WorkflowStep.workflow_id == workflow_id).all()
    if any(s.status == "rejected" for s in steps):
        wf.status = "failed"
        wf.completed_at = now
    elif all(s.status == "completed" for s in steps):
        wf.status = "completed"
        wf.completed_at = now
    else:
        wf.status = "running"
    db.commit()
    return {"message": "Review recorded", "workflow_id": workflow_id,
            "step_status": step.status, "workflow_status": wf.status}


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
    if wf.type == "training_review":
        # 审核工作流必须人工逐级审核，禁止自动完成通道绕过合规检查
        raise HTTPException(status_code=400,
                            detail="Review workflow requires manual step review")
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
