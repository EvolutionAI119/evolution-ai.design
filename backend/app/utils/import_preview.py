"""
整车导入后的"图片预览契约"工具集（独立、无路由、纯逻辑，方便任何模块复用）。

复用目标：
  - 路由层（import_export.py 的 /import /import/file /sessions）
  - 未来 websocket 推送"会话列表变更"时补齐图片字段
  - 导出服务在打包预览报告时，自动决定封面图 brand/model

用法::

    from app.utils.import_preview import brand_model_inferrer, build_preview_contract

    brand_key, model_key = brand_model_inferrer.infer("taycan_turbo_s.CATPart")

    contract = build_preview_contract(
        session_id=sid,
        name="My Model",
        original_filename="taycan_turbo_s.CATPart",
    )
    # => { "inferred_brand_key": "porsche",
    #      "inferred_model_key": "taycan",
    #      "preview_url": "/api/v1/import-export/<sid>/preview" }
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ============================================================
# 品牌/车型目录（纯数据，任何模块可引用）
# ============================================================
BRAND_MODEL_CATALOG: List[Dict[str, Any]] = [
    # 注意：brand_aliases 里只放"品牌别名"，不要放具体车型名
    # （避免品牌先命中后，车型被"turbo/gt"这类通用词误匹配）。
    {"brand_key": "rolls-royce", "brand_aliases": [
        "rollsroyce", "rolls royce", "rolls-royce", "rr", "劳斯莱斯",
    ], "models": [
        {"model_key": "phantom",  "aliases": ["phantom", "幻影"]},
        {"model_key": "ghost",    "aliases": ["ghost", "古斯特", "ghostseries"]},
        {"model_key": "cullinan", "aliases": ["cullinan", "库里南", "cullinansuv"]},
        {"model_key": "wraith",   "aliases": ["wraith", "魅影"]},
    ]},
    {"brand_key": "bentley", "brand_aliases": [
        "bentley", "本特利", "宾利",
    ], "models": [
        {"model_key": "continental-gt",
            "aliases": ["continentalgt", "continental gt", "continental-gt", "contigt"]},
        {"model_key": "continental-gtc",
            "aliases": ["continentalgtc", "continental gtc", "continental-gtc", "contigtc"]},
        {"model_key": "flying-spur",
            "aliases": ["flyingspur", "flying spur", "flying-spur", "飞驰"]},
        {"model_key": "bentayga",
            "aliases": ["bentayga", "添越", "bentaygasuv"]},
    ]},
    {"brand_key": "bugatti", "brand_aliases": ["bugatti", "布加迪"],
     "models": [
        {"model_key": "chiron", "aliases": ["chiron", "凯龙", "赤龙"]},
        {"model_key": "veyron", "aliases": ["veyron", "威龙"]},
        {"model_key": "divo",   "aliases": ["divo"]},
    ]},
    {"brand_key": "porsche", "brand_aliases": ["porsche", "保时捷"],
     "models": [
        {"model_key": "taycan",   "aliases": [
            "taycanturbos", "taycancrossturismo", "taycancross", "taycanturbo",
            "taycan gts", "taycan"
        ]},
        {"model_key": "911",      "aliases": [
            "911 turbo s", "911turbo", "911gt3", "911 gt3", "911gt2",
            "911carrera", "992", "991", "carrera", "911"
        ]},
        {"model_key": "panamera", "aliases": [
            "panamerasportturismo", "panameraturismo", "panamera", "帕拉梅拉"
        ]},
        {"model_key": "cayenne",  "aliases": [
            "cayennecoupe", "cayennesuv", "cayenne", "卡宴"
        ]},
        {"model_key": "macan",    "aliases": ["macangts", "macansuv", "macan", "迈坎"]},
    ]},
    {"brand_key": "ferrari", "brand_aliases": ["ferrari", "法拉利"],
     "models": [
        {"model_key": "sf90",       "aliases": ["sf90stradale", "sf90xx", "sf90"]},
        {"model_key": "f8-tributo", "aliases": ["f8tributo", "f8 tributo", "f8-tributo", "f8"]},
        {"model_key": "roma",       "aliases": ["roma"]},
    ]},
    {"brand_key": "tesla", "brand_aliases": ["tesla", "特斯拉"],
     "models": [
        {"model_key": "model_3",  "aliases": [
            "model3performance", "model3perf", "model3", "model 3", "model-3"
        ]},
        {"model_key": "model_s",  "aliases": ["modelsplaid", "models", "model s", "model-s"]},
        {"model_key": "model_x",  "aliases": ["modelxplaid", "modelx", "model x", "model-x"]},
        {"model_key": "model_y",  "aliases": [
            "modelyperformance", "modely", "model y", "model-y"
        ]},
        {"model_key": "cybertruck", "aliases": [
            "cyber truck", "cybertruck", "cyber-truck"
        ]},
    ]},
    {"brand_key": "toyota", "brand_aliases": ["toyota", "丰田"],
     "models": [
        {"model_key": "camry",         "aliases": [
            "camryse", "camryxse", "camryxv70", "camry", "凯美瑞"
        ]},
        {"model_key": "corolla",       "aliases": ["corolla", "卡罗拉"]},
        {"model_key": "land_cruiser",  "aliases": [
            "landcruiser", "land cruiser", "land-cruiser", "兰德酷路泽"
        ]},
        {"model_key": "rav4",          "aliases": ["rav4", "荣放"]},
        {"model_key": "sienna",        "aliases": ["sienna", "塞纳"]},
    ]},
    {"brand_key": "audi", "brand_aliases": ["audi", "奥迪"],
     "models": [
        {"model_key": "e-tron", "aliases": [
            "etrongtconcept", "etrongt", "e-tron gt", "e-tron", "etron", "e tron"
        ]},
        {"model_key": "a4",  "aliases": ["a4l", "a4"]},
        {"model_key": "a5",  "aliases": ["a5", "a5sportback"]},
        {"model_key": "a6",  "aliases": ["a6l", "a6", "a6avant"]},
        {"model_key": "a7",  "aliases": ["a7l", "a7", "a7sportback"]},
        {"model_key": "a8",  "aliases": ["a8l", "a8", "a8horch"]},
        {"model_key": "q3",  "aliases": ["q3"]},
        {"model_key": "q5",  "aliases": ["q5l", "q5"]},
        {"model_key": "q7",  "aliases": ["q7"]},
        {"model_key": "q8",  "aliases": ["q8", "rsq8"]},
    ]},
    {"brand_key": "bmw", "brand_aliases": ["bmw", "宝马", "bayerische"],
     "models": [
        {"model_key": "3_series", "aliases": [
            "3series", "3-series", "3er", "3系", "g20", "f30", "3serieslimousine"
        ]},
        {"model_key": "5_series", "aliases": [
            "5series", "5-series", "5er", "5系", "g60", "g30", "f10"
        ]},
        {"model_key": "7_series", "aliases": [
            "7series", "7-series", "7er", "7系", "g70", "g11", "g12"
        ]},
        {"model_key": "x3", "aliases": ["x3", "ix3"]},
        {"model_key": "x5", "aliases": ["x5", "gx5", "x5m"]},
        {"model_key": "x6", "aliases": ["x6", "x6m"]},
        {"model_key": "x7", "aliases": ["x7", "alpinaxb7"]},
    ]},
    {"brand_key": "mercedes",
     "brand_aliases": [
        "mercedes", "mercedesbenz", "mercedes-benz", "benz", "奔驰", "amg", "maybach"
     ],
     "models": [
        {"model_key": "c_class", "aliases": [
            "cclass", "c-class", "c class", "c级", "w206", "w205"
        ]},
        {"model_key": "e_class", "aliases": [
            "eclass", "e-class", "e class", "e级", "w214", "w213"
        ]},
        {"model_key": "s_class", "aliases": [
            "sclass", "s-class", "s class", "s级", "w223", "w222", "maybachsclass"
        ]},
        {"model_key": "amg",     "aliases": ["amggt", "amg gt", "amg-gt", "amg"]},
        {"model_key": "maybach", "aliases": ["maybach", "迈巴赫"]},
    ]},
    {"brand_key": "byd", "brand_aliases": ["byd", "比亚迪"],
     "models": [
        {"model_key": "han",  "aliases": ["hanev", "handmi", "han ev", "han", "汉", "han dmi"]},
        {"model_key": "tang", "aliases": ["tangdmi", "tangev", "tang", "唐"]},
        {"model_key": "song", "aliases": ["songdmi", "songev", "song", "宋"]},
        {"model_key": "qin",  "aliases": ["qindmi", "qinev", "qin", "秦"]},
    ]},
]

# 类别 fallback：没命中具体品牌/车型时，按"车型类别"映射到风格接近的占位真车图
# （即便 brand_key 为 None，前端也会落到运行时 SVG 兜底，保证不空白）
MODEL_FALLBACK_BY_KEYWORD: Sequence[Tuple[Sequence[str], Optional[str], str]] = [
    (["suv", "suvconcept", "suv概念", "越野车"], "porsche", "cayenne"),
    (["sedan", "evsedan", "轿车", "三厢", "saloon"], "rolls-royce", "ghost"),
    (["coupe", "两门", "硬顶"], "rolls-royce", "wraith"),
    (["sport", "sports", "supercar", "hypercar", "跑车", "超跑", "gt"], "bugatti", "chiron"),
    (["mpv", "商务", "van", "minivan"], "toyota", "sienna"),
    (["pickup", "truck", "皮卡"], "tesla", "cybertruck"),
    (["concept", "prototype", "概念"], None, "concept"),
]


# ============================================================
# 规范化（纯函数，可单测）
# ============================================================
def normalize_keyword(text: Optional[str]) -> str:
    """把文件名/名称统一成"去标点去空格小写"字符串，便于做关键字匹配。"""
    if not text:
        return ""
    s = str(text).lower().strip()
    # 去掉所有非字母数字中文
    s = re.sub(r"[\s\-\.\,\_\/\\\|\(\)\[\]\{\}\:\;\"\'\?\!\+\*\#\@\&\%]+", "", s)
    return s


# ============================================================
# 品牌/车型推断器
# ============================================================
@dataclass
class BrandModelInferrer:
    """可复用的"文本→ (brand_key, model_key)"推断器。

    对外暴露两个扩展点（便于后续模块自定义 catalog / fallback 规则而不修改本文件）::

        custom = BrandModelInferrer(
            catalog=[...extra brands...],
            fallback_keywords=[ (["targa"], None, "concept") ],
        )

    """

    catalog: List[Dict[str, Any]] = field(default_factory=lambda: list(BRAND_MODEL_CATALOG))
    fallback_keywords: Sequence[Tuple[Sequence[str], Optional[str], str]] = tuple(
        MODEL_FALLBACK_BY_KEYWORD
    )

    # ------------------------------------------------------------------ 公开 API
    def infer(self, text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        返回 (brand_key, model_key)。

        匹配顺序：
        1) 品牌命中 + 该品牌下某个车型别名命中
        2) 仅车型别名命中 → 反向得到品牌
        3) 类别关键字 fallback（若第 1 步已记住品牌则复用品牌）
        4) 只记住品牌没记住车型 → 返回 (brand, None)
        5) 完全无命中 → (None, None)
        """
        n = normalize_keyword(text)
        if not n:
            return None, None
        found_brand_key: Optional[str] = None
        for brand in self.catalog:
            brand_hit = self._any_alias_in(brand.get("brand_aliases") or (), n)
            if not brand_hit:
                continue
            found_brand_key = brand["brand_key"]
            for m in brand.get("models") or ():
                if self._any_alias_in(m.get("aliases") or (), n):
                    return brand["brand_key"], m["model_key"]
        # 仅车型反向匹配
        for brand in self.catalog:
            for m in brand.get("models") or ():
                aliases = [normalize_keyword(a) for a in (m.get("aliases") or ())]
                aliases = [a for a in aliases if a]
                if any(a == n or (a and a in n) for a in aliases):
                    return brand["brand_key"], m["model_key"]
        # 类别 fallback
        for keywords, bk, mk in self.fallback_keywords:
            if any(normalize_keyword(k) in n for k in keywords):
                return (found_brand_key or bk), mk
        if found_brand_key:
            return found_brand_key, None
        return None, None

    # ------------------------------------------------------------------ 内部工具
    @staticmethod
    def _any_alias_in(aliases: Iterable[str], needle: str) -> bool:
        for a in aliases:
            na = normalize_keyword(a)
            if na and na in needle:
                return True
        return False


# ============================================================
# 预览契约构造器
# ============================================================
def build_preview_contract(
    session_id: str,
    name: Optional[str] = None,
    original_filename: Optional[str] = None,
    inferrer: Optional[BrandModelInferrer] = None,
    preview_url_template: str = "/api/v1/import-export/{session_id}/preview",
) -> Dict[str, Optional[str]]:
    """
    统一的"导入后图片预览契约"构造器（独立，任何地方需要会话图片字段都可调用）。

    Args:
        session_id: 当前会话 ID（用于 preview_url）
        name: 会话显示名（"Model 3 Perf"之类；若没传 original_filename 会 fallback 到它）
        original_filename: 原始 CAD/JSON 文件名（如 taycan_turbo_s.STEP），推断时优先
        inferrer: 可选自定义推断器（不传则使用默认单例）
        preview_url_template: preview_url 模板，包含 `{session_id}` 占位符

    Returns:
        {
            "inferred_brand_key": Optional[str],
            "inferred_model_key": Optional[str],
            "preview_url":          str,         # 永不为空
        }
    """
    if not session_id:
        raise ValueError("build_preview_contract requires session_id")
    inf = inferrer or DEFAULT_INFERRER
    infer_text = original_filename or name
    brand_key, model_key = inf.infer(infer_text)
    return {
        "inferred_brand_key": brand_key,
        "inferred_model_key": model_key,
        "preview_url": preview_url_template.format(session_id=session_id),
    }


# ============================================================
# 默认单例（避免每次都重新构造 catalog；保持与生产一致）
# ============================================================
DEFAULT_INFERRER = BrandModelInferrer()
