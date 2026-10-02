# -*- coding: utf-8 -*-
"""AI 设计意图引擎：自然语言 → 结构化整车设计方案

让用户用一句自然语言（"我要一台运动感强、风阻低的深色轿跑"）直接得到
可执行的整车设计方案：车型、风格标签、14 项几何参数、车身色、设计原理。

设计原则：
  1. LLM 只负责"理解意图"，所有输出必须经过白名单校验与范围钳制，
     模型永远无法把越界/非法参数直接送达生成器
  2. 无 Key / 上游故障 / 非法 JSON 均返回明确错误码，绝不静默伪造方案
  3. 与底层几何解耦：本模块不 import 生成器，输出契约对齐前端
     src/config/carPresets.js 的参数形状，由前端注入设计器
  4. 核心纯函数 sanitize_intent 独立可测，LLM 调用可 monkeypatch
"""
from __future__ import annotations

import os
import re
import json
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..rate_limit import limit

router = APIRouter(prefix="/api/v1/design-intent", tags=["AI 设计意图引擎"])

# ── 输出契约常量 ────────────────────────────────────────
CAR_TYPES = ("sedan", "suv", "coupe", "sport", "mpv", "pickup")

#: 参数白名单与钳制范围（mm / 度）。依据 src/config/carPresets.js 六车型
#: 实际参数取全局 min/max 后再留约 10% 余量，保证设计师自由又不越物理常识
PARAM_BOUNDS: Dict[str, tuple] = {
    "overall_length":    (3800, 6200),
    "overall_width":     (1750, 2100),
    "overall_height":    (1100, 2000),
    "wheel_base":        (2400, 3800),
    "track_width":       (1450, 1850),
    "ground_clearance":  (80, 300),
    "hood_length":       (700, 1700),
    "roof_height":       (300, 1100),
    "wheel_diameter":    (550, 850),
    "windshield_angle":  (20, 55),
    "rear_window_angle": (10, 50),
    "rear_slant_angle":  (5, 60),
    "front_overhang":    (600, 1300),
    "rear_overhang":     (600, 1400),
}

_STYLE_VOCAB = (
    "运动", "豪华", "优雅", "硬朗", "圆润", "肌肉感", "流线", "低风阻",
    "科技", "复古", "稳重", "大气", "紧凑", "越野", "商务", "年轻",
)

_SILICONFLOW_URL = "https://api.siliconflow.cn/v1/chat/completions"
_LLM_MODEL = "Qwen/Qwen2.5-72B-Instruct"
_LLM_TIMEOUT = 45.0

_SYSTEM_PROMPT = f"""你是 EVOLUTION-AI.DESIGN 平台的资深汽车造型设计师。用户会用自然语言描述想要的车，
你要把意图翻译为严格的整车参数方案。只输出一个 JSON 对象，不要任何解释文字或 markdown 代码块。

JSON 结构：
{{
  "car_type": 车型，必须是 {list(CAR_TYPES)} 之一,
  "style_tags": ["风格标签"],
  "params": {{
    "overall_length": 车长mm(3800~6200), "overall_width": 车宽mm(1750~2100),
    "overall_height": 车高mm(1100~2000), "wheel_base": 轴距mm(2400~3800),
    "track_width": 轮距mm(1450~1850), "ground_clearance": 离地间隙mm(80~300),
    "hood_length": 发动机盖长mm(700~1700), "roof_height": 车顶纵向跨度mm(300~1100),
    "wheel_diameter": 轮径mm(550~850), "windshield_angle": 前风挡角度度(20~55,越大越倾斜),
    "rear_window_angle": 后窗角度度(10~50), "rear_slant_angle": 尾部倾角度(5~60),
    "front_overhang": 前悬mm(600~1300), "rear_overhang": 后悬mm(600~1400)
  }},
  "color": {{"hex": "#十六进制颜色", "name": "颜色中文名"}},
  "rationale": "用中文说明这些参数如何回应用户意图（80字以内）",
  "confidence": 0.0到1.0的浮点数，表示你对意图把握程度
}}

规则：
- 车型词汇映射：用户说"轿跑"→coupe；"跑车/超跑"→sport；明确"轿车/三厢"→sedan；
  "越野车"→suv；"商务车/MPV"→mpv；"皮卡"→pickup
- style_tags 从下列词中挑选 2~5 个：{list(_STYLE_VOCAB)}
- 必须给出全部 14 个参数，数值严格落在给定范围内
- 几何自洽：车长 ≈ 前悬 + 轴距 + 后悬；运动/低风阻风格应降低车高、增大风挡倾角
- 用户没提到的维度，按该车型常规设计给出合理值
- 颜色 hex 必须是合法 #RRGGBB；若用户指定颜色则遵从
"""


# ── 请求模型 ────────────────────────────────────────────
class ParseRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=1000,
                        description="自然语言设计需求")


# ── 纯函数：校验 / 钳制 / 降级（无 IO，独立可测） ─────────
def _clamp(name: str, value: Any, warnings: List[str]) -> float:
    lo, hi = PARAM_BOUNDS[name]
    try:
        v = float(value)
    except (TypeError, ValueError):
        warnings.append(f"参数 {name} 非数值，回退为中值")
        return round((lo + hi) / 2, 1)
    if v != v:  # NaN
        warnings.append(f"参数 {name} 为 NaN，回退为中值")
        return round((lo + hi) / 2, 1)
    if v < lo:
        warnings.append(f"参数 {name}={value} 低于下限 {lo}，已钳制")
        v = lo
    elif v > hi:
        warnings.append(f"参数 {name}={value} 高于上限 {hi}，已钳制")
        v = hi
    # 角度取整数位，线性量保留到 mm 整数
    return round(v) if "angle" not in name else round(v, 1)


#: prompt 强信号词 → 车型（确定性校正优先于模型概率判断）。
#: 用户明确说出的车型词，比模型的语义猜测更可靠。
_PROMPT_CAR_HINTS = (
    ("coupe", ("轿跑",)),
    ("sport", ("超跑", "跑车")),
    ("pickup", ("皮卡",)),
    ("mpv", ("mpv", "MPV", "商务车", "七座")),
    ("suv", ("suv", "SUV", "越野")),
    ("sedan", ("三厢", "轿车")),
)


def sanitize_intent(raw: Dict[str, Any], prompt: str = "") -> Dict[str, Any]:
    """把 LLM 原始输出校验为合法方案；任何坏字段都安全降级而非抛异常。

    返回结构含 warnings 列表，记录所有被修正的字段（可追溯）。
    prompt 非空时，用其中的强信号词对车型做确定性校正。
    """
    warnings_out: List[str] = []

    car_type = raw.get("car_type")
    if car_type not in CAR_TYPES:
        warnings_out.append(f"非法车型 {car_type!r}，回退为 sedan")
        car_type = "sedan"

    # prompt 明确车型词 → 覆盖模型判断（用户意图优先）
    ptext = prompt or ""
    for hinted, words in _PROMPT_CAR_HINTS:
        if any(w in ptext for w in words):
            if car_type != hinted:
                warnings_out.append(
                    f"按需求中的车型词校正：{car_type} → {hinted}")
                car_type = hinted
            break

    raw_params = raw.get("params") or {}
    if not isinstance(raw_params, dict):
        warnings_out.append("params 非对象，全部回退为中值")
        raw_params = {}
    params = {name: _clamp(name, raw_params.get(name), warnings_out)
              for name in PARAM_BOUNDS}

    # 几何自洽守卫：车长与 前悬+轴距+后悬 偏差超 300mm 时报告（不强行改，
    # 让前端/用户可见；设计器滑杆会处理联动）
    span = params["front_overhang"] + params["wheel_base"] + params["rear_overhang"]
    if abs(span - params["overall_length"]) > 300:
        warnings_out.append(
            f"车长 {params['overall_length']} 与 前悬+轴距+后悬={span} 偏差较大")

    tags_raw = raw.get("style_tags") or []
    tags = [t for t in tags_raw if isinstance(t, str) and t in _STYLE_VOCAB]
    tags = list(dict.fromkeys(tags))[:5]
    if not tags:
        tags = ["稳重"]
        warnings_out.append("无有效风格标签，使用默认 [稳重]")

    color_raw = raw.get("color") or {}
    color = {"hex": "#374151", "name": "碳灰"}
    if isinstance(color_raw, dict):
        hx = str(color_raw.get("hex", "")).strip()
        if re.fullmatch(r"#[0-9a-fA-F]{6}", hx):
            color["hex"] = hx.lower()
            nm = color_raw.get("name")
            color["name"] = str(nm).strip()[:12] if isinstance(nm, str) and nm.strip() else "定制色"
        else:
            warnings_out.append(f"非法颜色 {hx!r}，回退为碳灰")

    rationale = raw.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        rationale = "模型未提供设计说明"
        warnings_out.append("缺少 rationale")
    rationale = rationale.strip()[:140]

    try:
        conf = float(raw.get("confidence", 0.5))
        if conf != conf:
            raise ValueError
    except (TypeError, ValueError):
        conf = 0.5
        warnings_out.append("非法 confidence，回退为 0.5")
    confidence = max(0.0, min(1.0, conf))

    return {
        "car_type": car_type,
        "style_tags": tags,
        "params": params,
        "color": color,
        "rationale": rationale,
        "confidence": round(confidence, 2),
        "warnings": warnings_out,
    }


# ── LLM 调用（封装以便测试 monkeypatch） ────────────────
async def invoke_llm(prompt: str) -> Dict[str, Any]:
    """调用 SiliconFlow 让模型输出 JSON；返回解析后的 dict。

    无 Key → 503；上游故障 → 502；坏 JSON → 502。
    """
    api_key = os.getenv("EVOAI_SILICONFLOW_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="未配置 EVOAI_SILICONFLOW_KEY，设计意图引擎不可用",
        )

    payload = {
        "model": _LLM_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}",
               "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=_LLM_TIMEOUT) as client:
            resp = await client.post(_SILICONFLOW_URL, json=payload, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"意图引擎超时（{_LLM_TIMEOUT:.0f}s）")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"意图引擎网络故障：{type(exc).__name__}")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"上游返回 {resp.status_code}：{resp.text[:200]}",
        )

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"上游响应无法解析为 JSON：{type(exc).__name__}")


# ── 端点 ────────────────────────────────────────────────
_EXAMPLES = [
    "我要一台运动感强、风阻低的深色轿跑，适合城市通勤",
    "设计一台稳重大气的黑色豪华轿车，用于商务接待",
    "想要一台通过性好、空间大的 SUV，适合全家周末郊游，白色",
    "给年轻人的紧凑型两厢车，线条圆润、颜色鲜亮",
    "一台充满肌肉感的美式跑车，低趴、宽体、红色",
]


@router.get("/examples")
def examples():
    """示例需求（供前端一键填充）"""
    return {"examples": _EXAMPLES}


@router.post("/parse")
@limit(settings.RATE_LIMIT_AI)
async def parse_intent(req: ParseRequest, request: Request):
    """自然语言 → 结构化整车设计方案（经 SiliconFlow 理解 + 服务端校验钳制）"""
    raw = await invoke_llm(req.prompt)
    result = sanitize_intent(raw, req.prompt)
    result["source"] = f"siliconflow:{_LLM_MODEL}"
    return result
