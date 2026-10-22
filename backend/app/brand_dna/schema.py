"""
品牌造型 DNA JSON Schema（结构定义）
====================================

抽象自 SISA ``moyu_brand_dna.json`` 的数据结构，但**不含任何机密品牌数据**。
本模块只定义结构契约，实际品牌 DNA 由用户在运行时通过 ``loader`` 导入。

Schema 版本
-----------
- ``schema_version``: "1.0"  — 与 SISA DNA 数据结构兼容
- 支持通过 ``exchange_protocol`` 从 SISA 导入脱敏成果包

结构概览
--------
- ``_CONFIDENTIAL``: 密级声明（平台侧默认为 public，不存机密数据）
- ``brand``: 品牌基本信息（key/name/zh_name/positioning）
- ``philosophy``: 设计哲学框架与原则
- ``jade_traits``: 材质特质映射（可泛化为 brand_traits）
- ``forbidden`` / ``allowed``: 造型约束清单
- ``on_brand_constraints``: 可量化的合规判定约束
- ``cmf``: 色彩材质工艺
- ``models``: 车型参数矩阵（尺寸/曲面/细节/内饰）
- ``engine_spec``: 引擎运行时规格（zero_rules/range_rules/series_spec）
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

#: 当前 Schema 版本
SCHEMA_VERSION = "1.0"

#: 合规判定状态枚举
CLAUSE_STATUSES = ("PASS", "FAIL", "NO_DATA", "N/A")

#: 约束规则类型
RULE_TYPES = ("zero", "range", "enum", "sealed")


class BrandDNASchema:
    """品牌 DNA 结构定义与校验器

    用法::

        schema = BrandDNASchema()
        ok, errors = schema.validate(dna_dict)
    """

    #: 必填顶层字段
    REQUIRED_TOP_FIELDS = ("brand", "on_brand_constraints")

    #: brand 必填字段
    REQUIRED_BRAND_FIELDS = ("key", "name", "zh_name")

    #: on_brand_constraints 每条约束必填字段
    REQUIRED_CLAUSE_FIELDS = ("rule",)

    def validate(self, dna: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """校验 DNA 数据结构

        返回 (is_valid, errors)
        """
        errors: List[str] = []

        if not isinstance(dna, dict):
            return False, ["DNA 必须是 dict 对象"]

        # 顶层必填
        for f in self.REQUIRED_TOP_FIELDS:
            if f not in dna:
                errors.append(f"缺少顶层必填字段: {f}")

        # brand 校验
        brand = dna.get("brand")
        if isinstance(brand, dict):
            for f in self.REQUIRED_BRAND_FIELDS:
                if f not in brand:
                    errors.append(f"brand 缺少必填字段: {f}")
        elif brand is not None:
            errors.append("brand 必须是 dict")

        # on_brand_constraints 校验
        constraints = dna.get("on_brand_constraints")
        if isinstance(constraints, dict):
            for key, clause in constraints.items():
                if not isinstance(clause, dict):
                    errors.append(f"约束 {key} 必须是 dict")
                    continue
                for f in self.REQUIRED_CLAUSE_FIELDS:
                    if f not in clause:
                        errors.append(f"约束 {key} 缺少必填字段: {f}")
        elif constraints is not None:
            errors.append("on_brand_constraints 必须是 dict")

        # engine_spec 校验（可选）
        engine = dna.get("engine_spec")
        if engine is not None and not isinstance(engine, dict):
            errors.append("engine_spec 必须是 dict")

        # models 校验（可选）
        models = dna.get("models")
        if models is not None and not isinstance(models, list):
            errors.append("models 必须是 list")

        # schema_version 兼容
        sv = dna.get("schema_version")
        if sv is not None and sv != SCHEMA_VERSION:
            errors.append(
                f"schema_version 不兼容: 期望 {SCHEMA_VERSION}, 实际 {sv}"
            )

        return (len(errors) == 0), errors

    def to_template(self) -> Dict[str, Any]:
        """生成空 DNA 模板（供新品牌创建）"""
        return {
            "schema_version": SCHEMA_VERSION,
            "_CONFIDENTIAL": {
                "level": "public",
                "policy": "可公开",
                "storage": "backend/app/brand_dna/dnas/ 或运行时导入",
            },
            "brand": {
                "key": "",
                "name": "",
                "zh_name": "",
                "status": "public",
                "positioning": "",
                "one_line": "",
            },
            "philosophy": {
                "framework": "",
                "principles": [],
            },
            "jade_traits": [],
            "forbidden": [],
            "allowed": [],
            "on_brand_constraints": {},
            "cmf": {
                "palette": [],
                "interior": {},
            },
            "models": [],
            "engine_spec": {
                "zero_rules": [],
                "range_rules": [],
                "series_spec": {},
            },
        }


def validate_dna(dna: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """便捷函数：校验 DNA 结构"""
    return BrandDNASchema().validate(dna)


def load_schema_template() -> Dict[str, Any]:
    """返回空 DNA 模板"""
    return BrandDNASchema().to_template()


__all__ = [
    "BrandDNASchema",
    "validate_dna",
    "load_schema_template",
    "SCHEMA_VERSION",
    "CLAUSE_STATUSES",
    "RULE_TYPES",
]
