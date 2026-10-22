"""
品牌合规判定引擎（On-Brand Evaluation）
======================================

吸收 SISA ``on_brand.py`` 的方法论，独立实现品牌 DNA 约束判定。

判定分级（不掩盖不可测项）
--------------------------
    PASS      实测满足
    FAIL      实测违反
    NO_DATA   当前无法测量 —— 如实标注，绝不推定通过
    N/A       该约束不适用于当前产物类型

约束规则类型
------------
    zero    : value = 0（如无格栅、无车标）
    range   : min ≤ value ≤ max
    enum    : value in allowed_values
    sealed  : value == "sealed"（前脸封闭）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .schema import CLAUSE_STATUSES


@dataclass
class Clause:
    """一条 DNA 约束的判定结果

    与 SISA ``Clause`` 数据契约兼容。
    """
    key: str
    rule: str
    status: str = "NO_DATA"
    trait: str = ""
    principle: str = ""
    measured: Any = None
    note: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "rule": self.rule,
            "status": self.status,
            "trait": self.trait,
            "principle": self.principle,
            "measured": self.measured,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Clause":
        return cls(
            key=d["key"],
            rule=d.get("rule", ""),
            status=d.get("status", "NO_DATA"),
            trait=d.get("trait", ""),
            principle=d.get("principle", ""),
            measured=d.get("measured"),
            note=d.get("note", ""),
        )


@dataclass
class OnBrandResult:
    """品牌合规判定汇总结果"""
    brand_key: str
    clauses: List[Clause] = field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    no_data_count: int = 0
    na_count: int = 0
    score: float = 0.0  # 0~100，仅统计可判定项

    def as_dict(self) -> Dict[str, Any]:
        return {
            "brand_key": self.brand_key,
            "clauses": [c.as_dict() for c in self.clauses],
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "no_data_count": self.no_data_count,
            "na_count": self.na_count,
            "score": round(self.score, 2),
        }


def _parse_rule(rule: str) -> Tuple[str, Dict[str, Any]]:
    """解析规则字符串

    支持格式：
        "=0.0"           → (zero, {})
        "≤0.3mm"         → (range, {"max": 0.3})
        "≥0.85"          → (range, {"min": 0.85})
        "=sealed"        → (sealed, {})
        "≥160°"          → (range, {"min": 160.0})
        "≤2辐"           → (range, {"max": 2})
    """
    rule = rule.strip()
    if rule.startswith("="):
        val = rule[1:].strip()
        if val.lower() == "sealed":
            return "sealed", {}
        try:
            v = float(val)
            if v == 0.0:
                return "zero", {}
            return "enum", {"values": [v]}
        except ValueError:
            return "enum", {"values": [val]}

    if rule.startswith("≤") or rule.startswith("<="):
        num = _extract_number(rule[1:])
        return "range", {"max": num} if num is not None else ("range", {})

    if rule.startswith("≥") or rule.startswith(">="):
        num = _extract_number(rule[1:])
        return "range", {"min": num} if num is not None else ("range", {})

    return "unknown", {}


def _extract_number(s: str) -> Optional[float]:
    """从字符串提取第一个数字"""
    import re
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else None


def _evaluate_clause(
    key: str,
    clause_spec: Dict[str, Any],
    measured: Dict[str, Any],
) -> Clause:
    """评估单条约束"""
    rule = clause_spec.get("rule", "")
    trait = clause_spec.get("trait", "")
    principle = clause_spec.get("principle", "")

    measured_val = measured.get(key)
    if measured_val is None:
        return Clause(
            key=key, rule=rule, status="NO_DATA",
            trait=trait, principle=principle,
            measured=None, note="当前无法测量",
        )

    rule_type, params = _parse_rule(rule)

    if rule_type == "zero":
        ok = float(measured_val) == 0.0
        status = "PASS" if ok else "FAIL"
    elif rule_type == "sealed":
        ok = str(measured_val).lower() == "sealed"
        status = "PASS" if ok else "FAIL"
    elif rule_type == "range":
        val = float(measured_val)
        mn = params.get("min")
        mx = params.get("max")
        ok = True
        if mn is not None:
            ok = ok and val >= mn
        if mx is not None:
            ok = ok and val <= mx
        status = "PASS" if ok else "FAIL"
    elif rule_type == "enum":
        ok = measured_val in params.get("values", [])
        status = "PASS" if ok else "FAIL"
    else:
        status = "NO_DATA"

    return Clause(
        key=key, rule=rule, status=status,
        trait=trait, principle=principle,
        measured=measured_val,
    )


def evaluate_on_brand(
    dna: Dict[str, Any],
    measured: Dict[str, Any],
) -> OnBrandResult:
    """对一个产物执行品牌合规判定

    参数
    ----
    dna: 品牌 DNA 字典（需含 on_brand_constraints）
    measured: 实测参数字典 {key: value}

    返回
    ----
    OnBrandResult
    """
    brand_key = dna.get("brand", {}).get("key", "unknown")
    constraints = dna.get("on_brand_constraints", {})

    clauses: List[Clause] = []
    for key, spec in constraints.items():
        if not isinstance(spec, dict):
            continue
        clauses.append(_evaluate_clause(key, spec, measured))

    pass_count = sum(1 for c in clauses if c.status == "PASS")
    fail_count = sum(1 for c in clauses if c.status == "FAIL")
    no_data_count = sum(1 for c in clauses if c.status == "NO_DATA")
    na_count = sum(1 for c in clauses if c.status == "N/A")

    decidable = pass_count + fail_count
    score = (pass_count / decidable * 100.0) if decidable > 0 else 0.0

    return OnBrandResult(
        brand_key=brand_key,
        clauses=clauses,
        pass_count=pass_count,
        fail_count=fail_count,
        no_data_count=no_data_count,
        na_count=na_count,
        score=score,
    )


__all__ = ["Clause", "OnBrandResult", "evaluate_on_brand"]
