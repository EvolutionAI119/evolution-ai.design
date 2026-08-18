"""SQLAlchemy数据库引擎与ORM模型"""
from datetime import datetime
from sqlalchemy import (create_engine, Column, Integer, String, Float, Text,
                        DateTime, Boolean, ForeignKey)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

from .config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Project(Base):
    """项目"""
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    models = relationship("ModelFile", back_populates="project")
    workflows = relationship("Workflow", back_populates="project")
    reports = relationship("QualityReport", back_populates="project")


class ModelFile(Base):
    """模型文件（含构建参数与车身数据持久化）"""
    __tablename__ = "model_files"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    file_type = Column(String(20))
    file_size = Column(Integer)
    status = Column(String(20), default="uploaded")
    params_json = Column(Text, nullable=True, comment="构建参数JSON")
    car_data_json = Column(Text, nullable=True, comment="生成的车身数据JSON")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="models")
    workflow_steps = relationship("WorkflowStep", back_populates="model")
    variants = relationship("ModelVariant", back_populates="model", order_by="ModelVariant.id")


class Workflow(Base):
    """工作流"""
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String(100), nullable=False)
    type = Column(String(20))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    project = relationship("Project", back_populates="workflows")
    steps = relationship("WorkflowStep", back_populates="workflow")


class WorkflowStep(Base):
    """工作流步骤"""
    __tablename__ = "workflow_steps"
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    model_id = Column(Integer, ForeignKey("model_files.id"))
    step_name = Column(String(50), nullable=False)
    step_type = Column(String(20))
    status = Column(String(20), default="pending")
    progress = Column(Float, default=0.0)
    input_params = Column(Text)
    output_data = Column(Text)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    workflow = relationship("Workflow", back_populates="steps")
    model = relationship("ModelFile", back_populates="workflow_steps")


class QualityReport(Base):
    """质量报告"""
    __tablename__ = "quality_reports"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    model_id = Column(Integer, ForeignKey("model_files.id"))
    overall_score = Column(Float)
    passed = Column(Boolean)
    report_data = Column(Text)
    report_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="reports")


class ParameterSet(Base):
    """参数集（Parameter）"""
    __tablename__ = "parameter_sets"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String(100), nullable=False)
    params = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project")


class ModelVariant(Base):
    """模型变体"""
    __tablename__ = "model_variants"
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("model_files.id"), nullable=False)
    name = Column(String(100), nullable=False)
    parent_variant_id = Column(Integer, ForeignKey("model_variants.id"), nullable=True)
    params_json = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    car_data_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("ModelFile", back_populates="variants")
    parent_variant = relationship("ModelVariant", remote_side=[id])


def init_db():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI依赖：提供数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
