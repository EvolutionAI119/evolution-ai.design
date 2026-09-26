"""参数化纹理设计 API

输入设计纹样图，自动分析视觉特征（方向/圆润度/复杂度/对称性/色调等），
并映射为汽车参数覆盖（overrides），实现"看纹样自动调参"。

端点：
  GET  /api/v1/texture/regions          列出可选目标部位
  POST /api/v1/texture/analyze          上传纹样图 → 返回特征 + 参数覆盖
  POST /api/v1/texture/apply/{sid}      上传纹样图 → 直接应用到会话并重新生成
"""
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from ..texture_analyzer import analyze_texture, list_target_regions
from ..clip_semantics import (
    analyze_with_semantics,
    is_available as is_clip_available,
    get_load_error,
    TORCH_AVAILABLE as CLIP_TORCH_READY,
)
from ..session_store import get_session_store

router = APIRouter(prefix="/api/v1/texture", tags=["参数化纹理设计"])


@router.get("/regions")
async def get_target_regions():
    """列出可选的目标部位"""
    return {
        "regions": list_target_regions(),
        "description": {
            "整车": "影响整体比例与造型风格",
            "引擎盖": "影响发动机盖尺寸与角度",
            "车顶": "影响车顶与风挡造型",
            "翼子板": "影响轮拱与车轮",
            "前脸": "影响前保险杠、格栅、大灯",
            "尾部": "影响后保险杠、尾灯、行李箱",
        },
        "semantic": {
            "available": is_clip_available(),
            "error": get_load_error() if not is_clip_available() else None,
            "model": "openai/clip-vit-base-patch32",
            "axes": ["运动感", "豪华感", "科技感", "硬朗感", "简约感", "自然感"],
            "note": "CLIP 语义特征可用时，/analyze 与 /apply 默认启用几何+语义融合分析",
        },
    }


@router.post("/analyze")
async def analyze_texture_image(
    image: UploadFile = File(..., description="设计纹样图（PNG/JPG/BMP）"),
    target_region: str = Form("整车", description="目标部位，见 GET /regions"),
    intensity: float = Form(0.5, description="调参强度 0~1"),
    use_semantic: bool = Form(True, description="启用 CLIP 语义融合（权重不可用时自动回退纯几何）"),
    semantic_weight: float = Form(0.4, description="语义权重 0~1（0=纯几何，1=纯语义）"),
):
    """上传纹样图，分析视觉特征并生成参数覆盖

    返回：
      - features: 提取的 7 维几何特征
      - semantic: CLIP 语义特征（运动感/豪华感/科技感等 6 轴 + 风格关键词），不可用时为 null
      - target_region: 选定的目标部位
      - overrides: 参数覆盖字典 {group: {key: value}}（几何+语义融合）
      - param_count: 调整的参数数量
    """
    if target_region not in list_target_regions():
        raise HTTPException(
            status_code=400,
            detail=f"未知目标部位: {target_region}，可选: {list_target_regions()}",
        )
    if not 0.0 <= intensity <= 1.0:
        raise HTTPException(status_code=400, detail="intensity 必须在 0~1 之间")
    if not 0.0 <= semantic_weight <= 1.0:
        raise HTTPException(status_code=400, detail="semantic_weight 必须在 0~1 之间")

    # 读取图片
    img_bytes = await image.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="图片为空")

    try:
        if use_semantic:
            result = analyze_with_semantics(
                img_bytes, target_region, intensity, semantic_weight
            )
        else:
            result = analyze_texture(img_bytes, target_region=target_region, intensity=intensity)
            result["semantic"] = None
            result["semantic_available"] = False
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"缺少依赖: {e}，请安装 Pillow 和 numpy")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"纹样分析失败: {e}")

    return result


@router.post("/apply/{session_id}")
async def apply_texture_to_session(
    session_id: str,
    image: UploadFile = File(..., description="设计纹样图"),
    target_region: str = Form("整车"),
    intensity: float = Form(0.5),
    use_semantic: bool = Form(True, description="启用 CLIP 语义融合（不可用时自动回退纯几何）"),
    semantic_weight: float = Form(0.4, description="语义权重 0~1"),
    auto_render: bool = Form(True, description="是否立即重新生成几何"),
):
    """上传纹样图，直接应用到已有会话的参数并可选重新生成几何

    工作流：
      1. 分析纹样图（几何+语义融合）→ 得到 overrides
      2. 把 overrides 应用到 session_id 对应的会话
      3. 如果 auto_render=true，重新生成几何（返回预览点云）
    """
    store = get_session_store()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} 不存在")

    if target_region not in list_target_regions():
        raise HTTPException(status_code=400, detail=f"未知目标部位: {target_region}")

    img_bytes = await image.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="图片为空")

    # 分析纹样（几何+语义融合）
    try:
        if use_semantic:
            result = analyze_with_semantics(img_bytes, target_region, intensity, semantic_weight)
        else:
            result = analyze_texture(img_bytes, target_region=target_region, intensity=intensity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"纹样分析失败: {e}")

    overrides = result["overrides"]

    # 应用到会话
    params = session["config"]["automotive_parameters"]
    applied = []
    for group, items in overrides.items():
        if group in params:
            for key, val in items.items():
                if key in params[group]:
                    meta = params[group][key]
                    # min/max 校验
                    if "min_value" in meta and "max_value" in meta:
                        val = max(meta["min_value"], min(meta["max_value"], val))
                    meta["value"] = val
                    session.setdefault("overrides", {}).setdefault(group, {})[key] = val
                    applied.append({"group": group, "key": key, "value": val})

    # 持久化
    store.set(session_id, session)

    resp = {
        "session_id": session_id,
        "features": result["features"],
        "semantic": result.get("semantic"),
        "semantic_available": result.get("semantic_available", False),
        "target_region": target_region,
        "intensity": intensity,
        "applied_params": applied,
        "param_count": len(applied),
    }

    # 可选重新生成几何
    if auto_render:
        try:
            from ..car_generator import NURBSCarBodyGenerator

            gen = NURBSCarBodyGenerator(config_override=session.get("overrides"))
            car = gen.generate_complete_car()
            components = []
            for comp in car.get("components", []):
                components.append({
                    "name": comp.get("name"), "type": comp.get("type"),
                    "points": comp.get("points"), "color": comp.get("color", "#c0c0c0"),
                    "opacity": comp.get("opacity", 1.0),
                    "position": comp.get("position", {"x": 0, "y": 0, "z": 0}),
                })
            resp["preview"] = {
                "components": components,
                "total_surfaces": car.get("total_surfaces", len(components)),
            }
            resp["rendered"] = True
        except Exception as e:
            resp["rendered"] = False
            resp["render_error"] = str(e)

    return resp
