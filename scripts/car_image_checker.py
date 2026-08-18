"""
车型图片快速检测命令行工具
==========================
直接传入图片文件或文件夹路径，自动运行纯白背景过滤 + 完整车身检测

用法：
    # 单张图片
    python car_image_checker.py photo.jpg

    # 多个图片
    python car_image_checker.py 1.jpg 2.jpg 3.jpg

    # 整个文件夹
    python car_image_checker.py D:\my_images

    # 递归扫描子文件夹
    python car_image_checker.py D:\my_images --recursive

    # 检测并保存通过的图片到指定目录
    python car_image_checker.py D:\my_images --output D:\passed_images

    # 生成HTML报告
    python car_image_checker.py D:\my_images --report report.html
"""
import argparse, sys, shutil
from pathlib import Path
from PIL import Image
import numpy as np

# 复用核心逻辑
from car_image_filter_pipeline import (
    analyze_background, detect_complete_car,
    WHITE_BG_CONFIG, COMPLETE_CAR_CONFIG
)

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def collect_images(paths, recursive=False):
    """从路径列表收集图片文件"""
    images = []
    seen = set()
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"⚠️  路径不存在: {p}")
            continue
        if path.is_file():
            if path.suffix.lower() in SUPPORTED_EXTS:
                if str(path) not in seen:
                    seen.add(str(path))
                    images.append(path)
        elif path.is_dir():
            pattern = "**/*" if recursive else "*"
            for f in sorted(path.glob(pattern)):
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
                    if str(f) not in seen:
                        seen.add(str(f))
                        images.append(f)
    return images


def check_single_image(img_path):
    """检测单张图片，返回结果字典"""
    with Image.open(img_path) as im:
        arr = np.array(im.convert("RGB"))
        w, h = im.size

    bg_result = analyze_background(arr, WHITE_BG_CONFIG)
    bg_pass = bg_result["pass"]

    if bg_pass:
        car_result = detect_complete_car(arr, COMPLETE_CAR_CONFIG)
        car_pass = car_result["pass"]
    else:
        car_result = {"pass": False, "reasons": ["背景未通过，跳过车身检测"]}
        car_pass = False

    overall = bg_pass and car_pass

    return {
        "file": img_path.name,
        "path": str(img_path),
        "size": f"{w}x{h}",
        "bg_pass": bg_pass,
        "bg_reasons": bg_result.get("reasons", []),
        "bg_white_ratio": bg_result.get("white_ratio", 0),
        "bg_corner_std": bg_result.get("corner_std", 0),
        "bg_corner_diff": bg_result.get("corner_brightness_diff", 0),
        "bg_brightness": bg_result.get("brightness", 0),
        "car_pass": car_pass,
        "car_reasons": car_result.get("reasons", []),
        "car_width_ratio": car_result.get("width_ratio", 0),
        "car_height_ratio": car_result.get("height_ratio", 0),
        "overall": overall,
    }


def print_results(results):
    """打印检测结果"""
    passed = [r for r in results if r["overall"]]
    failed = [r for r in results if not r["overall"]]

    print(f"\n{'='*100}")
    print(f"  检测结果: {len(passed)} 通过 / {len(failed)} 不通过 / 共 {len(results)} 张")
    print(f"{'='*100}\n")

    # 通过的图片
    if passed:
        print(f"✅ 通过 {len(passed)} 张:")
        print(f"{'文件':<40} {'尺寸':<12} {'白色占比':<10} {'车宽占比':<10} {'车高占比':<10}")
        print(f"{'-'*82}")
        for r in passed:
            print(f"  {r['file']:<38} {r['size']:<12} {r['bg_white_ratio']:>7.1f}%   {r['car_width_ratio']:>7.1f}%   {r['car_height_ratio']:>7.1f}%")
        print()

    # 不通过的图片
    if failed:
        print(f"❌ 不通过 {len(failed)} 张:")
        for r in failed:
            issues = []
            if not r["bg_pass"]:
                issues.append(f"背景({', '.join(r['bg_reasons'])})")
            if not r["car_pass"]:
                issues.append(f"车身({', '.join(r['car_reasons'])})")
            print(f"  {r['file']:<38} {r['size']:<12} → {'; '.join(issues)}")
        print()

    return passed, failed


def save_passed(results, output_dir):
    """保存通过的图片到输出目录"""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    passed = [r for r in results if r["overall"]]
    if not passed:
        print("没有通过的图片需要保存")
        return

    for r in passed:
        src = Path(r["path"])
        dst = out_path / src.name
        shutil.copy2(src, dst)
        print(f"  已复制: {src.name} → {dst}")

    print(f"\n共保存 {len(passed)} 张到 {out_path}")


def generate_report(results, report_path):
    """生成HTML可视化报告"""
    passed = [r for r in results if r["overall"]]
    failed = [r for r in results if not r["overall"]]

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>车型图片检测报告</title>
<style>
body{{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}}
h1{{text-align:center;margin-bottom:5px}}
.summary{{text-align:center;margin-bottom:20px;font-size:18px}}
.pass{{color:#2ecc71}}.fail{{color:#e94560}}
.section{{background:#16213e;border-radius:10px;padding:15px;margin-bottom:20px}}
.section h2{{margin-top:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.card{{background:#000;border-radius:8px;overflow:hidden;border:2px solid #333}}
.card.pass{{border-color:#2ecc71}}.card.fail{{border-color:#e94560}}
.card img{{width:100%;height:180px;object-fit:contain;display:block;background:#fff}}
.info{{padding:10px;font-size:12px}}
.info .name{{font-weight:bold;margin-bottom:5px;word-break:break-all}}
.info .metric{{color:#3498db;font-size:11px;margin:2px 0}}
.info .reasons{{color:#e94560;font-size:11px;margin:2px 0}}
</style></head><body>
<h1>🚗 车型图片检测报告</h1>
<div class="summary">通过 <span class="pass">{len(passed)}</span> / 不通过 <span class="fail">{len(failed)}</span> / 共 {len(results)} 张</div>
"""

    if passed:
        html += f'<div class="section"><h2>✅ 通过 ({len(passed)} 张)</h2><div class="grid">'
        for r in passed:
            safe_path = r['path'].replace('\\', '/')
            html += f'''<div class="card pass">
<img src="file:///{safe_path}" onerror="this.style.background='#333';this.src=''">
<div class="info">
<div class="name">{r['file']}</div>
<div class="metric">📐 {r['size']}</div>
<div class="metric">⚪ 白色占比: {r['bg_white_ratio']:.1f}%</div>
<div class="metric">🚗 车宽占比: {r['car_width_ratio']:.1f}% | 车高占比: {r['car_height_ratio']:.1f}%</div>
</div></div>'''
        html += "</div></div>"

    if failed:
        html += f'<div class="section"><h2>❌ 不通过 ({len(failed)} 张)</h2><div class="grid">'
        for r in failed:
            issues = ""
            if not r["bg_pass"]:
                issues += f'<div class="reasons">背景: {", ".join(r["bg_reasons"])}</div>'
            if not r["car_pass"]:
                issues += f'<div class="reasons">车身: {", ".join(r["car_reasons"])}</div>'
            safe_path = r['path'].replace('\\', '/')
            html += f'''<div class="card fail">
<img src="file:///{safe_path}" onerror="this.style.background='#333';this.src=''">
<div class="info">
<div class="name">{r['file']}</div>
<div class="metric">📐 {r['size']}</div>
{issues}
</div></div>'''
        html += "</div></div>"

    html += "</body></html>"

    out = Path(report_path)
    out.write_text(html, encoding="utf-8")
    print(f"📄 报告已生成: {out.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="车型图片快速检测工具 - 纯白背景 + 完整车身",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python car_image_checker.py photo.jpg
  python car_image_checker.py D:\\images
  python car_image_checker.py D:\\images --output D:\\passed --report report.html
  python car_image_checker.py D:\\images --recursive
        """)
    parser.add_argument("paths", nargs="+", help="图片文件或文件夹路径（支持多个）")
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="递归扫描子文件夹")
    parser.add_argument("--output", "-o", default=None,
                        help="将通过的图片复制到此目录")
    parser.add_argument("--report", default=None,
                        help="生成HTML可视化报告（指定文件路径）")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="显示详细检测指标")
    args = parser.parse_args()

    # 收集图片
    images = collect_images(args.paths, recursive=args.recursive)
    if not images:
        print("未找到任何支持的图片文件")
        sys.exit(1)

    print(f"🔍 发现 {len(images)} 张图片，开始检测...\n")

    # 检测
    results = []
    for i, img_path in enumerate(images, 1):
        try:
            r = check_single_image(img_path)
            results.append(r)
            status = "✅" if r["overall"] else "❌"
            if args.verbose:
                print(f"  [{i}/{len(images)}] {status} {r['file']} | 白{r['bg_white_ratio']:.1f}% 车宽{r['car_width_ratio']:.1f}%")
            else:
                print(f"  [{i}/{len(images)}] {status} {r['file']}")
        except Exception as e:
            print(f"  [{i}/{len(images)}] ⚠️  {img_path.name} - 错误: {e}")
            results.append({
                "file": img_path.name, "path": str(img_path),
                "size": "?", "bg_pass": False, "bg_reasons": [f"ERROR: {e}"],
                "bg_white_ratio": 0, "bg_corner_std": 0, "bg_corner_diff": 0,
                "bg_brightness": 0, "car_pass": False, "car_reasons": [],
                "car_width_ratio": 0, "car_height_ratio": 0, "overall": False,
            })

    # 输出结果
    passed, failed = print_results(results)

    # 保存通过的图片
    if args.output:
        save_passed(results, args.output)

    # 生成报告
    if args.report:
        generate_report(results, args.report)

    # 返回退出码
    if len(passed) == 0:
        sys.exit(1)
    elif len(failed) == 0:
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
