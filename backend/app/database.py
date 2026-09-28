"""SQLAlchemy数据库引擎与ORM模型"""
from datetime import datetime
from sqlalchemy import (create_engine, Column, Integer, String, Float, Text,
                        DateTime, Boolean, ForeignKey, UniqueConstraint)
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
    # 项目属主：创建项目需登录，普通用户仅能修改/删除自己的项目
    # （历史项目/游客期创建的项目 user_id 为空，管理员可处理）
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    models = relationship("ModelFile", back_populates="project")
    workflows = relationship("Workflow", back_populates="project")
    reports = relationship("QualityReport", back_populates="project")
    owner = relationship("User", foreign_keys=[user_id])


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


class User(Base):
    """用户账户"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    # 微信扫码登录（开放平台 OpenID）
    wechat_unionid = Column(String(64), unique=True, index=True, nullable=True)
    wechat_openid = Column(String(64), unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    # 分级权限角色（权威字段）：
    #   user       普通用户（项目工作 / 模型生成）
    #   admin      管理员（排查问题 / 查看登录记录）
    #   superadmin 超级管理员（账户修复 / 后端错误与 BUG 调试）
    # is_admin 保留以兼容既有代码：role 为 admin/superadmin 时视为管理员
    role = Column(String(20), default="user", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    api_keys = relationship("ApiKey", back_populates="user",
                            cascade="all, delete-orphan")


class LoginRecord(Base):
    """登录记录：每次登录尝试（成功/失败）落地，供管理员排查与审计。"""
    __tablename__ = "login_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    email = Column(String(255), index=True)
    success = Column(Boolean, default=False, index=True)
    # 失败原因：bad_credentials / disabled / missing_code / network ...
    reason = Column(String(40), nullable=True)
    # 登录方式：password / mp / wechat
    method = Column(String(20), default="password")
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AdminAuditLog(Base):
    """管理员/超级管理员敏感操作审计日志（详细、可追溯）。"""
    __tablename__ = "admin_audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), index=True)
    # 操作动作：set_active / reset_password / set_role ...
    action = Column(String(40), index=True)
    target_type = Column(String(30), default="user")
    target_id = Column(Integer, nullable=True)
    # 操作详情 JSON（不含明文密码等敏感数据）
    detail_json = Column(Text, default="{}")
    ip = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ApiKey(Base):
    """用户配置的各 LLM 提供商 API Key（Fernet 加密存储）"""
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(30), nullable=False)   # ernie/qwen/hunyuan/doubao/deepseek/kimi
    key_encrypted = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="api_keys")
    # 同一用户同一提供商仅保留一条
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_api_keys_user_provider"),
    )


class ParameterRecord(Base):
    """参数持久化记录（替代 modify 路由的内存 _parameters）"""
    __tablename__ = "parameter_records"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrainingTask(Base):
    """AI 训练任务（PyTorch 训练状态持久化）"""
    __tablename__ = "training_tasks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(150), nullable=False)
    dataset = Column(String(100), default="synthetic")
    config_json = Column(Text, default="{}")         # epochs/batch_size/lr 等
    status = Column(String(20), default="pending")   # pending/running/completed/failed/cancelled
    progress = Column(Float, default=0.0)            # 0~100
    metrics_json = Column(Text, default="[]")        # 每轮 loss/acc 等
    logs = Column(Text, default="")                  # 训练日志
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


def init_db():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)
    _migrate_wechat_columns()
    _migrate_role_and_project_owner()


def _migrate_wechat_columns():
    """向已存在的 users 表补充 wechat_unionid / wechat_openid（SQLite 简化版）。"""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("users")}
    with engine.begin() as conn:
        if "wechat_unionid" not in existing:
            conn.execute(text("ALTER TABLE users ADD COLUMN wechat_unionid VARCHAR(64)"))
        if "wechat_openid" not in existing:
            conn.execute(text("ALTER TABLE users ADD COLUMN wechat_openid VARCHAR(64)"))


def _migrate_role_and_project_owner():
    """分级权限升级迁移（SQLite 简化版）：

    1. users.role 补列，并按 is_admin 回填：
       is_admin=1 → 'admin'，其余 → 'user'
    2. projects.user_id 补列（项目属主，历史项目留空）
    """
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "users" in tables:
        user_cols = {col["name"] for col in inspector.get_columns("users")}
        with engine.begin() as conn:
            if "role" not in user_cols:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN role VARCHAR(20) "
                    "NOT NULL DEFAULT 'user'"
                ))
                # 历史管理员账户提升为 admin 角色
                conn.execute(text(
                    "UPDATE users SET role='admin' WHERE is_admin=1"
                ))

    if "projects" in tables:
        proj_cols = {col["name"] for col in inspector.get_columns("projects")}
        if "user_id" not in proj_cols:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE projects ADD COLUMN user_id INTEGER"
                ))


def get_db():
    """FastAPI依赖：提供数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
