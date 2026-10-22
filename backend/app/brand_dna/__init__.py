"""
品牌造型 DNA 语言模块（Brand DNA Module）
=========================================

定位
----
独立于 SISA 核心算法层的品牌造型 DNA 定制化模块。
吸收 SISA 2D 形状识别与标注的方法论，但通过 JSON 数据契约实现隔离，
不 import 任何 SISA 代码，不包含墨玉等机密品牌数据。

核心能力
--------
1. ``schema``      — 品牌 DNA JSON Schema（结构定义，不含机密数据）
2. ``features_2d`` — 2D 形状无量纲特征提取（12 维，吸收 SISA 方法论独立实现）
3. ``on_brand``    — 品牌合规判定引擎（PASS/FAIL/NO_DATA/N/A 四级）
4. ``loader``      — DNA 加载器与数据契约（支持 JSON 导入，机密数据留 SISA）

隔离边界
--------
- 本模块仅依赖标准库 + numpy，不依赖 SISA 任何模块
- 与 SISA 的交互通过 JSON 文件契约（见 ``contracts/exchange_protocol.md``）
- 墨玉等机密品牌 DNA 数据不进入本模块代码库，由用户在运行时按需导入
"""
from __future__ import annotations

from .schema import BrandDNASchema, validate_dna
from .features_2d import SurfaceFeatures, extract_features, FEATURE_DIM, FEATURE_NAMES
from .on_brand import Clause, OnBrandResult, evaluate_on_brand
from .loader import load_dna, list_available_dnas, import_dna_file

__all__ = [
    "BrandDNASchema",
    "validate_dna",
    "SurfaceFeatures",
    "extract_features",
    "FEATURE_DIM",
    "FEATURE_NAMES",
    "Clause",
    "OnBrandResult",
    "evaluate_on_brand",
    "load_dna",
    "list_available_dnas",
    "import_dna_file",
]

__version__ = "1.0.0"
