"""
严格背景纯净度过滤器
对4款失败车的所有Bing候选图进行背景分析，只保留纯白背景的图片

过滤标准（全部必须满足）：
1. 4个角落颜色一致（标准差 < 15）
2. 4个角落颜色接近白色（RGB平均值 > 235）
3. 边缘条带颜色一致（标准差 < 20）
4. 白色背景像素占比 > 55%（说明背景占大部分面积）
5. 宽高比 1.3-2.5（正侧视典型比例）
6. 宽度 >= 800px
"""
import os, json, hashlib, io
from pathlib import Path
from PIL import Image
import numpy as np

ROOT = Path(r"d:\API\Evolution-Ai.Design")
SRC_DIR = ROOT / "public" / "_bing_v2_candidates"
OUT_DIR = ROOT / "public" / "_white_bg_candidates"
OUT_DIR.mkdir(exist_ok=True)

# 清空旧内容
import shutil
for f in OUT_DIR.glob("*"):
    if f.is_file(): f.unlink()
    elif f.is_dir(): shutil.rmtree(f)

CARS = [
    ("bentley", "bentayga", "Bentley Bentayga"),
    ("bentley", "flying-spur", "Bentley Flying Spur"),
    ("bentley", "continental-gtc", "Bentley Continental GTC"),
    ("rolls-royce", "cullinan", "Rolls-Royce Cullinan"),
]


def analyze_background(img_path):
    """
    严格分析图片背景纯净度
    返回: dict with pass/fail and details
    """
    try:
        with Image.open(img_path) as im:
            w, h = im.size
            rgb = im.convert("RGB")
            arr = np.array(rgb)  # shape: (h, w, 3)
            
            # 1. 4个角落分析（每角取15x15区域）
            corner_size = 15
            corners = {
                "top_left": arr[0:corner_size, 0:corner_size],
                "top_right": arr[0:corner_size, w-corner_size:w],
                "bottom_left": arr[h-corner_size:h, 0:corner_size],
                "bottom_right": arr[h-corner_size:h, w-corner_size:w],
            }
            
            # 4角的平均颜色
            corner_means = []
            for name, region in corners.items():
                mean_rgb = region.mean(axis=(0,1))
                corner_means.append(mean_rgb)
            
            corner_means = np.array(corner_means)  # shape: (4, 3)
            overall_mean = corner_means.mean(axis=0)  # 4角总平均RGB
            
            # 4角颜色差异（标准差）
            corner_std = corner_means.std(axis=0).mean()  # 4角之间的颜色差异
            
            # 2. 检查4角是否接近白色
            brightness = overall_mean.mean()  # 平均亮度
            is_white = brightness > 235 and all(c > 230 for c in overall_mean)
            
            # 3. 边缘条带分析（上下左右各取10px宽条带）
            edge_width = 10
            edges = {
                "top": arr[0:edge_width, :],
                "bottom": arr[h-edge_width:h, :],
                "left": arr[:, 0:edge_width],
                "right": arr[:, w-edge_width:w],
            }
            
            edge_means = []
            for name, region in edges.items():
                mean_rgb = region.mean(axis=(0,1))
                edge_means.append(mean_rgb)
            
            edge_means = np.array(edge_means)
            edge_std = edge_means.std(axis=0).mean()  # 4边之间的颜色差异
            
            # 4. 白色背景像素占比
            # 定义"接近白色"：RGB各分量都 > 230
            white_mask = np.all(arr > 230, axis=2)
            white_ratio = white_mask.sum() / (w * h)
            
            # 5. 宽高比
            asp = w / h if h else 0
            
            # 判定
            reasons = []
            pass_all = True
            
            if corner_std > 15:
                reasons.append(f"4角颜色差异大(std={corner_std:.1f}>15)")
                pass_all = False
            
            if not is_white:
                reasons.append(f"4角非白色(亮度={brightness:.0f}<235)")
                pass_all = False
            
            if edge_std > 20:
                reasons.append(f"边缘颜色差异大(std={edge_std:.1f}>20)")
                pass_all = False
            
            if white_ratio < 0.55:
                reasons.append(f"白色占比低({white_ratio*100:.0f}%<55%)")
                pass_all = False
            
            if asp < 1.3 or asp > 2.5:
                reasons.append(f"宽高比异常(asp={asp:.2f})")
                pass_all = False
            
            if w < 800:
                reasons.append(f"宽度不足(w={w}<800)")
                pass_all = False
            
            return {
                "pass": pass_all,
                "w": w, "h": h, "asp": round(asp, 2),
                "corner_std": round(float(corner_std), 1),
                "edge_std": round(float(edge_std), 1),
                "brightness": round(float(brightness), 0),
                "white_ratio": round(float(white_ratio * 100), 1),
                "is_white": bool(is_white),
                "reasons": reasons if not pass_all else ["ALL PASS"],
                "size_kb": round(img_path.stat().st_size / 1024),
            }
    except Exception as e:
        return {"pass": False, "error": str(e), "reasons": [f"ERROR: {e}"]}


def main():
    results = {}
    
    for brand, model, name in CARS:
        car_dir = SRC_DIR / f"{brand}__{model}"
        if not car_dir.exists():
            continue
        
        out_car_dir = OUT_DIR / f"{brand}__{model}"
        out_car_dir.mkdir(exist_ok=True)
        
        passed = []
        failed_count = 0
        
        # 扫描所有图片
        imgs = sorted(list(car_dir.glob("*.jpg")) + list(car_dir.glob("*.png")))
        
        for img_path in imgs:
            info = analyze_background(img_path)
            if info.get("pass"):
                # 复制到输出目录
                dst = out_car_dir / img_path.name
                dst.write_bytes(img_path.read_bytes())
                info["file"] = img_path.name
                passed.append(info)
            else:
                failed_count += 1
        
        # 按白色占比排序（越高越好），其次按尺寸
        passed.sort(key=lambda x: (-x["white_ratio"], -x["w"]))
        
        results[name] = {
            "total": len(imgs),
            "passed": len(passed),
            "failed": failed_count,
            "candidates": passed,
        }
        print(f"{name}: {len(imgs)}张 → 通过{len(passed)}张")
        for p in passed[:5]:
            print(f"  ★ {p['file']} {p['w']}x{p['h']} asp={p['asp']} 白色{p['white_ratio']}% 4角std={p['corner_std']} 亮度{p['brightness']}")
    
    # 保存日志
    log = OUT_DIR / "_white_bg_log.json"
    log.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    
    # 生成预览页
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>纯白背景候选图</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:10px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-section{background:#16213e;border:2px solid #2ecc71;border-radius:10px;padding:15px;margin-bottom:20px}
.car-title{color:#2ecc71;font-weight:bold;font-size:18px;margin-bottom:10px}
.cand-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.cand-card{background:#000;border-radius:6px;overflow:hidden;cursor:pointer;border:1px solid #333}
.cand-card img{width:100%;height:170px;object-fit:contain;display:block;background:#fff}
.cand-label{padding:5px;font-size:10px;color:#aaa;text-align:center}
</style></head><body>
<h1>纯白背景候选图（代码过滤）</h1>
<div class="sub">过滤标准：4角白色+边缘一致+白色占比>55%+宽高比1.3-2.5+宽度≥800px</div>
"""
    for car_name, data in results.items():
        car_folder = ""
        for b, m, n in CARS:
            if n == car_name:
                car_folder = f"{b}__{m}"
                break
        
        html += f'<div class="car-section">\n'
        html += f'  <div class="car-title">{car_name} ({data["passed"]}/{data["total"]}张通过)</div>\n'
        html += f'  <div class="cand-grid">\n'
        for c in data["candidates"]:
            src_url = f"/_white_bg_candidates/{car_folder}/{c['file']}"
            html += f'    <div class="cand-card">\n'
            html += f'      <img src="{src_url}" loading="lazy" onclick="window.open(this.src)" onerror="this.style.display=\'none\'">\n'
            html += f'      <div class="cand-label">{c["w"]}x{c["h"]} asp={c["asp"]} 白{c["white_ratio"]}% 4角std={c["corner_std"]} {c["size_kb"]}KB</div>\n'
            html += f'    </div>\n'
        html += f'  </div>\n</div>\n'
    
    html += "</body></html>"
    out = ROOT / "public" / "_preview_white_bg.html"
    out.write_text(html, encoding="utf-8")
    
    total_passed = sum(d["passed"] for d in results.values())
    total_total = sum(d["total"] for d in results.values())
    print(f"\n=== 完成 ===")
    print(f"总计: {total_passed}/{total_total} 张通过纯白背景过滤")
    print(f"预览页: http://localhost:5173/_preview_white_bg.html")


if __name__ == "__main__":
    main()
