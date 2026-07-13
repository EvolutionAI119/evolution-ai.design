from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from app.config.settings import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Project(Base):
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
    __tablename__ = "model_files"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    file_type = Column(String(20))
    file_size = Column(Integer)
    status = Column(String(20), default="uploaded")
    params_json = Column(Text, nullable=True, comment="构建参数JSON，用于变体对比")
    car_data_json = Column(Text, nullable=True, comment="生成的车身数据JSON，替代内存缓存")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="models")
    workflow_steps = relationship("WorkflowStep", back_populates="model")
    variants = relationship("ModelVariant", back_populates="model", order_by="ModelVariant.id")


class Workflow(Base):
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
    __tablename__ = "parameter_sets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String(100), nullable=False)
    params = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")


class ModelVariant(Base):
    __tablename__ = "model_variants"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("model_files.id"), nullable=False)
    name = Column(String(100), nullable=False)
    parent_variant_id = Column(Integer, ForeignKey("model_variants.id"), nullable=True)
    params_json = Column(Text, nullable=True, comment="变体参数JSON")
    description = Column(Text, nullable=True)
    car_data_json = Column(Text, nullable=True, comment="变体车身数据JSON")
    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("ModelFile", back_populates="variants")
    parent_variant = relationship("ModelVariant", remote_side=[id])


def init_db():
    Base.metadata.create_all(bind=engine)