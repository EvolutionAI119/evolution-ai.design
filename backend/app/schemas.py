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
    # 项目属主 ID（游客期/历史项目可能为空）
    user_id: Optional[int] = None
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


class TrainingReviewCreate(BaseModel):
    """训练产出接入预设审核工作流的请求体"""
    project_id: int
    task_id: int


class StepReviewCreate(BaseModel):
    """人工审核工作流步骤的结论（合规性/质量审核）"""
    approved: bool
    comment: Optional[str] = Field(None, max_length=500)


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


# ============ 导入改参导出 ============

class ParamOverrideItem(BaseModel):
    group: str = Field(..., description="参数分组，如 整车尺寸/车身部件/造型角度")
    key: str = Field(..., description="参数键名，如 overall_length")
    value: float = Field(..., description="新参数值")


class ParamModifyRequest(BaseModel):
    overrides: List[ParamOverrideItem] = Field(..., description="要修改的参数列表")


class ImportModelRequest(BaseModel):
    params: Optional[Dict[str, Dict[str, float]]] = Field(
        None, description="参数覆盖字典 {group: {key: value}}，为空则使用默认参数")
    name: Optional[str] = Field(None, description="模型名称")


class ExportFromSessionRequest(BaseModel):
    formats: List[str] = Field(default=["step"], description="导出格式：step/stl/obj/glb/json")
    name: Optional[str] = Field(None, description="导出文件名（不含扩展名）")


class SessionResponse(BaseModel):
    session_id: str
    name: str
    param_count: int
    created_at: str
    source_format: Optional[str] = Field(None, description="导入源格式标签，如 .step / .catpart / .json")
    warnings: Optional[List[str]] = Field(None, description="导入时产生的警告（如单位转换、几何解析回退）")
    bbox_size_mm: Optional[List[float]] = Field(None, description="整车包围盒尺寸 [长度, 高度, 宽度] mm（几何解析成功时才有）")
    overrides_count: Optional[int] = Field(None, description="通过 CAD 几何反推得到的参数覆盖数量")
    meta: Optional[Dict[str, Any]] = Field(None, description="其它元信息（原始文件引用、解析状态等）")
    # 导入后图片预览契约：前端 Deliver / Designer 直接用 brandKey / modelKey 匹配真车图，
    # 未命中品牌/车型时走运行时 SVG 兜底，保证整车数据导入后必有图可显示。
    inferred_brand_key: Optional[str] = Field(None, description="从文件名/名称推断的品牌稳定键，如 rolls-royce")
    inferred_model_key: Optional[str] = Field(None, description="从文件名/名称推断的车型稳定键，如 phantom")
    preview_url: Optional[str] = Field(None, description="3D 部件预览接口：/api/v1/import-export/{sid}/preview（供前端渲染三维缩略图）")


class ParamInfoResponse(BaseModel):
    # 为前端 i18n 提供稳定英文键：前端一律以 group_key / key 拼接 t()，不直出中文。
    group: str = Field(..., description="分组中文显示名（保留向后兼容，前端不直接渲染）")
    group_key: str = Field(..., description="分组稳定英文键，如 overall_dimensions / body_components / styling_angles / class_a_params / proportions")
    key: str = Field(..., description="参数稳定英文键，如 overall_length，可直接作为 i18n key")
    name: str = Field(..., description="参数中文显示名（保留向后兼容，前端不直接渲染）")
    value: float
    unit: str
    type: str
    min_value: float
    max_value: float
    category: str
