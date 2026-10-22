"""
品牌 DNA 模块隔离与兼容性测试
============================

验证目标：
1. brand_dna 模块不 import 任何 SISA 代码（隔离边界）
2. 2D 特征提取与 SISA 方法论兼容（12 维无量纲）
3. 品牌合规判定引擎正确工作
4. 加载器隔离机密数据（confidential 级别不持久化）
5. Schema 校验正确拒绝非法数据
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# 确保能 import brand_dna
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.brand_dna import (
    BrandDNASchema,
    SurfaceFeatures,
    extract_features,
    FEATURE_DIM,
    FEATURE_NAMES,
    Clause,
    evaluate_on_brand,
    load_dna,
    import_dna_file,
    list_available_dnas,
    validate_dna,
)


# ============================================================
# 1. 隔离边界测试
# ============================================================

class TestIsolationBoundary:
    """验证 brand_dna 不依赖 SISA"""

    def test_no_sisa_imports(self):
        """brand_dna 模块不得 import 任何 sisa.* 模块"""
        import backend.app.brand_dna as bd
        import backend.app.brand_dna.features_2d as f2d
        import backend.app.brand_dna.on_brand as ob
        import backend.app.brand_dna.loader as ld
        import backend.app.brand_dna.schema as sc

        import re
        for mod in (bd, f2d, ob, ld, sc):
            src = Path(mod.__file__).read_text(encoding="utf-8")
            # 只检查 import 语句，文档字符串中的说明性文字允许
            imports = re.findall(r'^\s*(?:import|from)\s+(\S+)', src, re.MULTILINE)
            for imp in imports:
                assert not imp.startswith("sisa"), \
                    f"{mod.__name__} import 了 SISA 模块: {imp}"
                assert not imp.startswith("internal"), \
                    f"{mod.__name__} import 了 SISA internal 模块: {imp}"

    def test_dependencies_only_standard_and_numpy(self):
        """仅依赖标准库 + numpy"""
        import backend.app.brand_dna.features_2d as f2d
        src = Path(f2d.__file__).read_text(encoding="utf-8")
        # 只允许 import numpy 和标准库
        for line in src.splitlines():
            line = line.strip()
            if line.startswith("import ") or line.startswith("from "):
                if "numpy" in line:
                    continue
                # 标准库模块白名单
                std_libs = {
                    "math", "json", "os", "re", "typing", "dataclasses",
                    "pathlib", "functools", "__future__",
                }
                parts = line.replace("import ", "").replace("from ", "").split(".")[0]
                first = parts.split()[0].strip()
                assert first in std_libs, f"非标准依赖: {line}"


# ============================================================
# 2. 2D 特征提取测试
# ============================================================

class TestFeatures2D:
    """验证 12 维无量纲特征提取"""

    def test_feature_dim(self):
        assert FEATURE_DIM == 12
        assert len(FEATURE_NAMES) == 12

    def test_extract_from_plane(self):
        """从平面控制点提取特征"""
        # 4x4 平面控制点
        cp = np.zeros((4, 4, 3))
        for i in range(4):
            for j in range(4):
                cp[i, j] = [i, j, 0.0]

        # 使用均匀非重节点测试均匀度
        feat = extract_features(
            cp, degree_u=3, degree_v=3,
            knots_u=[0.0, 0.25, 0.5, 0.75, 1.0],
            knots_v=[0.0, 0.25, 0.5, 0.75, 1.0],
            family="hood", source="test",
        )
        assert feat is not None
        assert len(feat.vec) == 12
        assert feat.family == "hood"
        # 平面度应接近 0（z 全为 0）
        assert feat.vec[7] == 0.0  # planarity
        # 节点均匀度应为 1.0（均匀节点）
        assert abs(feat.vec[9] - 1.0) < 0.01  # knot_uniformity_u
        assert abs(feat.vec[10] - 1.0) < 0.01  # knot_uniformity_v

    def test_extract_returns_none_on_bad_input(self):
        """非法输入返回 None"""
        assert extract_features(np.zeros((2, 3))) is None  # 维度不对
        assert extract_features(np.zeros((1, 1, 3))) is None  # 太小

    def test_feature_dict_roundtrip(self):
        """SurfaceFeatures 序列化/反序列化兼容 SISA 格式"""
        feat = SurfaceFeatures(family="roof", source="sisa", vec=[0.1] * 12)
        d = feat.as_dict()
        feat2 = SurfaceFeatures.from_dict(d)
        assert feat2.family == "roof"
        assert feat2.vec == feat.vec

    def test_feature_vector_to_dict(self):
        from backend.app.brand_dna.features_2d import feature_vector_to_dict
        d = feature_vector_to_dict([0.0] * 12)
        assert set(d.keys()) == set(FEATURE_NAMES)


# ============================================================
# 3. 品牌合规判定测试
# ============================================================

class TestOnBrand:
    """验证品牌合规判定引擎"""

    @pytest.fixture
    def sample_dna(self):
        return {
            "brand": {"key": "test_brand", "name": "Test", "zh_name": "测试"},
            "on_brand_constraints": {
                "character_line_depth": {
                    "rule": "=0.0", "trait": "温润", "principle": "藏锋于润",
                },
                "grille_openness": {
                    "rule": "=0.0", "trait": "纯净", "principle": "藏奢于简",
                },
                "light_blend": {
                    "rule": "≥0.85", "trait": "温润", "principle": "藏锋于润",
                },
                "body_tumblehome": {
                    "rule": "≤0.03", "trait": "温润", "principle": "藏锋于润",
                },
                "front_fascia": {
                    "rule": "=sealed", "trait": "纯净", "principle": "藏奢于简",
                },
            },
        }

    def test_all_pass(self, sample_dna):
        measured = {
            "character_line_depth": 0.0,
            "grille_openness": 0.0,
            "light_blend": 0.9,
            "body_tumblehome": 0.02,
            "front_fascia": "sealed",
        }
        result = evaluate_on_brand(sample_dna, measured)
        assert result.pass_count == 5
        assert result.fail_count == 0
        assert result.score == 100.0

    def test_some_fail(self, sample_dna):
        measured = {
            "character_line_depth": 5.0,  # FAIL
            "grille_openness": 0.0,       # PASS
            "light_blend": 0.7,           # FAIL
            "body_tumblehome": 0.02,      # PASS
            "front_fascia": "open",       # FAIL
        }
        result = evaluate_on_brand(sample_dna, measured)
        assert result.pass_count == 2
        assert result.fail_count == 3
        assert result.score == pytest.approx(40.0, abs=0.1)

    def test_no_data(self, sample_dna):
        """未提供测量值的项应为 NO_DATA"""
        measured = {"character_line_depth": 0.0}
        result = evaluate_on_brand(sample_dna, measured)
        assert result.no_data_count == 4
        # NO_DATA 不计入 score
        assert result.score == 100.0

    def test_clause_serialization(self):
        c = Clause(key="x", rule="=0.0", status="PASS", trait="t", principle="p")
        d = c.as_dict()
        c2 = Clause.from_dict(d)
        assert c2.key == "x"
        assert c2.status == "PASS"


# ============================================================
# 4. Schema 校验测试
# ============================================================

class TestSchema:
    def test_valid_dna(self):
        dna = {
            "brand": {"key": "x", "name": "X", "zh_name": "X"},
            "on_brand_constraints": {"k": {"rule": "=0.0"}},
        }
        ok, errors = validate_dna(dna)
        assert ok
        assert errors == []

    def test_missing_brand(self):
        ok, errors = validate_dna({"on_brand_constraints": {}})
        assert not ok
        assert any("brand" in e for e in errors)

    def test_template_has_all_fields(self):
        from backend.app.brand_dna.schema import load_schema_template
        tpl = load_schema_template()
        assert tpl["schema_version"] == "1.0"
        assert "brand" in tpl
        assert "on_brand_constraints" in tpl
        assert "models" in tpl


# ============================================================
# 5. 加载器隔离测试
# ============================================================

class TestLoader:
    def test_confidential_not_persisted(self, tmp_path):
        """机密级 DNA 不持久化"""
        conf_dna = {
            "_CONFIDENTIAL": {"level": "confidential"},
            "brand": {"key": "secret", "name": "S", "zh_name": "机密"},
            "on_brand_constraints": {"k": {"rule": "=0.0"}},
        }
        f = tmp_path / "secret.json"
        f.write_text(json.dumps(conf_dna, ensure_ascii=False), encoding="utf-8")

        ok, msg, dna = import_dna_file(str(f), persist=True)
        assert ok
        assert "仅内存" in msg
        # 不应出现在平台存储中
        assert load_dna("secret") is None

    def test_public_dna_persisted(self, tmp_path):
        """公开级 DNA 可持久化"""
        pub_dna = {
            "_CONFIDENTIAL": {"level": "public"},
            "brand": {"key": "pub", "name": "P", "zh_name": "公开"},
            "on_brand_constraints": {"k": {"rule": "=0.0"}},
        }
        f = tmp_path / "pub.json"
        f.write_text(json.dumps(pub_dna, ensure_ascii=False), encoding="utf-8")

        ok, msg, dna = import_dna_file(str(f), persist=True)
        assert ok
        loaded = load_dna("pub")
        assert loaded is not None
        assert loaded["brand"]["key"] == "pub"

    def test_invalid_json_rejected(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid json", encoding="utf-8")
        ok, msg, _ = import_dna_file(str(f))
        assert not ok

    def test_list_available(self):
        dnas = list_available_dnas()
        assert isinstance(dnas, list)


# ============================================================
# 6. 端到端兼容性测试
# ============================================================

class TestEndToEndCompatibility:
    """验证 brand_dna 可独立完成 特征提取 → 合规判定 全流程"""

    def test_full_pipeline(self):
        # 1. 构造一个品牌 DNA
        dna = {
            "brand": {"key": "demo", "name": "Demo", "zh_name": "演示"},
            "on_brand_constraints": {
                "character_line_depth": {"rule": "=0.0", "trait": "温润"},
                "light_blend": {"rule": "≥0.85", "trait": "温润"},
            },
        }

        # 2. 提取曲面特征
        cp = np.zeros((6, 6, 3))
        for i in range(6):
            for j in range(6):
                cp[i, j] = [i * 100, j * 100, np.sin(i * 0.5) * 50]

        feat = extract_features(cp, degree_u=5, degree_v=5, family="hood")
        assert feat is not None
        assert len(feat.vec) == 12

        # 3. 合规判定
        measured = {"character_line_depth": 0.0, "light_blend": 0.9}
        result = evaluate_on_brand(dna, measured)
        assert result.pass_count == 2
        assert result.score == 100.0

    def test_sisa_data_contract_compatible(self):
        """验证输出格式与 SISA 数据契约兼容"""
        feat = SurfaceFeatures(family="roof", source="sisa_import", vec=[0.5] * 12)
        d = feat.as_dict()
        # SISA 的 SurfaceFeatures.as_dict() 输出这三个字段
        assert set(d.keys()) == {"family", "source", "vec"}

        c = Clause(key="x", rule="=0.0", status="PASS")
        cd = c.as_dict()
        # SISA 的 Clause.as_dict() 输出这些字段
        assert set(cd.keys()) == {
            "key", "rule", "status", "trait", "principle", "measured", "note",
        }
