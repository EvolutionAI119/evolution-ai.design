"""
品牌 DNA 加载器与数据契约
=========================

隔离原则
--------
- 本模块不内置任何机密品牌 DNA 数据（墨玉等留在 SISA）
- 仅提供加载/导入接口，DNA 数据由用户在运行时提供
- 支持从 SISA 成果包导入（脱敏后）

数据交换协议
------------
SISA → 平台 的成果包为 JSON 文件，结构遵循 ``schema.SCHEMA_VERSION``。
导入前会自动校验密级声明，机密级别（internal_unreleased）的数据
不会被持久化到平台，仅在内存中使用。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .schema import validate_dna, SCHEMA_VERSION

#: 平台侧 DNA 存储目录（可配置）
DNA_STORE_DIR = Path(__file__).resolve().parent / "dnas"

#: 允许的密级
ALLOWED_CONFIDENTIALITY_LEVELS = ("public", "internal", "confidential")

#: 持久化允许的最高密级（高于此级别的仅内存使用）
MAX_PERSIST_LEVEL = "internal"


def _get_store_dir() -> Path:
    """获取 DNA 存储目录（确保存在）"""
    DNA_STORE_DIR.mkdir(parents=True, exist_ok=True)
    return DNA_STORE_DIR


def _check_confidentiality(dna: Dict[str, Any]) -> Tuple[str, bool]:
    """检查密级，返回 (level, can_persist)

    can_persist=False 表示该 DNA 不应持久化到磁盘（机密数据）。
    """
    conf = dna.get("_CONFIDENTIAL", {})
    level = conf.get("level", "public").lower()
    if level not in ALLOWED_CONFIDENTIALITY_LEVELS:
        level = "public"
    # confidential 级别仅内存使用
    can_persist = level != "confidential"
    return level, can_persist


def load_dna(brand_key: str) -> Optional[Dict[str, Any]]:
    """从平台存储加载指定品牌 DNA

    返回 None 如果不存在。
    """
    store = _get_store_dir()
    path = store / f"{brand_key}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    ok, errors = validate_dna(data)
    if not ok:
        raise ValueError(f"DNA 数据校验失败: {errors}")
    return data


def list_available_dnas() -> List[Dict[str, Any]]:
    """列出平台已存储的所有品牌 DNA"""
    store = _get_store_dir()
    result = []
    for path in sorted(store.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            brand = data.get("brand", {})
            result.append({
                "key": brand.get("key", path.stem),
                "name": brand.get("name", ""),
                "zh_name": brand.get("zh_name", ""),
                "level": data.get("_CONFIDENTIAL", {}).get("level", "public"),
                "file": str(path),
            })
        except Exception:
            continue
    return result


def import_dna_file(
    file_path: str,
    *,
    persist: bool = True,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """从 JSON 文件导入品牌 DNA

    参数
    ----
    file_path: DNA JSON 文件路径
    persist: 是否持久化到平台存储（机密数据会强制设为 False）

    返回
    ----
    (success, message, dna_dict_or_none)
    """
    path = Path(file_path)
    if not path.exists():
        return False, f"文件不存在: {file_path}", None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"JSON 解析失败: {e}", None

    # 结构校验
    ok, errors = validate_dna(data)
    if not ok:
        return False, f"DNA 结构校验失败: {errors}", None

    # 密级检查
    level, can_persist = _check_confidentiality(data)
    brand_key = data.get("brand", {}).get("key", "unknown")

    # 强制：机密数据不持久化
    if level == "confidential":
        persist = False

    if persist and can_persist:
        store = _get_store_dir()
        target = store / f"{brand_key}.json"
        target.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        msg = f"DNA '{brand_key}' 已导入并持久化（密级: {level}）"
    else:
        msg = f"DNA '{brand_key}' 已导入（仅内存，密级: {level}，未持久化）"

    return True, msg, data


def export_dna_template(target_path: str) -> bool:
    """导出空 DNA 模板到指定路径"""
    from .schema import load_schema_template
    template = load_schema_template()
    Path(target_path).write_text(
        json.dumps(template, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return True


__all__ = [
    "load_dna",
    "list_available_dnas",
    "import_dna_file",
    "export_dna_template",
    "DNA_STORE_DIR",
]
