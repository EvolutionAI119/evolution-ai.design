"""项目管理API路由

分级权限边界：
- GET（项目浏览）：游客公开可访问；
- POST/PUT/DELETE（项目工作）：必须登录，且普通用户只能改自己的项目；
  管理员可处理无属主的历史项目及任意用户项目（用于排查问题）。
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db, Project, User
from ..schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from ..security import get_current_user, user_is_admin

router = APIRouter()


def _can_manage(user: User, project: Project) -> bool:
    """属主本人或管理员可管理项目。"""
    return project.user_id == user.id or user_is_admin(user)


@router.post("/projects/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate,
                   current: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    db_project = Project(name=project.name, description=project.description,
                         user_id=current.id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
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
def update_project(project_id: int, project: ProjectUpdate,
                   current: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _can_manage(current, db_project):
        raise HTTPException(status_code=403, detail="无权修改他人的项目")
    if project.name:
        db_project.name = project.name
    if project.description is not None:
        db_project.description = project.description
    if project.status:
        db_project.status = project.status
    db_project.updated_at = datetime.now()
    db.commit()
    db.refresh(db_project)
    return db_project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int,
                   current: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _can_manage(current, project):
        raise HTTPException(status_code=403, detail="无权删除他人的项目")
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}
