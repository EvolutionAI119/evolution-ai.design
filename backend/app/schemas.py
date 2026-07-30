"""Pydantic数据模型（请求/响应Schema）"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ 项目 ============

class ProjectBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    status: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 模型文件 ============

class ModelFileBase(BaseModel):
    filename: str = Field(..., max_length=255)
    file_type: Optional[str] = None


class ModelFileCreate(ModelFileBase):
    project_id: int
    filepath: str = Field(..., max_length=500)
    file_size: int


class ModelFileResponse(ModelFileBase):
    id: int
    project_id: int
    filepath: str
    file_size: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 工作流 ============

class WorkflowBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: str = Field(..., max_length=20)


class WorkflowCreate(WorkflowBase):
    project_id: int


class WorkflowUpdate(BaseModel):
    status: Optional[str] = None


class WorkflowResponse(WorkflowBase):
    id: int
    project_id: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class WorkflowStepBase(BaseModel):
    step_name: str = Field(..., max_length=50)
    step_type: str = Field(..., max_length=20)
    input_params: Optional[Dict] = None


class WorkflowStepCreate(WorkflowStepBase):
    workflow_id: int
    model_id: int


class WorkflowStepResponse(WorkflowStepBase):
    id: int
    workflow_id: int
    model_id: Optional[int] = None
    status: str
    progress: float
    output_data: Optional[Dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 质量检查 ============

class QualityReportResponse(BaseModel):
    id: int
    project_id: int
    model_id: int
    overall_score: float
    passed: bool
    report_data: Optional[Dict] = None
    report_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TopologyOptimizationRequest(BaseModel):
    model_id: int
    target_faces: Optional[int] = 30000
    min_quad_ratio: Optional[float] = 0.75
    fix_normals: Optional[bool] = True
    merge_vertices: Optional[bool] = True


class QualityCheckRequest(BaseModel):
    model_id: int
    generate_html: Optional[bool] = True
    generate_json: Optional[bool] = True


class DataHandoverRequest(BaseModel):
    model_id: int
    formats: Optional[List[str]] = ["IGES", "STEP", "JT"]
    include_renders: Optional[bool] = True
    include_documentation: Optional[bool] = True


# ============ 车身生成 ============

class CarGenerateRequest(BaseModel):
    project_id: Optional[int] = None
    params_override: Optional[Dict[str, float]] = None


class CarComponentGenerateRequest(BaseModel):
    component: str = Field(..., description="部件名称")
    side: Optional[str] = Field("left", description="left/right")
    position: Optional[str] = Field(None, description="front/rear")
    pillar_type: Optional[str] = Field(None, description="A/B/C")


class CarComponentResponse(BaseModel):
    name: str
    type: str
    points: Optional[Any] = None
    color: Optional[str] = None
    opacity: Optional[float] = None
    position: Optional[Dict[str, float]] = None
    extra: Optional[Dict[str, Any]] = None


class CarCompleteResponse(BaseModel):
    name: str
    components: List[Dict[str, Any]]
    total_surfaces: int
    parameters: Optional[Dict[str, Any]] = None


# ============ 模型构建 ============

class ModelBuildRequest(BaseModel):
    project_id: int
    params: Optional[Dict[str, float]] = None
    build_options: Optional[Dict[str, Any]] = None


class ModelRebuildRequest(BaseModel):
    model_id: int
    params_override: Optional[Dict[str, float]] = None
    rebuild_components: Optional[List[str]] = None


class ModelBuildResponse(BaseModel):
    model_id: int
    status: str
    components_count: int
    build_time_ms: float
    parameters_used: Dict[str, float]


# ============ 模型导出 ============

class ModelExportRequest(BaseModel):
    model_id: int
    formats: List[str] = Field(default=["glb"])
    include_metadata: Optional[bool] = True
    precision: Optional[float] = Field(0.01)


class ModelExportResponse(BaseModel):
    model_id: int
    files: List[Dict[str, Any]]
    export_time_ms: float


# ============ 模型变体 ============

class ModelVariantCreateRequest(BaseModel):
    model_id: int
    name: str
    params_override: Optional[Dict[str, float]] = None
    description: Optional[str] = None


class ModelVariantResponse(BaseModel):
    id: int
    name: str
    model_id: int
    parent_variant_id: Optional[int] = None
    params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ModelCompareRequest(BaseModel):
    model_id_a: int
    model_id_b: int
    compare_fields: Optional[List[str]] = None
