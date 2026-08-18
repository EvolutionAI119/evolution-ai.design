"""
构造测试图片集，验证过滤逻辑准确性
生成不同背景类型（纯白/灰色/复杂）+ 不同车身状态的测试图片
运行过滤逻辑，对比预期结果与实际结果
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from car_image_filter_pipeline import analyze_background, detect_complete_car, WHITE_BG_CONFIG, COMPLETE_CAR_CONFIG

ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = ROOT / "public" / "_test_filter_images"
TEST_DIR.mkdir(parents=True, exist_ok=True)

# 清空旧测试图
import shutil
for f in TEST_DIR.glob("*.png"):
    f.unlink()
for f in TEST_DIR.glob("*.jpg"):
    f.unlink()


def draw_car(draw, x1, y1, x2, y2, color=(50, 50, 50)):
    """画一辆简化的车（矩形车身+梯形车顶+圆形车轮）"""
    draw.rectangle([x1, y1, x2, y2], fill=color)
    roof_h = (y2 - y1) * 0.3
    roof_y = y1 - roof_h
    margin = (x2 - x1) * 0.15
    draw.polygon([
        (x1 + margin, y1),
        (x1 + margin * 2, roof_y),
        (x2 - margin * 2, roof_y),
        (x2 - margin, y1),
    ], fill=color)
    wheel_r = (y2 - y1) * 0.15
    draw.ellipse([x1 + (x2-x1)*0.15 - wheel_r, y2 - wheel_r,
                  x1 + (x2-x1)*0.15 + wheel_r, y2 + wheel_r], fill=(20, 20, 20))
    draw.ellipse([x2 - (x2-x1)*0.15 - wheel_r, y2 - wheel_r,
                  x2 - (x2-x1)*0.15 + wheel_r, y2 + wheel_r], fill=(20, 20, 20))


def create_test_image(name, w, h, bg_type, car_config=None):
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    if bg_type == "white":
        draw.rectangle([0, 0, w, h], fill=(255, 255, 255))
    elif bg_type == "gray":
        draw.rectangle([0, 0, w, h], fill=(180, 180, 180))
    elif bg_type == "dark":
        draw.rectangle([0, 0, w, h], fill=(30, 30, 30))
    elif bg_type == "complex":
        for i in range(h):
            r, g, b = int(255 - i/h*100), int(150 + i/h*50), int(200 - i/h*80)
            draw.line([(0, i), (w, i)], fill=(r, g, b))
        draw.rectangle([0, 0, w//3, h//2], fill=(100, 150, 200))
        draw.rectangle([w*2//3, h//2, w, h], fill=(200, 100, 150))
    elif bg_type == "shadow":
        draw.rectangle([0, 0, w, h], fill=(255, 255, 255))
        draw.rectangle([0, 0, w//4, h//4], fill=(200, 200, 200))
    elif bg_type == "gradient":
        for i in range(w):
            gray = int(255 - i / w * 30)
            draw.line([(i, 0), (i, h)], fill=(gray, gray, gray))
    if car_config:
        draw_car(draw, *car_config)
    img.save(TEST_DIR / name)
    return img


# ==================== 构造10张测试图 ====================
print("=== 构造测试图片集 ===\n")
test_cases = []

# 纯白背景类
create_test_image("01_white_complete.png", 1200, 800, "white", car_config=(100, 350, 1100, 550))
test_cases.append({"file": "01_white_complete.png", "expect_bg": True, "expect_car": True, "desc": "纯白背景 + 完整车身（应全通过）"})

create_test_image("02_white_narrow.png", 1200, 800, "white", car_config=(500, 350, 700, 550))
test_cases.append({"file": "02_white_narrow.png", "expect_bg": True, "expect_car": False, "desc": "纯白背景 + 车辆太窄（背景通过，车身不通过）"})

create_test_image("03_white_no_margin.png", 1200, 800, "white", car_config=(0, 350, 1200, 550))
test_cases.append({"file": "03_white_no_margin.png", "expect_bg": True, "expect_car": False, "desc": "纯白背景 + 无留白（背景通过，车身不通过）"})

create_test_image("04_white_closeup.png", 1200, 800, "white", car_config=(100, 380, 1100, 420))
test_cases.append({"file": "04_white_closeup.png", "expect_bg": True, "expect_car": False, "desc": "纯白背景 + 局部特写（背景通过，车身不通过）"})

create_test_image("05_white_nocar.png", 1200, 800, "white", car_config=None)
test_cases.append({"file": "05_white_nocar.png", "expect_bg": True, "expect_car": False, "desc": "纯白背景 + 无车（背景通过，车身不通过）"})

# 灰色/暗色背景类
create_test_image("06_gray_complete.png", 1200, 800, "gray", car_config=(100, 350, 1100, 550))
test_cases.append({"file": "06_gray_complete.png", "expect_bg": False, "expect_car": None, "desc": "灰色背景 + 完整车身（背景不通过）"})

create_test_image("07_dark_complete.png", 1200, 800, "dark", car_config=(100, 350, 1100, 550))
test_cases.append({"file": "07_dark_complete.png", "expect_bg": False, "expect_car": None, "desc": "暗色背景 + 完整车身（背景不通过）"})

# 复杂背景类
create_test_image("08_complex_complete.png", 1200, 800, "complex", car_config=(100, 350, 1100, 550))
test_cases.append({"file": "08_complex_complete.png", "expect_bg": False, "expect_car": None, "desc": "复杂背景 + 完整车身（背景不通过）"})

# 边界情况
create_test_image("09_shadow.png", 1200, 800, "shadow", car_config=(100, 350, 1100, 550))
test_cases.append({"file": "09_shadow.png", "expect_bg": False, "expect_car": None, "desc": "白底+左上阴影（4角不一致，背景不通过）"})

create_test_image("10_gradient.png", 1200, 800, "gradient", car_config=(100, 350, 1100, 550))
test_cases.append({"file": "10_gradient.png", "expect_bg": False, "expect_car": None, "desc": "白到灰渐变（4角不一致，背景不通过）"})

print(f"已生成 {len(test_cases)} 张测试图片\n")

# ==================== 运行过滤逻辑 ====================
print("=== 运行过滤逻辑验证 ===\n")
results = []
pass_count = 0
fail_count = 0

for tc in test_cases:
    img_path = TEST_DIR / tc["file"]
    with Image.open(img_path) as im:
        arr = np.array(im.convert("RGB"))
    bg_result = analyze_background(arr, WHITE_BG_CONFIG)
    bg_pass = bg_result["pass"]
    if bg_pass:
        car_result = detect_complete_car(arr, COMPLETE_CAR_CONFIG)
        car_pass = car_result["pass"]
    else:
        car_result = {"reasons": ["背景未通过，跳过"]}
        car_pass = False
    bg_match = (bg_pass == tc["expect_bg"])
    car_match = (car_pass == tc["expect_car"]) if tc["expect_car"] is not None else True
    all_match = bg_match and car_match
    if all_match:
        pass_count += 1
        status = "PASS"
    else:
        fail_count += 1
        status = "FAIL"
    results.append({
        "file": tc["file"], "desc": tc["desc"], "status": status,
        "bg_pass": bg_pass, "bg_expect": tc["expect_bg"], "bg_match": bg_match,
        "bg_reasons": bg_result.get("reasons", []),
        "bg_white_ratio": bg_result.get("white_ratio", "?"),
        "bg_corner_std": bg_result.get("corner_std", "?"),
        "bg_corner_diff": bg_result.get("corner_brightness_diff", "?"),
        "bg_brightness": bg_result.get("brightness", "?"),
        "car_pass": car_pass if bg_pass else None, "car_expect": tc["expect_car"],
        "car_match": car_match, "car_reasons": car_result.get("reasons", []),
        "car_width_ratio": car_result.get("width_ratio", "?"),
    })

# ==================== 输出报告 ====================
print("=" * 120)
print(f"{'状态':<6} {'文件':<28} {'背景':<12} {'白%':<6} {'std':<6} {'diff':<6} {'亮度':<5} {'车身':<12} {'车占%':<6} 描述")
print("=" * 120)
for r in results:
    bg_str = f"{'通过' if r['bg_pass'] else '不通过'}({'OK' if r['bg_match'] else 'X'})"
    car_str = "N/A" if r["car_pass"] is None else f"{'通过' if r['car_pass'] else '不通过'}({'OK' if r['car_match'] else 'X'})"
    print(f"{r['status']:<6} {r['file']:<28} {bg_str:<12} {str(r['bg_white_ratio']):<6} {str(r['bg_corner_std']):<6} {str(r['bg_corner_diff']):<6} {str(r['bg_brightness']):<5} {car_str:<12} {str(r['car_width_ratio']):<6} {r['desc']}")
print("=" * 120)
print(f"\n总计: {pass_count} PASS / {fail_count} FAIL / {len(results)} 总数")
print(f"准确率: {pass_count/len(results)*100:.1f}%\n")

if fail_count > 0:
    print("=== 失败详情 ===\n")
    for r in results:
        if r["status"] == "FAIL":
            print(f"[{r['file']}] {r['desc']}")
            if not r["bg_match"]:
                print(f"  背景异常: 实际={'通过' if r['bg_pass'] else '不通过'}, 期望={'通过' if r['bg_expect'] else '不通过'}")
                print(f"  原因: {r['bg_reasons']}")
                print(f"  指标: 白色={r['bg_white_ratio']}%, 4角std={r['bg_corner_std']}, 亮度差={r['bg_corner_diff']}, 亮度={r['bg_brightness']}")
            if not r["car_match"] and r["car_pass"] is not None:
                print(f"  车身异常: 实际={'通过' if r['car_pass'] else '不通过'}, 期望={'通过' if r['car_expect'] else '不通过'}")
                print(f"  原因: {r['car_reasons']}")
            print()

# ==================== 生成可视化预览页 ====================
html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>过滤逻辑测试报告</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:monospace;margin:0;padding:20px}
h1{text-align:center;margin-bottom:20px}
table{width:100%;border-collapse:collapse;margin-bottom:20px}
th{background:#16213e;padding:10px;text-align:left;border:1px solid #333}
td{padding:8px;border:1px solid #333;vertical-align:top}
.pass{color:#2ecc71;font-weight:bold}
.fail{color:#e94560;font-weight:bold}
.img-cell img{width:200px;height:130px;object-fit:contain;background:#fff;display:block}
.reasons{color:#aaa;font-size:11px}
.metric{color:#3498db;font-size:11px}
</style></head><body>
<h1>过滤逻辑测试报告</h1>
<table>
<tr><th>状态</th><th>测试图</th><th>描述</th><th>背景过滤</th><th>背景指标</th><th>车身检测</th><th>车身指标</th></tr>
"""
for r in results:
    sc = "pass" if r["status"] == "PASS" else "fail"
    bc = "pass" if r["bg_match"] else "fail"
    cc = "pass" if r["car_match"] else "fail"
    bg_str = f"{'通过' if r['bg_pass'] else '不通过'} (期望{'通过' if r['bg_expect'] else '不通过'})"
    car_str = "N/A" if r["car_pass"] is None else f"{'通过' if r['car_pass'] else '不通过'} (期望{'通过' if r['car_expect'] else '不通过'})"
    bg_metrics = f"白色{r['bg_white_ratio']}% | std={r['bg_corner_std']} | diff={r['bg_corner_diff']} | 亮度{r['bg_brightness']}<br><span class='reasons'>{', '.join(r['bg_reasons'])}</span>"
    car_metrics = f"车占{r['car_width_ratio']}%<br><span class='reasons'>{', '.join(r['car_reasons'])}</span>"
    html += f"""<tr>
<td class="{sc}">{r['status']}</td>
<td class="img-cell"><img src="/_test_filter_images/{r['file']}"></td>
<td>{r['desc']}</td>
<td class="{bc}">{bg_str}</td>
<td class="metric">{bg_metrics}</td>
<td class="{cc}">{car_str}</td>
<td class="metric">{car_metrics}</td>
</tr>"""
html += f"""</table>
<h2 style="text-align:center">总计: <span class="pass">{pass_count} PASS</span> / <span class="fail">{fail_count} FAIL</span> / {len(results)} 总数 | 准确率: {pass_count/len(results)*100:.1f}%</h2>
</body></html>"""
out = ROOT / "public" / "_test_filter_report.html"
out.write_text(html, encoding="utf-8")
print(f"\n可视化报告: http://localhost:5173/_test_filter_report.html")
print(f"测试图片目录: {TEST_DIR}")
