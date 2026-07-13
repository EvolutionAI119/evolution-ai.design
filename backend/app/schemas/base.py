from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


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


class QualityIssue(BaseModel):
    check_type: str
    location: str
    issue_type: str
    severity: str
    description: str
    suggestion: str
    check_time: Optional[str] = None


class CheckResult(BaseModel):
    check_type: str
    passed: bool
    score: float
    issues: List[Dict]
    check_time: str


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


class LearningParams(BaseModel):
    L: float = 5.10
    W: float = 1.99
    H: float = 1.51
    WB: float = 3.06
    FO: float = 0.85
    RO: float = 1.19
    GC: float = 0.14
    WR: float = 0.33
    TW: float = 1.66
    AA: float = 26.0
    CA: float = 40.0
    WL: float = 0.82
    WBulge: float = 0.03


class LearningRequest(BaseModel):
    seed_params: Optional[LearningParams] = None
    generations: Optional[int] = 50
    population_size: Optional[int] = 20
    benchmark_key: Optional[str] = None


class ModelLearningRequest(BaseModel):
    model_key: str
    generations: Optional[int] = 50
    population_size: Optional[int] = 20


class AutoLearningRequest(BaseModel):
    seed_params: Optional[LearningParams] = None
    interval: Optional[int] = 10000
    generations: Optional[int] = 20


class EvaluationResponse(BaseModel):
    total: float
    scores: Dict[str, float]
    params: Dict[str, float]
    timestamp: str


class LearningResponse(BaseModel):
    initial_score: float
    final_score: float
    improvement: float
    best_params: Dict[str, float]
    generations: int
    elapsed: float
    emergence_events: List[Dict]
    convergence_history: List[Dict]
    initial_scores: Dict[str, float]
    final_scores: Dict[str, float]


class ModelLearningResponse(LearningResponse):
    model_key: str
    model_name: str


class AutoLearningStatus(BaseModel):
    is_running: bool
    interval: int
    session: Optional[Dict] = None


class ModelInfo(BaseModel):
    key: str
    name: str
    params: Dict[str, float]


# ============ 车身生成 schemas ============

class CarGenerateRequest(BaseModel):
    """车身生成请求"""
    project_id: Optional[int] = None
    params_override: Optional[Dict[str, float]] = None


class CarComponentGenerateRequest(BaseModel):
    """单部件生成请求"""
    component: str = Field(..., description="部件名称: hood, windshield, roof, rear_window, trunk, door_front, door_rear, bumper_front, bumper_rear, headlight, taillight, grille, wheel, mirror, fender, pillar, door_seam")
    side: Optional[str] = Field("left", description="左右侧: left, right")
    position: Optional[str] = Field(None, description="前后位置: front, rear（仅 wheel/fender 使用）")
    pillar_type: Optional[str] = Field(None, description="立柱类型: A, B, C（仅 pillar 使用）")


class CarComponentResponse(BaseModel):
    """部件生成响应"""
    name: str
    type: str
    points: Optional[Any] = None
    color: Optional[str] = None
    opacity: Optional[float] = None
    position: Optional[Dict[str, float]] = None
    extra: Optional[Dict[str, Any]] = None


class CarCompleteResponse(BaseModel):
    """完整车身生成响应"""
    name: str
    components: List[Dict[str, Any]]
    total_surfaces: int
    parameters: Optional[Dict[str, Any]] = None


# ============ 模型构建 schemas ============

class ModelBuildRequest(BaseModel):
    """模型构建请求"""
    project_id: int
    params: Optional[Dict[str, float]] = None
    build_options: Optional[Dict[str, Any]] = None


class ModelRebuildRequest(BaseModel):
    """模型重建请求"""
    model_id: int
    params_override: Optional[Dict[str, float]] = None
    rebuild_components: Optional[List[str]] = None


class ModelBuildResponse(BaseModel):
    """模型构建响应"""
    model_id: int
    status: str
    components_count: int
    build_time_ms: float
    parameters_used: Dict[str, float]


# ============ 模型导出 schemas ============

class ModelExportRequest(BaseModel):
    """模型导出请求"""
    model_id: int
    formats: List[str] = Field(default=["glb"], description="导出格式: glb, stl, obj, iges, step")
    include_metadata: Optional[bool] = True
    precision: Optional[float] = Field(0.01, description="网格精度（mm）")


class ModelExportResponse(BaseModel):
    """模型导出响应"""
    model_id: int
    files: List[Dict[str, Any]]
    export_time_ms: float


# ============ 模型版本 schemas ============

class ModelVariantCreateRequest(BaseModel):
    """创建模型变体"""
    model_id: int
    name: str
    params_override: Optional[Dict[str, float]] = None
    description: Optional[str] = None


class ModelVariantResponse(BaseModel):
    """模型变体响应"""
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
    """模型对比请求"""
    model_id_a: int
    model_id_b: int
    compare_fields: Optional[List[str]] = None