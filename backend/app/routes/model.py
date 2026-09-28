"""模型管理API路由（上传、查询、删除）

分级权限：GET 游客公开；上传/删除属于项目工作，需登录且仅限自己的项目
（管理员可代为处理）。
"""
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db, ModelFile, Project, User
from ..schemas import ModelFileResponse
from ..config import settings
from ..security import get_current_user, user_is_admin

router = APIRouter()


def _can_manage(user: User, project: Project) -> bool:
    return project.user_id == user.id or user_is_admin(user)


@router.post("/models/upload/", response_model=ModelFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_model(project_id: int, file: UploadFile = File(...),
                       current: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _can_manage(current, project):
        raise HTTPException(status_code=403, detail="无权向他人的项目上传模型")
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions_list:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}")
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {settings.MAX_FILE_SIZE / 1024 / 1024}MB")
    file_path = settings.models_path / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    db_model = ModelFile(
        project_id=project_id, filename=file.filename, filepath=str(file_path),
        file_type=file_ext[1:].upper(), file_size=file.size)
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
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
def delete_model(model_id: int,
                 current: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    project = db.query(Project).filter(Project.id == model.project_id).first()
    if not project or not _can_manage(current, project):
        raise HTTPException(status_code=403, detail="无权删除他人项目下的模型")
    if Path(model.filepath).exists():
        Path(model.filepath).unlink()
    db.delete(model)
    db.commit()
    return {"message": "Model deleted successfully"}
