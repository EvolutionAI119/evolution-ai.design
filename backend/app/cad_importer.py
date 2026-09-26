"""CAD 文件导入器：解析 STEP / IGES / STP / IGS / STL / OBJ / CATPart / Wire 等整车数据，
反推出 automotive_parameters 的参数覆盖字典。

实现原则：
1. **最佳努力（Best-effort）反推**：不同 CAD 格式包含的几何语义差异极大，能精确提取就精确提取，
   无法确定时用默认值兜底，绝不因格式解析失败而阻断导入流程。
2. **分层回退策略**：
   - 第一层：trimesh 直接加载 mesh → 合并包围盒 + 部件级包围盒分析 → 反推参数
   - 第二层：STEP / IGES 文本解析提取 CARTESIAN_POINT 云 → 计算包围盒
   - 第三层（CATPart/Wire 专有格式）：不解析几何，保存原始文件到 data/uploads，
     用默认参数创建会话，并在 session.meta 中标记 "source_format"，后续 Export 可以选择回传原文件。
3. **坐标系约定**：
   车身坐标系：X = 车长方向（前-后），Y = 车高方向（底-顶），Z = 车宽方向（左-右），单位 mm。
   导入的数据若方向不对，会根据包围盒维度自动排序匹配 (最长边→X，次长→Z，最短→Y)。
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import settings


# ============== 支持的 CAD 格式 ==============

CAD_FORMAT_EXTENSIONS = {
    # 通用中性格式
    ".step", ".stp", ".iges", ".igs",
    # 三角网格格式
    ".stl", ".obj", ".glb", ".gltf",
    # CATIA 专有格式（导入时走第三层兜底策略）
    ".catpart", ".catproduct", ".cgr",
    # Wire 格式（通常为简单点/线集合，后缀多样统一处理）
    ".wire", ".wrl", ".igs_wire",
}

CAD_FORMAT_LABELS = {
    ".step": "STEP (AP214/242)",
    ".stp": "STEP (Alias)",
    ".iges": "IGES (5.3)",
    ".igs": "IGES (Alias)",
    ".stl": "STL (Mesh)",
    ".obj": "Wavefront OBJ",
    ".glb": "GLTF Binary",
    ".gltf": "GLTF JSON",
    ".catpart": "CATIA V5/V6 Part",
    ".catproduct": "CATIA Product",
    ".cgr": "CATIA CGR",
    ".wire": "Wire (Curve Set)",
    ".wrl": "VRML Wireframe",
    ".igs_wire": "IGES Wire",
}

# 分组英文稳定键 → automotive_parameters.json 中使用的中文 key
# infer_car_params 内部始终写英文稳定键；这里在写 overrides 字典时做一次转换，
# 保证结果字典的 key 能被 import_export.py 的 _normalize_group 双向识别（中英文都能命中）。
GROUP_EN_TO_ZH = {
    "overall_dimensions": "整车尺寸",
    "body_components": "车身部件",
    "styling_angles": "造型角度",
    "class_a_params": "A级曲面参数",
    "proportions": "比例参数",
}
GROUP_ZH_TO_EN = {v: k for k, v in GROUP_EN_TO_ZH.items()}


@dataclass
class ImportedGeometry:
    """从 CAD 文件提取的几何信息（参数反推的输入）"""
    source_file: str
    format_ext: str
    # 总包围盒 (min, max)，形状 (2,3)，顺序 [X,Y,Z] = [长度,高度,宽度]
    overall_bbox: np.ndarray
    # 部件级包围盒列表：[{name, bbox(2,3), centroid(3,)}]
    parts: List[Dict[str, Any]] = field(default_factory=list)
    # 原始点云（若格式仅能提取点），形状 (N,3)
    point_cloud: Optional[np.ndarray] = None
    # 单位推断：mm / m / cm / in — 用于统一缩放
    unit_scale: float = 1.0
    # 几何解析是否成功（False 表示走兜底策略）
    geometry_parsed: bool = True
    # 警告/备注（显示给用户）
    warnings: List[str] = field(default_factory=list)


# ============== 辅助函数 ==============

def _norm_ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def _save_uploaded_bytes(raw: bytes, filename: str) -> Path:
    """保存上传的原始 CAD 文件到 data/uploads，供后续回溯下载"""
    upload_dir = Path(settings.DATA_DIR).resolve() / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_stem = re.sub(r"[^\w\-.]+", "_", Path(filename).stem)[:60] or "cad_file"
    ext = _norm_ext(filename)
    out = upload_dir / f"{ts}_{uuid.uuid4().hex[:6]}_{safe_stem}{ext}"
    out.write_bytes(raw)
    return out


def _reorder_bbox_axes(raw_min: np.ndarray, raw_max: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    """
    根据包围盒三个维度的大小，自动对齐到汽车坐标系约定：
        X轴 = 最长边（车长 overall_length）
        Z轴 = 次长边（车宽 overall_width）
        Y轴 = 最短边（车高 overall_height）
    返回 (reordered_min, reordered_max, axis_mapping)
        axis_mapping: {"x": src_axis_idx, "y": src_axis_idx, "z": src_axis_idx}
    """
    sizes = raw_max - raw_min
    order = np.argsort(-sizes)  # 从大到小 [largest, middle, smallest]
    # 映射目标轴 [X, Z, Y] ← 对应排序后的 [0,1,2]
    target = [0, 2, 1]  # order[0]->X, order[1]->Z, order[2]->Y
    axis_mapping = {"x": int(order[0]), "y": int(order[2]), "z": int(order[1])}
    new_min = np.array([
        raw_min[order[0]],  # X (length)
        raw_min[order[2]],  # Y (height)
        raw_min[order[1]],  # Z (width)
    ])
    new_max = np.array([
        raw_max[order[0]],
        raw_max[order[2]],
        raw_max[order[1]],
    ])
    return new_min, new_max, axis_mapping


def _infer_unit_scale(bbox_size: np.ndarray, warnings: List[str]) -> float:
    """Infer length unit from overall bounding box and scale everything to mm.

    Vehicle size reference (in mm):
    - Compact car:      3500..4500 mm
    - Mid-size car:     4500..5000 mm
    - Full-size car:    5000..5500 mm
    - SUV:              4400..5200 mm
    - Minivan:          4800..5200 mm
    - Truck/Bus:        6000..15000+ mm

    CAD files may use mm, cm, m, or inches. The function tries to detect
    the unit by matching the bbox length against known vehicle size ranges.
    For large bbox values (>6000mm), we check if it's a large vehicle or
    if the model has a coordinate offset (common in CAD assemblies).

    Detection order (non-overlapping ranges):
    1. Already in mm (500-6000mm) → no scaling
    2. Large vehicle in mm (6000-50000mm) → no scaling, warn
    3. Micrometers (50000-50000000μm) → ÷1000 to mm
    4. Meters (0.5-50m) → ×1000 to mm
    5. Decimeters (5-500dm) → ×100 to mm
    6. Centimeters (50-500cm) → ×10 to mm
    7. Inches (20-2000in) → ×25.4 to mm
    8. Fallback → no scaling, warn
    """
    L = bbox_size[0]
    if L == 0:
        warnings.append("Bounding box size is 0, skipping unit calibration")
        return 1.0

    # 1. Already in mm range for normal vehicles (500mm–6m)
    if 500 <= L <= 6000:
        return 1.0

    # 2. Large vehicle in mm (truck, bus, or large SUV with coordinate offset)
    #    Up to 50m covers full-size trucks and CAD assemblies with origin offsets
    if 6000 < L <= 50000:
        warnings.append(
            f"Detected length {L:.0f} mm — treating as millimeters (large vehicle or coordinate offset). "
            f"No scaling applied."
        )
        return 1.0

    # 3. Micrometers → mm (common in some precision CAD formats, e.g. CATIA)
    #    50mm–50000mm in micrometers = 50000–50000000μm
    if 50000 <= L <= 50000000:
        scaled = L / 1000.0
        if 500 <= scaled <= 50000:
            warnings.append(
                f"Unit inferred as micrometers (length ≈ {L:.0f} μm). Auto-scaled ÷1000 to mm."
            )
            return 0.001

    # 4. Meters → mm (common in some CAD systems, e.g. STEP with meter units)
    #    0.5m–50m = 500mm–50000mm
    if 0.5 <= L <= 50:
        scaled = L * 1000
        if 500 <= scaled <= 50000:
            warnings.append(
                f"Unit inferred as meters (length ≈ {L:.2f} m). Auto-scaled ×1000 to mm."
            )
            return 1000.0

    # 5. Decimeters → mm (rare but possible in some older CAD systems)
    #    5dm–500dm = 500mm–50000mm
    if 5 <= L <= 500:
        scaled = L * 100
        if 500 <= scaled <= 50000:
            warnings.append(
                f"Unit inferred as decimeters (length ≈ {L:.1f} dm). Auto-scaled ×100 to mm."
            )
            return 100.0

    # 6. Centimeters → mm
    #    50cm–500cm = 500mm–5000mm
    if 50 <= L <= 500:
        scaled = L * 10
        if 500 <= scaled <= 50000:
            warnings.append(
                f"Unit inferred as centimeters (length ≈ {L:.0f} cm). Auto-scaled ×10 to mm."
            )
            return 10.0

    # 7. Inches → mm (common in US-based CAD systems)
    #    20in–2000in = 508mm–50800mm
    if 20 <= L <= 2000:
        scaled = L * 25.4
        if 500 <= scaled <= 50000:
            warnings.append(
                f"Unit inferred as inches (length ≈ {L:.1f} in). Auto-scaled ×25.4 to mm."
            )
            return 25.4

    # 8. Fallback: unable to determine unit
    warnings.append(
        f"Unable to auto-infer unit (detected length {L:.1f}). "
        f"Keeping raw values as-is. If dimensions look wrong, the CAD file "
        f"may use a non-standard unit."
    )
    return 1.0


# ============== Loader 1: trimesh (STL/OBJ/GLB/STEP etc.) ==============

def _load_via_trimesh(filepath: Path, warnings: List[str]) -> Optional[ImportedGeometry]:
    try:
        import trimesh
    except Exception as e:
        warnings.append(f"trimesh is not available: {e}")
        return None
    try:
        loaded = trimesh.load(str(filepath), force="scene")
    except Exception as e:
        warnings.append(f"trimesh.load failed for {filepath.suffix}: {e}")
        return None

    scene = loaded if hasattr(loaded, "geometry") else None
    if scene is None and isinstance(loaded, trimesh.Trimesh):
        scene = trimesh.Scene([loaded])
    if scene is None:
        warnings.append(f"Load result is {type(loaded).__name__}: no geometries extracted")
        return None

    all_points = []
    parts = []
    for name, geom in scene.geometry.items():
        if not hasattr(geom, "vertices") or geom.vertices is None or len(geom.vertices) == 0:
            continue
        vs = np.asarray(geom.vertices, dtype=np.float64)
        all_points.append(vs)
        mn, mx = vs.min(axis=0), vs.max(axis=0)
        centroid = (mn + mx) / 2
        parts.append({
            "name": str(name) or f"part_{len(parts)}",
            "bbox": np.stack([mn, mx]),
            "centroid": centroid,
            "vertices_count": len(vs),
        })
    if not all_points:
        warnings.append("No vertex data found in CAD file")
        return None
    cloud = np.vstack(all_points)
    raw_min, raw_max = cloud.min(axis=0), cloud.max(axis=0)
    return ImportedGeometry(
        source_file=str(filepath),
        format_ext=_norm_ext(filepath.name),
        overall_bbox=np.stack([raw_min, raw_max]),
        parts=parts,
        point_cloud=cloud,
    )


# ============== Loader 2: STEP / IGES text parsing (CARTESIAN_POINT) ==============

_CP_STEP_RE = re.compile(r"CARTESIAN_POINT\s*[^,]*,\s*\(\s*([\-0-9\.eE+\s]+)\s*,\s*([\-0-9\.eE+\s]+)\s*,\s*([\-0-9\.eE+\s]+)\s*\)")


def _parse_step_text_points(text: str, limit: int = 50000) -> Optional[np.ndarray]:
    pts = []
    for m in _CP_STEP_RE.finditer(text):
        try:
            x, y, z = float(m.group(1)), float(m.group(2)), float(m.group(3))
            pts.append((x, y, z))
            if len(pts) >= limit:
                break
        except ValueError:
            continue
    return np.array(pts, dtype=np.float64) if pts else None


_IGES_SECTION_RE = re.compile(r"[SGDPT]\s+\d+\s*$")


def _extract_iges_entity_coordinates(
    entity_type: int, params: List[float]
) -> List[Tuple[float, float, float]]:
    """Extract control point coordinates from IGES entity parameter list,
    skipping structural parameters based on entity type.

    Only entities known to contain direct coordinate data are processed;
    topological entities (504 Edge List, 508 Loop, 510 Face, 514 Shell, etc.)
    are skipped to avoid misinterpreting their integer reference parameters as
    coordinates.

    Entity 126 (Rational B-Spline Curve):
        Index 0..5: K, M, A(planar), B(closed), C(rational), D(polynomial)
        Index 6..:  knots (M+K+2 values), optional weights (K+1 if C=1),
                    then control points (K+1)*3.
    Entity 128 (Rational B-Spline Surface):
        Index 0..9: K1, K2, M1, M2, A, B(u closed), C(v closed), D(rational),
                    E(polynomial), F(periodic)
        Index 10..: knots u (K1+M1+2), knots v (K2+M2+2),
                    optional weights ((K1+1)*(K2+1) if D=1),
                    then control points (K1+1)*(K2+1)*3.
    Entity 502 (Vertex List):
        Index 0: N (number of vertices)
        Index 1..: N*3 coordinate values.
    Entity 100 (Circular Arc): Z-axis + center + start + end.
    Entity 110 (Line): start point + end point.
    Entity 116 (Point): single X, Y, Z triple.
    """
    pts: List[Tuple[float, float, float]] = []
    try:
        if entity_type == 126:  # Rational B-Spline Curve
            if len(params) < 6:
                return pts
            K = int(params[0])
            M = int(params[1])
            rational = int(params[4]) == 1
            num_knots = M + K + 2
            num_cp = K + 1
            offset = 6 + num_knots
            if rational:
                offset += num_cp
            if len(params) < offset + num_cp * 3:
                return pts
            for i in range(num_cp):
                idx = offset + i * 3
                pts.append((params[idx], params[idx + 1], params[idx + 2]))

        elif entity_type == 128:  # Rational B-Spline Surface
            if len(params) < 10:
                return pts
            K1 = int(params[0])
            K2 = int(params[1])
            M1 = int(params[2])
            M2 = int(params[3])
            rational = int(params[7]) == 1
            num_u_knots = K1 + M1 + 2
            num_v_knots = K2 + M2 + 2
            num_cp = (K1 + 1) * (K2 + 1)
            offset = 10 + num_u_knots + num_v_knots
            if rational:
                offset += num_cp
            if len(params) < offset + num_cp * 3:
                return pts
            for i in range(num_cp):
                idx = offset + i * 3
                pts.append((params[idx], params[idx + 1], params[idx + 2]))

        elif entity_type == 502:  # Vertex List
            if len(params) < 1:
                return pts
            N = int(params[0])
            offset = 1  # only N is structural
            if N <= 0 or len(params) < offset + N * 3:
                return pts
            for i in range(N):
                idx = offset + i * 3
                pts.append((params[idx], params[idx + 1], params[idx + 2]))

        elif entity_type == 100:  # Circular Arc
            # Parameters: Zt, Xc, Yc, Xs, Ys, Xe, Ye (7 values)
            if len(params) < 7:
                return pts
            # center point (Xc, Yc, Zt)
            pts.append((params[1], params[2], params[0]))
            # start point (Xs, Ys, Zt)
            pts.append((params[3], params[4], params[0]))
            # end point (Xe, Ye, Zt)
            pts.append((params[5], params[6], params[0]))

        elif entity_type == 110:  # Line
            # start point + end point
            if len(params) < 6:
                return pts
            pts.append((params[0], params[1], params[2]))
            pts.append((params[3], params[4], params[5]))

        elif entity_type == 116:  # Point
            if len(params) < 3:
                return pts
            pts.append((params[0], params[1], params[2]))

        # Other entity types (508/510/514 topology, 124 transform, 102/142
        # composite/curve-on-surface, etc.) are intentionally skipped — their
        # parameters are integer references or matrix elements, not coordinates.

    except (ValueError, IndexError):
        # If entity structure is malformed, skip it rather than crash.
        return pts
    return pts


def _parse_iges_text_points(text: str, limit: int = 50000) -> Optional[np.ndarray]:
    """Parse IGES Parameter Data (P) section for control point coordinates.

    Uses an entity-aware parsing strategy: splits the P-section by the record
    separator (';') into individual entity parameter blocks, then for each
    block reads the leading entity type number and applies entity-specific
    offset rules (Entity 126/128/502/100/110/116) to skip structural
    parameters (knots, weights, counts, topology references) and extract
    only coordinate values.

    P-section line detection is tolerant of both strict 80-column IGES and
    non-standard line widths (look for 'P' section marker + sequence number
    in the trailing region of the line).

    After extraction, applies statistical outlier filtering (MAD-based 3σ rule)
    to remove any residual non-coordinate values that slipped through.
    """
    lines = text.splitlines()
    p_lines: List[str] = []
    for line in lines:
        # Strict: column 73 (0-indexed 72) == 'P' in 80-column format
        is_p = len(line) >= 73 and line[72] == "P"
        if not is_p:
            # Flexible: line ends with pattern like "P      1" (section marker + sequence)
            tail = line.rstrip("\n\r")[-12:] if line else ""
            if _IGES_SECTION_RE.search(tail):
                is_p = tail.lstrip()[0] == "P" if tail.strip() else False
                # Fallback: check if 'P' is the first non-space char in the trailing region
                if not is_p:
                    m = re.search(r"\bP\s+\d+\s*$", line)
                    is_p = bool(m)
        if is_p:
            # Per IGES spec: cols 1-64 hold parameter data, cols 65-72 hold
            # the back-pointer to the Directory Entry, col 73 is 'P', cols
            # 74-80 are the sequence number. Strip everything from col 65 on.
            if len(line) >= 73:
                clean = line[:64].rstrip()
            else:
                # Non-standard widths: truncate at the section marker 'P'
                idx = line.rfind("P") if "P" in line else len(line)
                clean = line[:idx].rstrip() if idx > 0 else line.rstrip("\n\r")
            if clean:
                p_lines.append(clean)
    if not p_lines:
        return None

    # Concatenate all P-section content (entities may span multiple lines)
    joined = " ".join(p_lines)

    # Split into individual entity blocks using the IGES record separator ';'.
    # Each block's first parameter is the entity type number.
    all_points: List[Tuple[float, float, float]] = []
    for block in joined.split(";"):
        block = block.strip()
        if not block:
            continue
        # Parameters within an entity are separated by ','; parse numbers,
        # skipping any non-numeric tokens (e.g., Hollerith labels like '7Hfoo').
        params: List[float] = []
        for tok in block.split(","):
            tok = tok.strip()
            if not tok:
                continue
            # Normalize Fortran-style exponent markers (1.0D-3 -> 1.0E-3)
            norm = tok.replace("D", "E").replace("d", "e")
            try:
                params.append(float(norm))
            except ValueError:
                continue
        if not params:
            continue
        entity_type = int(params[0])
        coords = _extract_iges_entity_coordinates(entity_type, params[1:])
        if coords:
            all_points.extend(coords)
            if len(all_points) >= limit:
                break

    if not all_points:
        return None

    arr = np.array(all_points[:limit], dtype=np.float64).reshape(-1, 3)

    # Apply statistical outlier filtering to remove any residual non-coordinate
    # values (e.g., transform-matrix entries from unknown entity types).
    filtered = _filter_point_cloud_outliers(arr)
    if len(filtered) >= 3:
        return filtered
    # If filtering removed too many points, return original (better than nothing)
    return arr


def _filter_point_cloud_outliers(
    points: np.ndarray, sigma_threshold: float = 3.0
) -> np.ndarray:
    """Remove statistical outliers from a point cloud using the 3σ rule.

    For each axis, computes the median and median absolute deviation (MAD),
    then removes points where any coordinate deviates more than
    sigma_threshold * 1.4826 * MAD from the median (1.4826 scales MAD to
    approximate standard deviation for normally distributed data).

    This effectively filters out non-coordinate floats (entity parameters
    like circle radius, line distance, etc.) that are scattered far from
    the main geometry cluster.
    """
    if len(points) < 10:
        return points

    medians = np.median(points, axis=0)
    # Median Absolute Deviation (robust estimate of standard deviation)
    abs_deviations = np.abs(points - medians)
    mad = np.median(abs_deviations, axis=0)
    # Scale factor to approximate standard deviation
    sigma = np.where(mad > 0, mad * 1.4826, 1e-10)
    # Distance of each point from median in units of sigma
    normalized_dist = np.max(abs_deviations / sigma, axis=1)
    # Keep points within sigma_threshold standard deviations
    mask = normalized_dist <= sigma_threshold
    filtered = points[mask]

    # Ensure we don't filter too aggressively — keep at least 50% of points
    if len(filtered) < len(points) * 0.5:
        return points

    return filtered


def _load_via_text_parse(filepath: Path, warnings: List[str]) -> Optional[ImportedGeometry]:
    """Fallback loader for STEP / IGES when trimesh backend is unavailable."""
    ext = _norm_ext(filepath.name)
    try:
        raw = filepath.read_bytes()
        text = raw.decode("utf-8", errors="ignore")
    except Exception as e:
        warnings.append(f"Cannot read CAD file as text: {e}")
        return None
    pts: Optional[np.ndarray] = None
    if ext in (".step", ".stp"):
        pts = _parse_step_text_points(text)
        if pts is None:
            warnings.append("STEP text parsing yielded no CARTESIAN_POINT")
    elif ext in (".iges", ".igs"):
        pts = _parse_iges_text_points(text)
        if pts is None:
            warnings.append("IGES text parsing yielded no coordinate points")
    if pts is None or len(pts) < 3:
        return None
    raw_min, raw_max = pts.min(axis=0), pts.max(axis=0)
    return ImportedGeometry(
        source_file=str(filepath),
        format_ext=ext,
        overall_bbox=np.stack([raw_min, raw_max]),
        parts=[{
            "name": "point_cloud",
            "bbox": np.stack([raw_min, raw_max]),
            "centroid": (raw_min + raw_max) / 2,
            "vertices_count": len(pts),
        }],
        point_cloud=pts,
    )


# ============== 主入口：加载 CAD 并统一坐标系+单位 ==============

def load_cad_geometry(raw: bytes, filename: str) -> ImportedGeometry:
    """
    入口函数：把上传的 bytes 落到磁盘，依次尝试各层加载器。
    返回统一后的 ImportedGeometry（已完成坐标系重排 + 单位校准）。
    """
    ext = _norm_ext(filename)
    if ext not in CAD_FORMAT_EXTENSIONS and ext != ".json":
        raise ValueError(
            f"不支持的 CAD 格式: {ext!r}。支持: {sorted(CAD_FORMAT_EXTENSIONS)} + .json 参数"
        )
    saved_path = _save_uploaded_bytes(raw, filename)
    warnings: List[str] = []
    geom: Optional[ImportedGeometry] = None

    # Layer 1: trimesh 直接加载
    geom = _load_via_trimesh(saved_path, warnings)

    # Layer 2: 文本解析 STEP / IGES 点
    if geom is None and ext in (".step", ".stp", ".iges", ".igs"):
        geom = _load_via_text_parse(saved_path, warnings)

    if geom is None:
        # Layer 3: Fallback for proprietary formats (CATPart / Wire / etc.)
        geom = ImportedGeometry(
            source_file=str(saved_path),
            format_ext=ext,
            overall_bbox=np.array([[0, 0, 0], [0, 0, 0]], dtype=np.float64),
            geometry_parsed=False,
        )
        label = CAD_FORMAT_LABELS.get(ext, ext)
        warnings.append(
            f"{label} is a proprietary/binary format; geometry-based parameter "
            f"inference is not supported yet. Fallback applied: the original file "
            f"has been preserved and the session was seeded with default parameters. "
            f"The original file can be retrieved later via 'Export -> Export original'."
        )
        geom.warnings = warnings
        geom.source_file_ref = str(saved_path)  # type: ignore[attr-defined]
        return geom

    # 统一坐标系：轴重排
    raw_min, raw_max = geom.overall_bbox[0], geom.overall_bbox[1]
    new_min, new_max, mapping = _reorder_bbox_axes(raw_min, raw_max)

    def remap_bbox(b: np.ndarray) -> np.ndarray:
        src = b.flatten().reshape(2, 3)
        out = np.zeros((2, 3), dtype=np.float64)
        for target_axis, src_axis in mapping.items():
            ti = {"x": 0, "y": 1, "z": 2}[target_axis]
            out[:, ti] = src[:, src_axis]
        return out

    def remap_point(p: np.ndarray) -> np.ndarray:
        out = np.zeros(3, dtype=np.float64)
        for target_axis, src_axis in mapping.items():
            ti = {"x": 0, "y": 1, "z": 2}[target_axis]
            out[ti] = p[src_axis]
        return out

    geom.overall_bbox = np.stack([new_min, new_max])
    for part in geom.parts:
        part["bbox"] = remap_bbox(part["bbox"])
        part["centroid"] = remap_point(part["centroid"])
    if geom.point_cloud is not None:
        geom.point_cloud = np.apply_along_axis(remap_point, 1, geom.point_cloud)

    # 统一单位 → mm
    size = geom.overall_bbox[1] - geom.overall_bbox[0]
    scale = _infer_unit_scale(size, warnings)
    if scale != 1.0:
        geom.overall_bbox *= scale
        for part in geom.parts:
            part["bbox"] *= scale
            part["centroid"] *= scale
        if geom.point_cloud is not None:
            geom.point_cloud *= scale
        geom.unit_scale = scale

    geom.warnings = warnings
    # 保存原始文件引用（后续下载用）
    geom.source_file_ref = str(saved_path)  # type: ignore[attr-defined]
    return geom


# ============== Parameter inference engine: ImportedGeometry → overrides dict ==============

def infer_car_params(geom: ImportedGeometry,
                     default_params: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Reverse-engineer automotive_parameters overrides from extracted geometry.

    All group keys in the returned dict use **Chinese keys** (matching
    automotive_parameters.json) because import_export.py already recognizes
    both Chinese and English group keys via _normalize_group; keeping Chinese
    here avoids a second normalization pass and simplifies round-trip
    inspection.
    """
    overrides: Dict[str, Dict[str, float]] = {}

    if not geom.geometry_parsed:
        return overrides

    bbox = geom.overall_bbox
    size = bbox[1] - bbox[0]
    L, H, W = size[0], size[1], size[2]
    centroid = (bbox[0] + bbox[1]) / 2

    def _set(group_en: str, key: str, val: float) -> None:
        """Apply inferred value. Accepts an ENGLISH group stable key.

        - clamps to the default config's [min_value, max_value]
        - emits ENGLISH warnings that reference GROUP_EN.key so the UI can
          display them directly in an English-only locale.
        """
        group_zh = GROUP_EN_TO_ZH.get(group_en)
        if not group_zh or group_zh not in default_params or key not in default_params[group_zh]:
            return
        meta = default_params[group_zh][key]
        if not isinstance(meta, dict) or "value" not in meta:
            return
        lo = meta.get("min_value", float("-inf"))
        hi = meta.get("max_value", float("inf"))
        clamped = False
        if val < lo:
            val = lo
            clamped = True
            geom.warnings.append(
                f"Parameter {group_en}.{key} inferred below min ({lo}); clamped to min."
            )
        elif val > hi:
            val = hi
            clamped = True
            geom.warnings.append(
                f"Parameter {group_en}.{key} inferred above max ({hi}); clamped to max."
            )
        _ = clamped  # silence unused-assignment if we later hook logging
        overrides.setdefault(group_zh, {})[key] = float(val)

    # ---- Overall dimensions ----
    _set("overall_dimensions", "overall_length", L)
    _set("overall_dimensions", "overall_width", W)
    _set("overall_dimensions", "overall_height", H)

    _set("overall_dimensions", "track_width", W * 0.85)

    # Wheelbase: ~55-62% of overall length, higher for taller bodies (SUV/van).
    ratio = 0.58
    if H / max(L, 1e-6) > 0.35:
        ratio = 0.60   # SUV / Van
    elif H / max(L, 1e-6) < 0.27:
        ratio = 0.56   # Sport coupe
    wheelbase = L * ratio
    _set("overall_dimensions", "wheelbase", wheelbase)

    # Overhangs: front + rear = overall_length - wheelbase
    overhang_total = L - wheelbase
    x_offset_norm = 0.0
    if L > 1e-6:
        x_offset_norm = (centroid[0] - (bbox[0, 0] + L / 2)) / L
    front_ratio = 0.45 - x_offset_norm * 0.8  # centroid rearwards → shorter front overhang
    front_ratio = max(0.35, min(0.55, front_ratio))
    _set("proportions", "overhang_front", overhang_total * front_ratio)
    _set("proportions", "overhang_rear",  overhang_total * (1 - front_ratio))

    # Ground clearance: ~13% of height for sedans, ~18% for SUVs
    if H / max(L, 1e-6) > 0.35:
        _set("overall_dimensions", "ground_clearance", H * 0.18)
    else:
        _set("overall_dimensions", "ground_clearance", H * 0.13)

    # ---- Body component sizing ----
    front_overhang = overhang_total * front_ratio
    rear_overhang  = overhang_total * (1 - front_ratio)

    _set("body_components", "hood_length", front_overhang * 0.9)
    _set("body_components", "hood_width",  W * 0.78)
    _set("body_components", "hood_height", H * 0.12)

    _set("body_components", "trunk_length", rear_overhang * 0.85)
    _set("body_components", "trunk_width",  W * 0.78)

    _set("body_components", "windshield_width",  W * 0.78)
    _set("body_components", "windshield_height", H * 0.35)
    _set("body_components", "rear_window_width", W * 0.72)
    _set("body_components", "rear_window_height", H * 0.28)

    roof_len = wheelbase * (0.65 if H / max(L, 1e-6) > 0.33 else 0.55)
    _set("body_components", "roof_length", roof_len)
    _set("body_components", "roof_width",  W * 0.75)
    _set("body_components", "roof_height", H * 0.08)

    door_total = wheelbase * 0.6
    _set("body_components", "door_front_length", door_total * 0.55)
    _set("body_components", "door_front_height", H * 0.55)
    _set("body_components", "door_rear_length",  door_total * 0.45)
    _set("body_components", "door_rear_height",  H * 0.52)

    wheel_diameter = H * (0.42 if H / max(L, 1e-6) > 0.33 else 0.38)
    _set("body_components", "wheel_diameter",   wheel_diameter)
    _set("body_components", "wheel_width",      wheel_diameter * 0.32)
    _set("body_components", "wheel_arch_radius", wheel_diameter * 0.6)

    _set("body_components", "headlight_height", H * 0.18)
    _set("body_components", "taillight_height", H * 0.22)
    _set("body_components", "grille_height",    H * 0.20)

    _set("body_components", "mirror_width",  wheel_diameter * 0.28)
    _set("body_components", "mirror_height", wheel_diameter * 0.32)
    _set("body_components", "mirror_depth",  wheel_diameter * 0.20)

    _set("body_components", "door_seam_width", 4.0)

    # ---- Styling angles ----
    body_hw_ratio = H / max(W, 1e-6)
    if body_hw_ratio > 0.85:
        ws_angle = 62.0   # more upright: SUV / boxy shapes
    elif body_hw_ratio < 0.72:
        ws_angle = 68.0   # more raked: coupe / aero shapes
    else:
        ws_angle = 65.0
    _set("styling_angles", "windshield_angle",   ws_angle)
    _set("styling_angles", "hood_angle",         3.0 if H / max(L, 1e-6) > 0.33 else 6.0)
    _set("styling_angles", "rear_slant_angle",   40.0 if body_hw_ratio < 0.72 else 25.0)
    _set("styling_angles", "rear_window_angle",  ws_angle - 8.0)

    # ---- Class A surface defaults (degrees retained, quality preserved) ----
    _set("class_a_params", "surface_degree_u", 3.0)
    _set("class_a_params", "surface_degree_v", 3.0)

    return overrides


# ============== 对外主函数：完整导入流水线 ==============

@dataclass
class CadImportResult:
    overrides: Dict[str, Dict[str, float]]
    name: str
    source_format: str
    source_file_ref: str
    geometry_parsed: bool
    warnings: List[str]
    bbox_size: List[float]  # [length, height, width] mm

    def to_meta(self) -> Dict[str, Any]:
        return {
            "source_format": self.source_format,
            "source_file": self.source_file_ref,
            "geometry_parsed": self.geometry_parsed,
            "warnings": self.warnings,
            "bbox_size_mm": self.bbox_size,
        }


def import_cad_file(raw: bytes, filename: str,
                    default_config: Dict[str, Any]) -> CadImportResult:
    """
    完整的 CAD 导入流水线：
      加载几何 → 反推 overrides → 返回结果
    """
    geom = load_cad_geometry(raw, filename)
    overrides = infer_car_params(geom, default_config.get("automotive_parameters", {}))
    bbox_size = (geom.overall_bbox[1] - geom.overall_bbox[0]).tolist() if geom.geometry_parsed else [0, 0, 0]
    name = Path(filename).stem
    if geom.geometry_parsed:
        name = f"{name}_L{int(round(bbox_size[0]))}"
    source_ref = getattr(geom, "source_file_ref", geom.source_file)
    return CadImportResult(
        overrides=overrides,
        name=name,
        source_format=CAD_FORMAT_LABELS.get(geom.format_ext, geom.format_ext),
        source_file_ref=source_ref,
        geometry_parsed=geom.geometry_parsed,
        warnings=geom.warnings,
        bbox_size=bbox_size,
    )
