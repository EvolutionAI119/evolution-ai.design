# -*- coding: utf-8 -*-
"""AI 设计意图引擎测试

覆盖两层：
  1. sanitize_intent 纯函数：白名单/钳制/降级全部行为
  2. /parse 与 /examples 端点：LLM 调用 monkeypatch，不依赖真实上游
真实 SiliconFlow 调用仅在环境变量 RUN_REAL_LLM=1 时执行。
"""
import math
import os

import pytest

from app.routes import design_intent as di


# ── 合法 LLM 输出样本 ───────────────────────────────────
GOOD_RAW = {
    "car_type": "coupe",
    "style_tags": ["运动", "低风阻"],
    "params": {
        "overall_length": 4800, "overall_width": 1890, "overall_height": 1380,
        "wheel_base": 2780, "track_width": 1620, "ground_clearance": 120,
        "hood_length": 1350, "roof_height": 420, "wheel_diameter": 700,
        "windshield_angle": 40, "rear_window_angle": 35, "rear_slant_angle": 40,
        "front_overhang": 1020, "rear_overhang": 1000,
    },
    "color": {"hex": "#0A0A0F", "name": "曜石黑"},
    "rationale": "降低车高、增大风挡倾角以降低风阻，长发动机盖强化运动姿态。",
    "confidence": 0.86,
}


# ── 1. 纯函数：正常路径 ─────────────────────────────────
def test_sanitize_good_output():
    out = di.sanitize_intent(GOOD_RAW)
    assert out["car_type"] == "coupe"
    assert out["style_tags"] == ["运动", "低风阻"]
    assert set(out["params"]) == set(di.PARAM_BOUNDS)
    assert out["color"] == {"hex": "#0a0a0f", "name": "曜石黑"}  # hex 小写化
    assert out["confidence"] == 0.86
    assert out["warnings"] == []


def test_all_params_within_bounds():
    out = di.sanitize_intent(GOOD_RAW)
    for name, (lo, hi) in di.PARAM_BOUNDS.items():
        assert lo <= out["params"][name] <= hi, name


# ── 2. 降级行为 ────────────────────────────────────────
def test_bad_car_type_falls_back():
    out = di.sanitize_intent({**GOOD_RAW, "car_type": "flying-car"})
    assert out["car_type"] == "sedan"
    assert any("车型" in w for w in out["warnings"])


def test_prompt_hint_overrides_model_car_type():
    # 模型给 sedan，但 prompt 明确"轿跑" → 校正为 coupe
    out = di.sanitize_intent({**GOOD_RAW, "car_type": "sedan"},
                             "我要一台深色轿跑")
    assert out["car_type"] == "coupe"
    assert any("轿跑" in w or "校正" in w for w in out["warnings"])


def test_prompt_hint_matching_model_no_warning():
    out = di.sanitize_intent({**GOOD_RAW, "car_type": "coupe"},
                             "一台轿跑")
    assert out["car_type"] == "coupe"
    assert not any("校正" in w for w in out["warnings"])


def test_prompt_sport_hint():
    out = di.sanitize_intent({**GOOD_RAW, "car_type": "coupe"},
                             "红色超跑")
    assert out["car_type"] == "sport"


def test_param_above_bound_is_clamped():
    raw = {**GOOD_RAW, "params": {**GOOD_RAW["params"], "overall_height": 9999}}
    out = di.sanitize_intent(raw)
    assert out["params"]["overall_height"] == di.PARAM_BOUNDS["overall_height"][1]
    assert any("overall_height" in w for w in out["warnings"])


def test_param_below_bound_is_clamped():
    raw = {**GOOD_RAW, "params": {**GOOD_RAW["params"], "wheel_base": 10}}
    out = di.sanitize_intent(raw)
    assert out["params"]["wheel_base"] == di.PARAM_BOUNDS["wheel_base"][0]


def test_non_numeric_param_becomes_midpoint():
    raw = {**GOOD_RAW, "params": {**GOOD_RAW["params"], "wheel_diameter": "huge"}}
    out = di.sanitize_intent(raw)
    lo, hi = di.PARAM_BOUNDS["wheel_diameter"]
    assert out["params"]["wheel_diameter"] == round((lo + hi) / 2)


def test_nan_param_becomes_midpoint():
    raw = {**GOOD_RAW, "params": {**GOOD_RAW["params"], "track_width": math.nan}}
    out = di.sanitize_intent(raw)
    lo, hi = di.PARAM_BOUNDS["track_width"]
    assert out["params"]["track_width"] == round((lo + hi) / 2)


def test_params_not_object_all_midpoints():
    raw = {**GOOD_RAW, "params": "ignore"}
    out = di.sanitize_intent(raw)
    assert len(out["warnings"]) >= 1
    for name, (lo, hi) in di.PARAM_BOUNDS.items():
        assert out["params"][name] in (round((lo + hi) / 2),
                                       round((lo + hi) / 2, 1))


def test_missing_params_all_midpoints():
    out = di.sanitize_intent({"car_type": "sedan"})
    assert len(out["params"]) == len(di.PARAM_BOUNDS)


def test_bad_color_falls_back():
    out = di.sanitize_intent({**GOOD_RAW, "color": {"hex": "red"}})
    assert out["color"] == {"hex": "#374151", "name": "碳灰"}
    assert any("颜色" in w for w in out["warnings"])


def test_valid_color_without_name_gets_default_name():
    out = di.sanitize_intent({**GOOD_RAW, "color": {"hex": "#ffffff"}})
    assert out["color"]["hex"] == "#ffffff"
    assert out["color"]["name"] == "定制色"


def test_bad_tags_replaced():
    out = di.sanitize_intent({**GOOD_RAW, "style_tags": ["赛博朋克", 123]})
    assert out["style_tags"] == ["稳重"]


def test_tags_dedup_and_cap_5():
    out = di.sanitize_intent(
        {**GOOD_RAW, "style_tags": ["运动", "运动", "豪华", "优雅", "硬朗", "圆润"]})
    assert len(out["style_tags"]) == 5
    assert out["style_tags"][0] == "运动"


def test_bad_confidence_falls_back():
    out = di.sanitize_intent({**GOOD_RAW, "confidence": "sure"})
    assert out["confidence"] == 0.5


def test_confidence_clamped():
    assert di.sanitize_intent({**GOOD_RAW, "confidence": 5})["confidence"] == 1.0
    assert di.sanitize_intent({**GOOD_RAW, "confidence": -1})["confidence"] == 0.0


def test_missing_rationale_flagged():
    out = di.sanitize_intent({**GOOD_RAW, "rationale": "  "})
    assert out["rationale"] == "模型未提供设计说明"


def test_length_inconsistency_warns():
    raw = {**GOOD_RAW,
           "params": {**GOOD_RAW["params"], "overall_length": 6200}}
    out = di.sanitize_intent(raw)
    assert any("车长" in w for w in out["warnings"])


# ── 3. 端点 ────────────────────────────────────────────
def test_invoke_llm_no_key(monkeypatch):
    import asyncio
    monkeypatch.delenv("EVOAI_SILICONFLOW_KEY", raising=False)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        asyncio.run(di.invoke_llm("test"))
    assert ei.value.status_code == 503


def test_parse_endpoint_with_mocked_llm(client, monkeypatch):
    async def fake_invoke(prompt):
        return GOOD_RAW
    monkeypatch.setattr(di, "invoke_llm", fake_invoke)
    resp = client.post("/api/v1/design-intent/parse",
                       json={"prompt": "一台运动轿跑"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["car_type"] == "coupe"
    assert data["source"] == f"siliconflow:{di._LLM_MODEL}"
    assert "params" in data and len(data["params"]) == 14


def test_parse_endpoint_rejects_short_prompt(client):
    # 短 prompt 被 Pydantic 422 拦截，不会到达 LLM
    resp = client.post("/api/v1/design-intent/parse", json={"prompt": "x"})
    assert resp.status_code == 422


def test_examples_endpoint(client):
    resp = client.get("/api/v1/design-intent/examples")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["examples"]) >= 3
    assert all(isinstance(e, str) for e in data["examples"])


# ── 4. 真实 LLM（默认跳过） ─────────────────────────────
@pytest.mark.skipif(os.getenv("RUN_REAL_LLM") != "1",
                    reason="需真实 SiliconFlow 调用；设 RUN_REAL_LLM=1 启用")
def test_real_llm_roundtrip(client):
    resp = client.post("/api/v1/design-intent/parse",
                       json={"prompt": "一台低趴运动红色跑车"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["car_type"] in di.CAR_TYPES
    assert len(data["params"]) == 14
