"""导入数字模型 → 更改参数 → 导出 全流程API

支持完整工作流：
1. 导入参数化模型（JSON 文件上传 / 内联JSON参数体 / STEP / IGES / STL / OBJ / CATPart / Wire 等整车 CAD 文件）
2. 查询当前参数列表（含名称/单位/范围/分类）
3. 修改任意参数（分组+键+值，带min/max校验）
4. 导出修改后的模型为 STEP / STL / OBJ / GLB / JSON / 原 CAD 文件
5. 获取3D预览数据（部件点云）
6. 导出参数快照（JSON，便于下次导入复用）
"""
import time
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from ..car_generator import NURBSCarBodyGenerator
from ..config import settings
from ..schemas import (
    ImportModelRequest, ParamModifyRequest, ExportFromSessionRequest,
    SessionResponse, ParamInfoResponse,
)
from ..session_store import get_session_store
from ..cad_importer import CAD_FORMAT_EXTENSIONS, import_cad_file
from ..utils.import_preview import (
    DEFAULT_INFERRER,
    build_preview_contract,
    normalize_keyword as _norm,
)

router = APIRouter(prefix="/api/v1/import-export", tags=["导入改参导出"])


# ============== 分组中文名 ↔ 英文稳定键 双向映射 ==============
# 前端所有显示与 i18n key 统一使用英文稳定键；后端保留中文原有 key（ automotive_parameters.json 不变）。
GROUP_ZH_TO_EN = {
    "整车尺寸": "overall_dimensions",
    "车身部件": "body_components",
    "造型角度": "styling_angles",
    "A级曲面参数": "class_a_params",
    "比例参数": "proportions",
}
GROUP_EN_TO_ZH = {v: k for k, v in GROUP_ZH_TO_EN.items()}


# 对外兼容旧符号：_BRAND_MODEL_CATALOG / _MODEL_FALLBACK_BY_KEYWORD / _infer_brand_model
# 仍能从 import_export 引用（其他模块/旧 E2E 测试不必改），但底层逻辑都复用 utils。
_BRAND_MODEL_CATALOG = DEFAULT_INFERRER.catalog
_MODEL_FALLBACK_BY_KEYWORD = list(DEFAULT_INFERRER.fallback_keywords)


def _infer_brand_model(name_text: Optional[str]) -> (Optional[str], Optional[str]):
    """老的入口（复用 BrandModelInferrer 默认单例），保持与 E2E 测试兼容"""
    return DEFAULT_INFERRER.infer(name_text)


def _normalize_group(params: dict, group: str) -> str:
    """把分组名规范化为 automotive_parameters.json 中使用的中文 key。
    支持三种输入：中文原名 / 英文稳定键 / JSON 默认 key。
    若找不到，原样返回（调用方仍会校验并报 422）。
    """
    if group in params:
        return group
    zh = GROUP_EN_TO_ZH.get(group)
    if zh and zh in params:
        return zh
    return group


def _group_key(group_zh: str) -> str:
    """返回分组英文稳定键；找不到时回退为把中文直接 slug（兜底避免崩溃）"""
    return GROUP_ZH_TO_EN.get(group_zh, group_zh)


def _get_sid(session_id: str) -> dict:
    """读取会话，不存在时抛出 404"""
    store = get_session_store()
    s = store.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


def _save_sid(session_id: str, s: dict) -> None:
    """保存会话（每次参数修改后调用，确保 Redis 写入）"""
    get_session_store().set(session_id, s)

# 支持的导出格式
_EXPORT_FORMATS = {
    "glb":  {"ext": ".glb",  "mime": "model/gltf-binary"},
    "gltf": {"ext": ".gltf", "mime": "model/gltf+json"},
    "stl":  {"ext": ".stl",  "mime": "model/stl"},
    "obj":  {"ext": ".obj",  "mime": "model/obj"},
    "step": {"ext": ".step", "mime": "model/step"},
    "stp":  {"ext": ".stp",  "mime": "model/step"},
    "iges": {"ext": ".iges", "mime": "model/iges"},
    "igs":  {"ext": ".igs",  "mime": "model/iges"},
    "json": {"ext": ".json", "mime": "application/json"},
}


def _load_default_config() -> dict:
    """加载默认参数配置（深拷贝避免污染）"""
    config_path = Path(__file__).parent.parent.parent / "config" / "automotive_parameters.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _flatten_params(params: dict) -> List[dict]:
    """将 {group: {key: {name,value,...}}} 展平为列表，并附带英文稳定键用于前端 i18n"""
    result = []
    for group_zh, items in params.items():
        gk = _group_key(group_zh)
        for key, meta in items.items():
            if isinstance(meta, dict) and "value" in meta:
                result.append({
                    "group": group_zh,
                    "group_key": gk,
                    "key": key,
                    "name": meta.get("name", key),
                    "value": meta["value"],
                    "unit": meta.get("unit", ""),
                    "type": meta.get("type", ""),
                    "min_value": meta.get("min_value", 0),
                    "max_value": meta.get("max_value", 9999),
                    "category": meta.get("category", ""),
                })
    return result


def _validate_override(params: dict, group: str, key: str, value: float) -> Optional[str]:
    """校验参数值是否在合法范围内。支持传入中文或英文分组名。"""
    g = _normalize_group(params, group)
    if g not in params:
        return f"Parameter group '{group}' does not exist"
    if key not in params[g]:
        return f"Parameter '{key}' does not exist in group '{group}'"
    meta = params[g][key]
    if not isinstance(meta, dict) or "value" not in meta:
        return f"Parameter '{group}.{key}' has invalid structure"
    lo = meta.get("min_value", 0)
    hi = meta.get("max_value", 9999)
    if value < lo or value > hi:
        return f"Value {value} for '{group}.{key}' is out of range [{lo}, {hi}]"
    return None


def _create_session(config: dict, overrides: dict, name: Optional[str] = None,
                    extra_meta: Optional[Dict[str, Any]] = None) -> SessionResponse:
    """统一的会话创建 + 持久化逻辑，返回扩展了 meta/warnings 的 SessionResponse"""
    sid = uuid.uuid4().hex[:12]
    if not name:
        name = f"imported_model_{sid[:6]}"
    # 图片预览契约（品牌/车型推断 + preview_url）：复用到独立工具类，便于其他模块同样逻辑
    infer_original_filename = None
    if extra_meta:
        infer_original_filename = extra_meta.get("original_filename") or extra_meta.get("name")
    contract = build_preview_contract(
        session_id=sid,
        name=name,
        original_filename=infer_original_filename,
    )
    inferred_brand_key = contract["inferred_brand_key"]
    inferred_model_key = contract["inferred_model_key"]
    preview_url = contract["preview_url"]

    session_data = {
        "name": name,
        "config": config,
        "overrides": overrides,
        "created_at": datetime.now().isoformat(),
        "inferred_brand_key": inferred_brand_key,
        "inferred_model_key": inferred_model_key,
        "preview_url": preview_url,
    }
    if extra_meta:
        session_data["meta"] = extra_meta
    get_session_store().set(sid, session_data)
    param_count = sum(
        1 for g in config["automotive_parameters"].values()
        for k in g if isinstance(g[k], dict) and "value" in g[k]
    )
    overrides_count = sum(len(v) for v in overrides.values()) if overrides else 0
    resp = SessionResponse(
        session_id=sid,
        name=name,
        param_count=param_count,
        created_at=session_data["created_at"],
        overrides_count=overrides_count if overrides_count > 0 else None,
        inferred_brand_key=inferred_brand_key,
        inferred_model_key=inferred_model_key,
        preview_url=preview_url,
    )
    if extra_meta:
        resp.source_format = extra_meta.get("source_format")
        resp.warnings = extra_meta.get("warnings") or None
        resp.bbox_size_mm = extra_meta.get("bbox_size_mm")
        resp.meta = {k: v for k, v in extra_meta.items() if k not in ("warnings",)}
    return resp


# ============ 导入 ============

@router.post("/import", response_model=SessionResponse)
async def import_model(data: ImportModelRequest):
    """导入参数化数字模型（内联JSON参数体）

    请求体示例：
    ```json
    {
      "name": "EV-Sedan Concept",
      "params": {
        "整车尺寸": {"overall_length": 4800, "overall_width": 1850},
        "造型角度": {"windshield_angle": 65}
      }
    }
    ```
    params 为空或不传时使用默认参数。
    """
    config = _load_default_config()
    auto_params = config["automotive_parameters"]
    overrides = data.params or {}
    errors = []
    applied: Dict[str, Dict[str, float]] = {}
    for group, items in overrides.items():
        for key, val in items.items():
            err = _validate_override(auto_params, group, key, val)
            if err:
                errors.append(err)
                continue
            g = _normalize_group(auto_params, group)
            auto_params[g][key]["value"] = val
            applied.setdefault(g, {})[key] = val
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors[:5]))
    meta = {"source_format": ".json (inline)"}
    if data.name:
        meta["original_filename"] = data.name
    return _create_session(config, applied, name=data.name, extra_meta=meta)


@router.post("/import/file", response_model=SessionResponse)
async def import_model_file(file: UploadFile = File(...)):
    """通过上传文件导入参数化模型。支持多种格式：

    - **参数化 JSON**：
      * automotive_parameters.json 完整配置（要求 automotive_parameters/car_body_components/nurbs_surface_templates 三个顶层键齐全）
      * 扁平覆盖字典：`{group: {key: value}}`（例如 {"整车尺寸": {"overall_length": 5000}}）
    - **整车 CAD 文件**（几何 → 参数 反推）：
      * STEP / STP
      * IGES / IGS
      * STL / OBJ / GLB / GLTF
      * CATIA Part / Product / CGR（专有格式走兜底：默认参数 + 保存原文件供后续原样导出）
      * Wire (.wire / .wrl)（同专有格式兜底）

    几何反推为最佳努力策略：解析不到几何时回退为默认参数，warnings 字段会说明原因。
    """
    filename = (file.filename or "model").strip()
    ext = Path(filename).suffix.lower()
    raw = await file.read()

    # =============== JSON 参数文件 ===============
    if ext == ".json":
        try:
            uploaded = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise HTTPException(status_code=400, detail=f"JSON 解析失败: {e}")
        config = _load_default_config()
        overrides: Dict[str, Any] = {}
        meta: Dict[str, Any] = {"source_format": ".json (upload)"}
        if "automotive_parameters" in uploaded:
            required_top = ("automotive_parameters", "car_body_components", "nurbs_surface_templates")
            missing = [k for k in required_top if k not in uploaded]
            if missing:
                raise HTTPException(
                    status_code=422,
                    detail=f"上传的完整配置缺少必要顶层键: {missing}. 所需: {list(required_top)}"
                )
            config = uploaded
            default_cfg = _load_default_config()
            default_params = default_cfg["automotive_parameters"]
            uploaded_params = uploaded["automotive_parameters"]
            calc_overrides: Dict[str, Any] = {}
            applied_full: Dict[str, Dict[str, float]] = {}
            errors = []
            ap = config["automotive_parameters"]
            for group, items in uploaded_params.items():
                if group not in default_params:
                    # 规范化分组名（支持英文稳定键/中文 key）
                    norm_g = _normalize_group(default_params, group)
                    if norm_g not in default_params:
                        continue
                    group = norm_g
                for key, meta_in in items.items():
                    if not isinstance(meta_in, dict) or "value" not in meta_in:
                        continue
                    if key not in default_params.get(group, {}):
                        continue
                    val = meta_in["value"]
                    err = _validate_override(default_params, group, key, val)
                    if err:
                        errors.append(err)
                        continue
                    default_val = default_params[group][key].get("value")
                    if val != default_val:
                        calc_overrides.setdefault(group, {})[key] = val
                        applied_full.setdefault(group, {})[key] = val
            if errors:
                raise HTTPException(status_code=422, detail="; ".join(errors[:5]))
            overrides = calc_overrides
            meta["original_filename"] = filename
            return _create_session(config, applied_full,
                                   name=Path(filename).stem,
                                   extra_meta=meta)
        else:
            overrides = uploaded
            errors = []
            applied_json: Dict[str, Dict[str, float]] = {}
            ap = config["automotive_parameters"]
            for group, items in overrides.items():
                if not isinstance(items, dict):
                    continue
                for key, val in items.items():
                    err = _validate_override(ap, group, key, val)
                    if err:
                        errors.append(err)
                        continue
                    g = _normalize_group(ap, group)
                    ap[g][key]["value"] = val
                    applied_json.setdefault(g, {})[key] = val
            if errors:
                raise HTTPException(status_code=422, detail="; ".join(errors[:5]))
            meta["original_filename"] = filename
            return _create_session(config, applied_json,
                                   name=Path(filename).stem,
                                   extra_meta=meta)

    # =============== CAD 整车文件（STEP / IGES / STL / OBJ / CATPart / Wire ...） ===============
    if ext in CAD_FORMAT_EXTENSIONS:
        config = _load_default_config()
        try:
            result = import_cad_file(raw, filename, config)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"CAD 文件解析失败: {type(e).__name__}: {e}"
            )
        # 应用 overrides（经过 infer_car_params 内部的 min/max 钳制，一般不会校验失败，但仍做一次完整校验）
        errors = []
        ap = config["automotive_parameters"]
        applied_cad: Dict[str, Dict[str, float]] = {}
        for group, items in result.overrides.items():
            for key, val in items.items():
                err = _validate_override(ap, group, key, val)
                if err:
                    errors.append(err)
                    continue
                g = _normalize_group(ap, group)
                ap[g][key]["value"] = val
                applied_cad.setdefault(g, {})[key] = val
        if errors:
            raise HTTPException(status_code=422, detail="; ".join(errors[:5]))
        meta = result.to_meta()
        meta["warnings"] = result.warnings  # 顶层 warnings 与 SessionResponse.warnings 对齐
        meta["original_filename"] = filename
        return _create_session(config, applied_cad,
                               name=result.name,
                               extra_meta=meta)

    raise HTTPException(
        status_code=400,
        detail=(
            f"不支持的文件扩展名: {ext!r}。"
            f"支持: .json / .step / .stp / .iges / .igs / .stl / .obj / .glb / .gltf "
            f"/ .catpart / .catproduct / .cgr / .wire / .wrl"
        )
    )


# ============ 参数查询 ============

@router.get("/{session_id}/params", response_model=List[ParamInfoResponse])
async def get_params(session_id: str):
    """获取当前会话的所有参数（含名称/单位/范围/分类）"""
    s = _get_sid(session_id)
    return _flatten_params(s["config"]["automotive_parameters"])


@router.get("/{session_id}/params/groups")
async def get_param_groups(session_id: str):
    """获取参数分组概览。

    返回格式：
    - groups: 中文分组名 → count（保留向后兼容）
    - groups_en: 英文稳定键 → count（前端 i18n 渲染使用）
    """
    s = _get_sid(session_id)
    groups = {}
    groups_en = {}
    for group_zh, items in s["config"]["automotive_parameters"].items():
        count = sum(1 for v in items.values() if isinstance(v, dict) and "value" in v)
        groups[group_zh] = count
        groups_en[_group_key(group_zh)] = count
    return {"session_id": session_id, "groups": groups, "groups_en": groups_en}


# ============ 参数修改 ============

@router.put("/{session_id}/params", response_model=List[ParamInfoResponse])
async def modify_params(session_id: str, req: ParamModifyRequest):
    """修改参数（批量，带min/max校验）

    请求体示例（group 可为中文原名或英文稳定键）：
    ```json
    {
      "overrides": [
        {"group": "overall_dimensions", "key": "overall_length", "value": 5000},
        {"group": "styling_angles",     "key": "windshield_angle", "value": 60}
      ]
    }
    ```
    """
    s = _get_sid(session_id)
    params = s["config"]["automotive_parameters"]
    # 先全部校验
    errors = []
    for item in req.overrides:
        err = _validate_override(params, item.group, item.key, item.value)
        if err:
            errors.append(err)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors[:10]))
    # 再全部应用
    for item in req.overrides:
        g = _normalize_group(params, item.group)
        params[g][item.key]["value"] = item.value
        s["overrides"].setdefault(g, {})[item.key] = item.value
    # 持久化（关键：否则 Redis 中仍是旧值）
    _save_sid(session_id, s)
    # 返回修改过的参数
    changed = []
    for item in req.overrides:
        g = _normalize_group(params, item.group)
        meta = params[g][item.key]
        changed.append({
            "group": g,
            "group_key": _group_key(g),
            "key": item.key,
            "name": meta.get("name", item.key),
            "value": meta["value"],
            "unit": meta.get("unit", ""),
            "type": meta.get("type", ""),
            "min_value": meta.get("min_value", 0),
            "max_value": meta.get("max_value", 9999),
            "category": meta.get("category", ""),
        })
    return changed


# ============ 预览 ============

@router.get("/{session_id}/preview")
async def get_preview(session_id: str):
    """获取3D预览数据（部件点云 + 图片预览契约字段 inferred_*/svg_model/fallback）

    返回内容同时满足两种前端消费：
      1) 3D 点云渲染：components / total_surfaces
      2) useCarSessionImage 图片 fallback：inferred_brand_key / inferred_model_key / svg_model / fallback
    """
    s = _get_sid(session_id)
    overrides = s.get("overrides") or None
    generator = NURBSCarBodyGenerator(config_override=overrides)
    car = generator.generate_complete_car()
    # 只返回前端渲染需要的精简数据
    components = []
    for comp in car.get("components", []):
        components.append({
            "name": comp.get("name"), "type": comp.get("type"),
            "points": comp.get("points"), "color": comp.get("color", "#c0c0c0"),
            "opacity": comp.get("opacity", 1.0),
            "position": comp.get("position", {"x": 0, "y": 0, "z": 0}),
        })
    brand_key = s.get("inferred_brand_key")
    model_key = s.get("inferred_model_key")
    # svg_model：前端用它拼运行时 SVG；这里给个稳定值（车型或会话名 slug）
    svg_model = model_key or (s.get("name") or "").lower().replace(" ", "_") or "default"
    # fallback 层级：告诉 useCarSessionImage 最佳起始层
    if brand_key and model_key:
        fallback_layer = 1  # 本地 JPG 就有希望命中
    elif brand_key or model_key:
        fallback_layer = 3  # 只能走运行时 SVG
    else:
        fallback_layer = 4  # 完全兜底
    return {
        "session_id": session_id,
        "name": s["name"],
        "components": components,
        "total_surfaces": car.get("total_surfaces", len(components)),
        # 图片预览契约（供 useCarSessionImage 消费）
        "inferred_brand_key": brand_key,
        "inferred_model_key": model_key,
        "svg_model": svg_model,
        "fallback": fallback_layer,
    }


# ============ 导出 ============

@router.post("/{session_id}/export")
async def export_model(session_id: str, req: ExportFromSessionRequest):
    """导出修改后的模型为指定格式（STEP/STL/OBJ/GLB/JSON）

    返回下载URL，客户端可通过 GET /{session_id}/download/{filename} 下载。
    """
    s = _get_sid(session_id)
    invalid = [f for f in req.formats if f.lower() not in _EXPORT_FORMATS]
    if invalid:
        raise HTTPException(status_code=400,
                            detail=f"不支持的格式: {invalid}. 支持: {list(_EXPORT_FORMATS)}")
    overrides = s.get("overrides") or None
    generator = NURBSCarBodyGenerator(config_override=overrides)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = req.name or s["name"]
    export_dir = settings.exports_path / f"import_export_{session_id}_{ts}"
    export_dir.mkdir(parents=True, exist_ok=True)
    start = time.time()
    files = []
    for fmt in req.formats:
        fl = fmt.lower()
        info = _EXPORT_FORMATS[fl]
        out_name = f"{name}{info['ext']}"
        out_path = export_dir / out_name
        if fl == "json":
            car = generator.generate_complete_car()
            out_path.write_text(json.dumps(car, ensure_ascii=False, indent=2), encoding="utf-8")
        elif fl in ("stl", "obj", "glb", "gltf"):
            method = {"glb": generator.export_glb, "gltf": generator.export_glb,
                      "stl": generator.export_stl, "obj": generator.export_obj}[fl]
            method(str(out_path))
        elif fl in ("step", "stp", "iges", "igs"):
            generator.export_step(str(out_path))
        files.append({
            "format": fl, "filename": out_name, "path": str(out_path),
            "size": out_path.stat().st_size if out_path.exists() else 0,
            "download_url": f"/api/v1/import-export/{session_id}/download/{out_name}",
        })
    elapsed = (time.time() - start) * 1000
    return {
        "session_id": session_id, "name": name,
        "files": files, "export_time_ms": round(elapsed, 2),
        "export_dir": str(export_dir),
    }


@router.get("/{session_id}/download/{filename}")
async def download_exported(session_id: str, filename: str):
    """下载导出的文件"""
    # 只校验 session 是否存在（防止越权枚举路径）
    _get_sid(session_id)
    # 在 exports 目录中查找该 session 的文件
    if settings.exports_path.exists():
        for export_dir in sorted(settings.exports_path.iterdir(), reverse=True):
            if export_dir.is_dir() and export_dir.name.startswith(f"import_export_{session_id}"):
                fp = export_dir / filename
                if fp.exists():
                    ext = Path(filename).suffix.lower()
                    mime = "application/octet-stream"
                    for fmt, info in _EXPORT_FORMATS.items():
                        if info["ext"] == ext:
                            mime = info["mime"]
                            break
                    return FileResponse(path=str(fp), media_type=mime, filename=filename)
    raise HTTPException(status_code=404, detail="File not found. Export first via POST /{session_id}/export.")


# ============ 参数快照导出 ============

@router.get("/{session_id}/snapshot")
async def export_param_snapshot(session_id: str):
    """导出当前参数快照为JSON（便于下次导入复用）"""
    s = _get_sid(session_id)
    overrides = s.get("overrides") or {}
    return {
        "session_id": session_id,
        "name": s["name"],
        "params": overrides,
        "created_at": s["created_at"],
        "snapshot_at": datetime.now().isoformat(),
    }


# ============ 会话管理 ============

@router.get("/sessions")
async def list_sessions():
    """列出所有活跃会话"""
    store = get_session_store()
    result = []
    for sid in store.keys():
        s = store.get(sid)
        if not s:
            continue
        param_count = sum(
            1 for g in s["config"]["automotive_parameters"].values()
            for k in g if isinstance(g[k], dict) and "value" in g[k]
        )
        override_count = sum(
            len(items) for items in (s.get("overrides") or {}).values()
        )
        result.append({
            "session_id": sid,
            "name": s["name"],
            "param_count": param_count,
            "override_count": override_count,
            "created_at": s["created_at"],
            "inferred_brand_key": s.get("inferred_brand_key"),
            "inferred_model_key": s.get("inferred_model_key"),
            "preview_url": s.get("preview_url") or f"/api/v1/import-export/{sid}/preview",
            "source_format": (s.get("meta") or {}).get("source_format"),
        })
    return {
        "sessions": result,
        "total": len(result),
        "backend": store.backend,
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    store = get_session_store()
    # 先确认存在
    if store.get(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    store.delete(session_id)
    return {"success": True, "message": f"Session {session_id} deleted", "backend": store.backend}
