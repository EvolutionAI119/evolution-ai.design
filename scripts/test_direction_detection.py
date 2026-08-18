"""
车头方向自动检测算法 - 测试脚本
================================
测试目标：
1. 原图（车头向左）→ 应检测为 direction="left", flip_needed=False
2. 翻转图（车头向右）→ 应检测为 direction="right", flip_needed=True

测试数据：
- 4款已确认车头向左的品牌图
- 每张图的水平翻转版（车头向右）
- 共8张测试图
"""
import sys, os, io
from pathlib import Path
from PIL import Image
import numpy as np

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import detect_car_direction, DIRECTION_CONFIG

ROOT = Path(__file__).resolve().parent.parent

# 测试数据：4款已确认车头向左的品牌图
TEST_CARS = [
    {"brand": "bentley", "model": "bentayga", "expected": "left"},
    {"brand": "bentley", "model": "flying-spur", "expected": "left"},
    {"brand": "bentley", "model": "continental-gtc", "expected": "left"},
    {"brand": "rolls-royce", "model": "cullinan", "expected": "left"},
]


def test_direction_detection():
    """测试方向检测算法"""
    results = []
    test_idx = 0

    print("=" * 90)
    print("  车头方向自动检测算法测试")
    print("=" * 90)
    print()

    for car in TEST_CARS:
        brand, model = car["brand"], car["model"]
        img_path = ROOT / "public" / "brands" / brand / f"{model}.jpg"

        if not img_path.exists():
            print(f"  ⚠️ 跳过 {brand}/{model} - 图片不存在")
            continue

        with Image.open(img_path) as im:
            arr_orig = np.array(im.convert("RGB"))

        # 测试原图（车头向左）
        test_idx += 1
        result_orig = detect_car_direction(arr_orig, DIRECTION_CONFIG)
        pass_orig = result_orig["direction"] == car["expected"]
        results.append({
            "idx": test_idx,
            "name": f"{brand}/{model}",
            "version": "原图(应向左)",
            "result": result_orig,
            "expected": "left",
            "pass": pass_orig,
        })

        # 测试翻转版（车头向右）- 使用numpy水平翻转
        test_idx += 1
        arr_flip = arr_orig[:, ::-1, :].copy()
        result_flip = detect_car_direction(arr_flip, DIRECTION_CONFIG)
        pass_flip = result_flip["direction"] == "right" and result_flip["flip_needed"] == True
        results.append({
            "idx": test_idx,
            "name": f"{brand}/{model}",
            "version": "翻转(应向右)",
            "result": result_flip,
            "expected": "right",
            "pass": pass_flip,
        })

    # 打印结果
    print(f"{'#':<4} {'车型':<25} {'版本':<15} {'检测方向':<8} {'置信度':<8} {'需翻转':<6} {'轮源':<14} {'结果':<6}")
    print("-" * 95)

    passed = 0
    failed = 0
    for r in results:
        res = r["result"]
        status = "✅ PASS" if r["pass"] else "❌ FAIL"
        if r["pass"]:
            passed += 1
        else:
            failed += 1

        direction = res.get("direction", "?")
        confidence = f"{res.get('confidence', 0):.0%}"
        flip = "是" if res.get("flip_needed", False) else "否"
        wheel_src = res.get("wheel_source", "?")

        print(f"  {r['idx']:<3} {r['name']:<24} {r['version']:<14} "
              f"{direction:<7} {confidence:<7} {flip:<5} {wheel_src:<13} {status}")

    print()
    print(f"{'=' * 90}")
    print(f"  结果: {passed} 通过 / {failed} 不通过 / 共 {len(results)} 张测试")
    accuracy = passed / len(results) * 100 if results else 0
    print(f"  准确率: {accuracy:.0f}%")
    print(f"{'=' * 90}")

    # 打印详细特征分析
    print("\n详细特征分析:")
    print(f"{'#':<4} {'车型':<25} {'版本':<14} {'检测到轮':<8} {'左悬垂':<7} {'右悬垂':<7} {'上部L':<7} {'上部R':<7}")
    print("-" * 95)
    for r in results:
        res = r["result"]
        wd = "是" if res.get("wheel_detected", False) else "否"
        print(f"  {r['idx']:<3} {r['name']:<24} {r['version']:<13} "
              f"{wd:<7} {res.get('left_overhang', '?'):<6} {res.get('right_overhang', '?'):<6} "
              f"{res.get('left_upper_avg', '?'):<6} {res.get('right_upper_avg', '?'):<6}")

    # 生成HTML报告
    generate_html_report(results, passed, failed, accuracy)

    return passed == len(results)


def generate_html_report(results, passed, failed, accuracy):
    """生成HTML可视化报告"""
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>车头方向检测测试报告</title>
<style>
body{{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}}
h1{{text-align:center;margin-bottom:5px}}
.summary{{text-align:center;margin-bottom:20px;font-size:18px}}
.pass{{color:#2ecc71}}.fail{{color:#e94560}}
table{{width:100%;border-collapse:collapse;margin-bottom:20px}}
th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #333;font-size:13px}}
th{{background:#1a1a2e;color:#3498db}}
tr.pass-row{{background:rgba(46,204,113,0.1)}}
tr.fail-row{{background:rgba(233,69,96,0.1)}}
.detail{{background:#16213e;border-radius:10px;padding:15px;margin-bottom:20px}}
.detail h2{{margin-top:0;color:#3498db}}
</style></head><body>
<h1>🚗 车头方向自动检测算法 - 测试报告</h1>
<div class="summary">通过 <span class="pass">{passed}</span> / 不通过 <span class="fail">{failed}</span> / 共 {len(results)} 张 | 准确率 <span class="{'pass' if accuracy == 100 else 'fail'}">{accuracy:.0f}%</span></div>
<table>
<tr><th>#</th><th>车型</th><th>版本</th><th>检测方向</th><th>置信度</th><th>需翻转</th><th>轮源</th><th>需人工</th><th>结果</th></tr>
"""
    for r in results:
        res = r["result"]
        row_class = "pass-row" if r["pass"] else "fail-row"
        status = "✅ PASS" if r["pass"] else "❌ FAIL"
        manual = "⚠️ 是" if res.get("need_manual") else "否"
        html += f'<tr class="{row_class}"><td>{r["idx"]}</td><td>{r["name"]}</td><td>{r["version"]}</td>'
        html += f'<td>{res.get("direction", "?")}</td><td>{res.get("confidence", 0):.0%}</td>'
        html += f'<td>{"是" if res.get("flip_needed") else "否"}</td>'
        html += f'<td>{res.get("wheel_source", "?")}</td><td>{manual}</td><td>{status}</td></tr>\n'

    html += """</table>
<div class="detail">
<h2>算法原理 v2</h2>
<p><b>核心原理</b>：前轮悬垂 &lt; 后轮悬垂（前轮更靠近车头边缘）。</p>
<p>通过多层特征融合+可靠性检查判定车头方向，适用所有车型（含深色车、敞篷车）。</p>
<h2>四层特征融合</h2>
<ul>
<li><b>特征1（权重3，主）</b>：底部轮廓车轮检测 — 车轮是车身最低点（触地），与车身颜色无关。通过底部轮廓的低点区域定位车轮。</li>
<li><b>特征2（权重1，辅）</b>：自适应亮度车轮检测 — 车轮是底部最暗区域，用自适应阈值（相对中值30%）检测。</li>
<li><b>特征3（权重1，辅）</b>：上轮廓非对称性 — 引擎盖低于行李箱/C柱（车尾更高）。</li>
<li><b>特征4（权重1，备用）</b>：亮度梯度 — 车头通常更亮（引擎盖反射、前格栅），亮度重心偏向车头侧。适用深色/无特征车。</li>
</ul>
<h2>可靠性检查</h2>
<ul>
<li>底部轮廓平坦（range &lt; 车高5%）→ 轮廓检测不可靠</li>
<li>车轮过宽（&gt; 车宽20%）→ 误检（合并了车身）</li>
<li>车轮间距过小（&lt; 车宽20%）→ 误检</li>
<li>不可靠时自动降级到亮度梯度，置信度上限0.4（标记需人工确认）</li>
</ul>
</div>
</body></html>"""

    out_path = ROOT / "public" / "_test_direction_report.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"\n📄 HTML报告: http://localhost:5173/_test_direction_report.html")


if __name__ == "__main__":
    success = test_direction_detection()
    sys.exit(0 if success else 1)
