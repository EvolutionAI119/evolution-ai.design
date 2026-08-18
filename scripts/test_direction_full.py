"""
车头方向检测 - 全量回归测试（19款车）
====================================
生产级验证：对所有19款车品牌图运行方向检测
每款车测试原图(期望left) + 翻转图(期望right)，共38个测试用例
"""
import sys
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import detect_car_direction, DIRECTION_CONFIG

ROOT = Path(__file__).resolve().parent.parent

# 19款车完整列表
ALL_CARS = [
    {"brand": "bentley", "model": "bentayga"},
    {"brand": "bentley", "model": "flying-spur"},
    {"brand": "bentley", "model": "continental-gtc"},
    {"brand": "bentley", "model": "continental-gt"},
    {"brand": "rolls-royce", "model": "cullinan"},
    {"brand": "rolls-royce", "model": "phantom"},
    {"brand": "rolls-royce", "model": "ghost"},
    {"brand": "rolls-royce", "model": "wraith"},
    {"brand": "ferrari", "model": "f8-tributo"},
    {"brand": "ferrari", "model": "sf90"},
    {"brand": "ferrari", "model": "roma"},
    {"brand": "porsche", "model": "911"},
    {"brand": "porsche", "model": "taycan"},
    {"brand": "porsche", "model": "macan"},
    {"brand": "porsche", "model": "cayenne"},
    {"brand": "porsche", "model": "panamera"},
    {"brand": "bugatti", "model": "divo"},
    {"brand": "bugatti", "model": "veyron"},
    {"brand": "bugatti", "model": "chiron"},
]


def main():
    print("=" * 80)
    print("  车头方向检测 - 全量回归测试（19款车 × 38用例）")
    print("=" * 80)

    results = []
    passed = 0
    failed = 0
    low_conf = 0

    for car in ALL_CARS:
        brand, model = car["brand"], car["model"]
        img_path = ROOT / "public" / "brands" / brand / f"{model}.jpg"

        if not img_path.exists():
            print(f"\n  ⚠️ 跳过 {brand}/{model} - 图片不存在")
            continue

        with Image.open(img_path) as im:
            arr = np.array(im.convert("RGB"))

        # 测试原图（期望车头向左）
        res_orig = detect_car_direction(arr, DIRECTION_CONFIG)
        pass_orig = res_orig["direction"] == "left"
        # 测试翻转图（期望车头向右）
        arr_flip = arr[:, ::-1, :].copy()
        res_flip = detect_car_direction(arr_flip, DIRECTION_CONFIG)
        pass_flip = res_flip["direction"] == "right" and res_flip["flip_needed"] == True

        both_pass = pass_orig and pass_flip
        if both_pass:
            passed += 1
            status = "✅"
        else:
            failed += 1
            status = "❌"

        if res_orig["confidence"] < DIRECTION_CONFIG["min_confidence"]:
            low_conf += 1
        if res_flip["confidence"] < DIRECTION_CONFIG["min_confidence"]:
            low_conf += 1

        name = f"{brand}/{model}"
        results.append({
            "name": name,
            "orig_dir": res_orig["direction"],
            "orig_conf": res_orig["confidence"],
            "orig_wheel": res_orig.get("wheel_source", "?"),
            "flip_dir": res_flip["direction"],
            "flip_conf": res_flip["confidence"],
            "flip_wheel": res_flip.get("wheel_source", "?"),
            "pass": both_pass,
            "status": status,
        })

        conf_tag = ""
        if res_orig["confidence"] < 0.5 or res_flip["confidence"] < 0.5:
            conf_tag = " ⚠️低置信"

        print(f"  {status} {name:<30} "
              f"原图:{res_orig['direction']}({res_orig['confidence']:.0%},{res_orig.get('wheel_source','?')[:4]}) "
              f"翻转:{res_flip['direction']}({res_flip['confidence']:.0%},{res_flip.get('wheel_source','?')[:4]})"
              f"{conf_tag}")

    # 汇总
    total = len(results)
    print(f"\n{'='*80}")
    print(f"  测试结果: {passed}/{total} 车型通过 ({passed/total*100:.0f}%)")
    print(f"  失败: {failed}  低置信用例: {low_conf}/{total*2}")
    print(f"{'='*80}")

    if failed > 0:
        print(f"\n  ❌ 失败车型:")
        for r in results:
            if not r["pass"]:
                print(f"    {r['name']}: 原图={r['orig_dir']}({r['orig_conf']:.0%}) "
                      f"翻转={r['flip_dir']}({r['flip_conf']:.0%})")

    # 生成HTML报告
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>车头方向检测全量回归报告</title>
<style>
body{{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}}
h1{{text-align:center;color:#2ecc71}}
.sub{{text-align:center;color:#888;margin-bottom:20px}}
.summary{{background:#16213e;border-radius:10px;padding:15px;margin-bottom:20px;text-align:center;font-size:18px}}
.pass{{color:#2ecc71}} .fail{{color:#e74c3c}} .warn{{color:#f39c12}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:8px;text-align:left;border-bottom:1px solid #333}}
th{{background:#1a1a2e;color:#3498db}}
.pass-row{{background:#0a3a0a}} .fail-row{{background:#3a0a0a}}
</style></head><body>
<h1>车头方向检测全量回归报告</h1>
<div class="sub">19款车 × 2方向 = {total*2}用例 | 准确率 {passed}/{total} ({passed/total*100:.0f}%)</div>
<div class="summary">
  <span class="{'pass' if failed==0 else 'fail'}">通过 {passed}/{total}</span> |
  <span class="fail">失败 {failed}</span> |
  <span class="warn">低置信 {low_conf}</span>
</div>
<table>
<tr><th>#</th><th>车型</th><th>原图方向</th><th>原图置信度</th><th>原图轮源</th><th>翻转方向</th><th>翻转置信度</th><th>翻转轮源</th><th>结果</th></tr>
"""
    for i, r in enumerate(results):
        row_class = "pass-row" if r["pass"] else "fail-row"
        status = "✅" if r["pass"] else "❌"
        html += f'<tr class="{row_class}"><td>{i+1}</td><td>{r["name"]}</td>'
        html += f'<td>{r["orig_dir"]}</td><td>{r["orig_conf"]:.0%}</td><td>{r["orig_wheel"]}</td>'
        html += f'<td>{r["flip_dir"]}</td><td>{r["flip_conf"]:.0%}</td><td>{r["flip_wheel"]}</td>'
        html += f'<td>{status}</td></tr>\n'
    html += "</table></body></html>"

    out = ROOT / "public" / "_test_direction_full_report.html"
    out.write_text(html, encoding="utf-8")
    print(f"\n  HTML报告: http://localhost:5173/_test_direction_full_report.html")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
