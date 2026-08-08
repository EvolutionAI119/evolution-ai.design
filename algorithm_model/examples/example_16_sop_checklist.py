"""
Example 16 - A 表面标准 SOP 13 项检查清单

基于 A表面标准SOP.md，对 full_car_attached 全部曲面执行 SOP 检查：
  - 8 项自动检查（控制点/曲率/间隙/连续性等）
  - 5 项人工检查占位（坐标系/点云/特征线/Shading/截面）

输出: TXT + CSV 报告 + 控制台摘要
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from algorithm_model.car_modeling import (
    CarParams, ContinuityChecker, SOPChecklist,
)
from algorithm_model.car_modeling.body_nurbs import build_body_nurbs
from algorithm_model.car_modeling.body_ends_g1 import (
    build_front_bumper_g1, build_rear_bumper_g1,
)
from algorithm_model.car_modeling.body_ends_attached import (
    build_grille_attached, build_headlight_attached, build_taillight_attached,
)
from algorithm_model.car_modeling.accessories_nurbs import (
    build_all_wheels_nurbs, build_all_mirrors_nurbs,
)

OUT_DIR = os.path.join(_ROOT, "data", "step")


def build_all_surfaces(params):
    """构造 full_car_attached 所有零件。"""
    body = build_body_nurbs(params)
    fb = build_front_bumper_g1(params, body, g1_k=0.3, bulge=0.08)
    rb = build_rear_bumper_g1(params, body, g1_k=0.3, bulge=0.06)
    grille = build_grille_attached(params, fb, recess=0.06)
    hl_R = build_headlight_attached(params, fb, "right", bulge=0.02)
    hl_L = build_headlight_attached(params, fb, "left", bulge=0.02)
    tl_R = build_taillight_attached(params, rb, "right", bulge=0.015)
    tl_L = build_taillight_attached(params, rb, "left", bulge=0.015)
    wheels = build_all_wheels_nurbs(params)
    mirrors = build_all_mirrors_nurbs(params)

    items = [
        ("body_upper_skin", body),
        ("front_bumper_g1", fb),
        ("rear_bumper_g1", rb),
        ("grille_attached", grille),
        ("headlight_R", hl_R),
        ("headlight_L", hl_L),
        ("taillight_R", tl_R),
        ("taillight_L", tl_L),
    ]
    for s, n, _ in wheels + mirrors:
        items.append((n, s))
    return items


def main():
    print("=" * 70)
    print("Example 16 - A 表面标准 SOP 13 项检查清单")
    print("SOP-A SURF-001 | 基于 A表面标准SOP.md")
    print("=" * 70)
    t0 = time.time()

    params = CarParams()
    print("CarParams: L=%.2f W=%.2f H=%.2f" % (params.L, params.W, params.H))

    print("\n[1] Build surfaces...")
    items = build_all_surfaces(params)
    print("    %d surfaces built" % len(items))

    print("\n[2] Run ContinuityChecker...")
    checker = ContinuityChecker(
        g0_thresh_mm=0.1, g1_thresh_deg=1.0, g1_visual_deg=5.0,
        n_samples=50, skip_patterns=["wheel_", "mirror_"],
    )
    checker.add_surfaces(items)
    checker.analyze_all()
    s = checker.summary()
    print("    %d pairs | G1 OK=%d | G0+G1=%d" % (
        s["total_pairs"], s["g1_pass"], s["g0_g1_both"]))

    print("\n[3] Run SOP Checklist (13 items)...")
    sop = SOPChecklist(checker)
    sop.run()
    sop.print_summary()

    print("\n[4] Write reports...")
    txt_path, csv_path = sop.write_report(OUT_DIR, prefix="sop_checklist")
    print("    TXT: " + txt_path)
    print("    CSV: " + csv_path)

    print("\n" + "=" * 70)
    print("Done in %.2fs. Auto=%d PASS / %d FAIL | Manual=%d" % (
        time.time() - t0,
        sop.passed_count(), sop.failed_count(), sop.manual_count()))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
