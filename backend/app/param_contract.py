"""参数契约（单一事实来源）：别名映射 + 取值范围校验

`POST /api/v1/car/generate` 接收**扁平** `params_override`（前端字段名），
`POST /api/v1/import-export/import` 接收**分组** `params`（后端参数名），
两个入口过去各自实现参数名解析与范围校验，导致：

  * generate 入口不校验范围，越界值被静默注入几何；
  * import 入口的范围校验与 generate 的别名映射无关，两端口径不一致。

本模块把「别名解析」与「min/max 越界判定」收敛成唯一实现：

  * 越界一律**拒绝**（返回错误字符串，由路由层转 422），不夹紧、不静默通过；
  * 错误消息固定包含 字段名 + 实际值 + 允许区间；
  * 未知字段名沿用既有语义**忽略**（不是越界，不应破坏旧调用方）。

本模块只读配置，不做写回；`load_parameter_groups()` 返回的字典不得修改。
"""
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import os
import json

# ============== 分组中文名 ↔ 英文稳定键 双向映射 ==============
# 前端所有显示与 i18n key 统一使用英文稳定键；后端保留中文原有 key
# （automotive_parameters.json 不变）。
GROUP_ZH_TO_EN = {
    "整车尺寸": "overall_dimensions",
    "车身部件": "body_components",
    "造型角度": "styling_angles",
    "A级曲面参数": "class_a_params",
    "比例参数": "proportions",
    "飞行参数": "flight_parameters",
}
GROUP_EN_TO_ZH = {v: k for k, v in GROUP_ZH_TO_EN.items()}

# ============== 前端字段名 → 后端配置参数名 ==============
# 映射原则（以**几何语义**为准，而非字面相同）：
#   wheel_base / front_overhang / rear_overhang 为纯命名差异，直接映射；
#   roof_height **两者同名但语义完全不同**（前端=车顶纵向跨度，
#   后端 roof_height=车顶板厚度 30~100），若按原名注入会把 850 当成
#   板厚、量级错 10 倍以上，故映射到语义对应的 roof_length；
#   rear_slant_angle 后端已有独立同名参数（5~60），保持独立，不得再映射到
#   c_pillar_angle（两者区间不同：c_pillar_angle 为 20~45）。
PARAM_ALIASES = {
    "wheel_base": "wheelbase",
    "front_overhang": "overhang_front",
    "rear_overhang": "overhang_rear",
    "roof_height": "roof_length",
}

#: 车顶语义隔离（契约硬约束）：车顶跨度与车顶板厚是**两个独立字段**。
#: 前端 roof_height（跨度语义）只能落到 ROOF_SPAN，绝不能落到 ROOF_THICKNESS。
ROOF_SPAN = "roof_length"
ROOF_THICKNESS = "roof_height"

#: 这些前端字段名**必须强制走别名**，即使后端存在同名参数。
#: 用于处理「同名不同义」的陷阱（当前为 roof_height）。
FORCE_ALIAS = frozenset({"roof_height"})

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "config", "automotive_parameters.json"
)


@lru_cache(maxsize=1)
def load_parameter_groups() -> Dict[str, Dict[str, Any]]:
    """读取默认参数分组（只读缓存，调用方不得修改返回值）"""
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["automotive_parameters"]


def normalize_group(params: Dict[str, Any], group: str) -> str:
    """把分组名规范化为 automotive_parameters.json 中的中文 key。

    支持三种输入：中文原名 / 英文稳定键 / JSON 默认 key。
    若找不到，原样返回（调用方仍会校验并报错）。
    """
    if group in params:
        return group
    zh = GROUP_EN_TO_ZH.get(group)
    if zh and zh in params:
        return zh
    return group


def group_key(group_zh: str) -> str:
    """返回分组英文稳定键；找不到时回退为原值（兜底避免崩溃）"""
    return GROUP_ZH_TO_EN.get(group_zh, group_zh)


def flat_index(groups: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """建立 {后端参数名: 所属中文分组} 索引，供扁平格式覆盖使用"""
    idx: Dict[str, str] = {}
    for gname, items in groups.items():
        for key in items:
            idx.setdefault(key, gname)
    return idx


def resolve_flat_name(key: str, idx: Dict[str, str]) -> Optional[str]:
    """扁平字段名 → 后端规范参数名；未知字段返回 None（沿用既有语义忽略）"""
    if key in FORCE_ALIAS:
        name = PARAM_ALIASES.get(key)
    else:
        name = key if key in idx else PARAM_ALIASES.get(key)
    if name is None or name not in idx:
        return None
    return name


def resolve_flat_overrides(
    overrides: Optional[Dict[str, Any]],
    groups: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """把扁平参数覆盖解析为分组格式（别名映射 + 未知字段忽略）"""
    if not overrides:
        return {}
    groups = groups if groups is not None else load_parameter_groups()
    idx = flat_index(groups)
    out: Dict[str, Dict[str, Any]] = {}
    for key, value in overrides.items():
        name = resolve_flat_name(key, idx)
        if name is None:
            continue
        out.setdefault(idx[name], {})[name] = value
    return out


def resolve_grouped_key(
    params: Dict[str, Dict[str, Any]], group: str, key: str
) -> Tuple[Optional[Tuple[str, str]], Optional[str]]:
    """分组键解析：返回 ((中文分组, 规范键), None)；失败返回 (None, 错误消息)

    分组内优先使用原名（显式分组即显式语义，例如「车身部件.roof_height」
    就是板厚）；仅当原名不存在时才尝试别名（如「整车尺寸.wheel_base」）。

    车顶隔离：`roof_length` 与 `roof_height` 各自原名优先命中自己的区间
    （[1200,2000] / [30,100]），不会被对方吞掉；前端经共享映射表统一提交
    `roof_length`，因此不会把车顶跨度误判成板厚。
    """
    g = normalize_group(params, group)
    if g not in params:
        return None, f"Parameter group '{group}' does not exist"
    if key in params[g]:
        return (g, key), None
    alias = PARAM_ALIASES.get(key)
    if alias and alias in params[g]:
        return (g, alias), None
    return None, f"Parameter '{key}' does not exist in group '{group}'"


def bounds(meta: Any) -> Tuple[Any, Any]:
    """取参数的允许区间；缺省沿用历史默认 [0, 9999]（与旧实现一致）"""
    if not isinstance(meta, dict):
        return 0, 9999
    lo = meta.get("min_value", 0)
    hi = meta.get("max_value", 9999)
    return lo, hi


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{value:g}"
    return repr(value)


def format_range(lo: Any, hi: Any) -> str:
    """区间展示：左闭右闭；未设边界时用 -inf / +inf 表示"""
    left = "-inf" if lo is None else _format_value(lo)
    right = "+inf" if hi is None else _format_value(hi)
    return f"[{left}, {right}]"


def _out_of_range(value: Any, lo: Any, hi: Any) -> bool:
    try:
        below = lo is not None and value < lo
        above = hi is not None and value > hi
    except TypeError:
        # 非数值（如上传的完整配置里 value 是字符串）：无法比较即视为越界
        return True
    return bool(below or above)


def _range_error(
    submitted: str, canonical: Optional[str], value: Any, lo: Any, hi: Any
) -> str:
    label = submitted
    if canonical and canonical != submitted:
        label = f"{submitted} ({canonical})"
    return (f"Value {_format_value(value)} for '{label}' "
            f"is out of range {format_range(lo, hi)}")


def validate_group_value(
    params: Dict[str, Dict[str, Any]], group: str, key: str, value: Any
) -> Optional[str]:
    """校验分组参数值；合法返回 None，否则返回可直接展示的错误字符串

    支持中文/英文分组名，以及分组内别名（原名优先）。
    """
    ref, err = resolve_grouped_key(params, group, key)
    if err:
        return err
    g, ckey = ref
    meta = params[g][ckey]
    if not isinstance(meta, dict) or "value" not in meta:
        return f"Parameter '{group}.{key}' has invalid structure"
    lo, hi = bounds(meta)
    if _out_of_range(value, lo, hi):
        canonical = None if ckey == key else f"{group_key(g)}.{ckey}"
        return _range_error(f"{group}.{key}", canonical, value, lo, hi)
    return None


def check_and_apply_group_value(
    params: Dict[str, Dict[str, Any]], group: str, key: str, value: Any
) -> Tuple[Optional[Tuple[str, str]], Optional[str]]:
    """校验并写入 `value`（不越界才写）；返回 ((中文分组, 规范键), 错误)"""
    err = validate_group_value(params, group, key, value)
    if err:
        return None, err
    ref, _ = resolve_grouped_key(params, group, key)
    g, ckey = ref
    params[g][ckey]["value"] = value
    return ref, None


def validate_flat_overrides(
    overrides: Optional[Dict[str, Any]],
    groups: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[str]:
    """校验扁平参数覆盖；返回错误列表（空列表表示全部合法）

    未知字段名**不报错**（沿用生成器既有语义：安全忽略），
    只对能解析到后端参数的越界值报错。
    """
    if not overrides:
        return []
    groups = groups if groups is not None else load_parameter_groups()
    idx = flat_index(groups)
    errors: List[str] = []
    for key, value in overrides.items():
        name = resolve_flat_name(key, idx)
        if name is None:
            continue
        g = idx[name]
        meta = groups[g][name]
        lo, hi = bounds(meta)
        if _out_of_range(value, lo, hi):
            canonical = f"{group_key(g)}.{name}"
            errors.append(_range_error(key, canonical, value, lo, hi))
    return errors


def parameter_schema() -> Dict[str, Any]:
    """只读参数契约：分组、默认值、区间、别名与车顶语义隔离说明。

    供前端选车型时拉取区间约束输入，避免默认载荷越界；不得用于写回配置。
    """
    groups = load_parameter_groups()
    out_groups: Dict[str, Any] = {}
    flat: Dict[str, Any] = {}
    for zh, items in groups.items():
        en = group_key(zh)
        params: Dict[str, Any] = {}
        for key, meta in items.items():
            if not isinstance(meta, dict):
                continue
            lo, hi = bounds(meta)
            row = {
                "name": meta.get("name"),
                "value": meta.get("value"),
                "unit": meta.get("unit"),
                "type": meta.get("type"),
                "category": meta.get("category"),
                "min": lo,
                "max": hi,
                "group": en,
                "group_zh": zh,
            }
            params[key] = row
            flat.setdefault(key, row)
        out_groups[en] = {"zh": zh, "params": params}
    return {
        "source": "backend/config/automotive_parameters.json",
        "groups": out_groups,
        "flat": flat,
        "aliases": dict(PARAM_ALIASES),
        "semantics": {
            ROOF_SPAN: {
                "meaning": "车顶跨度（mm）",
                "range": list(bounds(groups["车身部件"][ROOF_SPAN])),
                "never_alias_to": ROOF_THICKNESS,
            },
            ROOF_THICKNESS: {
                "meaning": "车顶板厚（mm）",
                "range": list(bounds(groups["车身部件"][ROOF_THICKNESS])),
            },
            "rear_slant_angle": {
                "meaning": "尾部溜背角（°）",
                "independent": True,
                "never_alias_to": "c_pillar_angle",
            },
        },
    }
