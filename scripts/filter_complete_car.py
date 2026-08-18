"""
纯白背景 + 完整车身过滤器
在已通过纯白背景过滤的13张图中，进一步检测：
1. 车辆是否完整显示（左右有留白，车身占宽度50-95%）
2. 车辆是否占据图片中央区域
3. 生成水平翻转版，用于后续车头方向判定

整车检测逻辑：
- 二值化：白色=0，非白=1
- 找非白色区域的边界框
- 检查边界框宽度占图片宽度的50-95%
- 检查边界框左右有白色留白（车身完整）
- 检查边界框上下有白色留白
"""
import os, json, hashlib, io
from pathlib import Path
from PIL import Image
import numpy as np

ROOT = Path(r"d:\API\Evolution-Ai.Design")
SRC_DIR = ROOT / "public" / "_white_bg_candidates"
OUT_DIR = ROOT / "public" / "_complete_car_candidates"
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


def detect_complete_car(img_path):
    """
    检测图片中是否包含完整车身
    返回: dict with pass/fail and bbox info
    """
    try:
        with Image.open(img_path) as im:
            w, h = im.size
            rgb = im.convert("RGB")
            arr = np.array(rgb)
            
            # 二值化：白色背景=0，非白色=1
            # 白色定义：RGB各分量都 > 230
            non_white_mask = ~np.all(arr > 230, axis=2)  # True = 非白色（车辆）
            
            # 找非白色区域的边界框
            rows = np.any(non_white_mask, axis=1)
            cols = np.any(non_white_mask, axis=0)
            
            if not rows.any() or not cols.any():
                return {"pass": False, "reason": "未检测到非白色区域"}
            
            rmin, rmax = np.where(rows)[0][[0, -1]]
            cmin, cmax = np.where(cols)[0][[0, -1]]
            
            car_w = cmax - cmin + 1
            car_h = rmax - rmin + 1
            
            # 车辆宽度占图片宽度的比例
            width_ratio = car_w / w
            # 车辆高度占图片高度的比例
            height_ratio = car_h / h
            
            # 左右留白
            left_margin = cmin
            right_margin = w - cmax - 1
            # 上下留白
            top_margin = rmin
            bottom_margin = h - rmax - 1
            
            # 宽高比
            asp = w / h if h else 0
            
            # 判定
            reasons = []
            pass_all = True
            
            # 1. 车辆宽度占比 50-95%
            if width_ratio < 0.50:
                reasons.append(f"车辆太窄(占{width_ratio*100:.0f}%<50%)")
                pass_all = False
            elif width_ratio > 0.98:
                reasons.append(f"车辆占满宽度(占{width_ratio*100:.0f}%)，可能不完整")
                pass_all = False
            
            # 2. 左右都有留白（车身完整）
            if left_margin < 5:
                reasons.append(f"左侧无留白({left_margin}px)，车头可能被裁切")
                pass_all = False
            if right_margin < 5:
                reasons.append(f"右侧无留白({right_margin}px)，车尾可能被裁切")
                pass_all = False
            
            # 3. 上下都有留白
            if top_margin < 3:
                reasons.append(f"上方无留白({top_margin}px)，车顶可能被裁切")
                pass_all = False
            if bottom_margin < 3:
                reasons.append(f"下方无留白({bottom_margin}px)，底盘可能被裁切")
                pass_all = False
            
            # 4. 车辆高度占比 30-85%（避免局部特写）
            if height_ratio < 0.30:
                reasons.append(f"车辆太矮(占{height_ratio*100:.0f}%<30%)，可能是局部特写")
                pass_all = False
            elif height_ratio > 0.90:
                reasons.append(f"车辆占满高度(占{height_ratio*100:.0f}%)")
                pass_all = False
            
            # 5. 宽高比检查（正侧视典型1.3-2.5）
            if asp < 1.3 or asp > 2.5:
                reasons.append(f"宽高比异常(asp={asp:.2f})")
                pass_all = False
            
            return {
                "pass": pass_all,
                "w": w, "h": h, "asp": round(asp, 2),
                "car_w": int(car_w), "car_h": int(car_h),
                "width_ratio": round(float(width_ratio * 100), 1),
                "height_ratio": round(float(height_ratio * 100), 1),
                "left_margin": int(left_margin),
                "right_margin": int(right_margin),
                "top_margin": int(top_margin),
                "bottom_margin": int(bottom_margin),
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
        
        imgs = sorted(list(car_dir.glob("*.jpg")) + list(car_dir.glob("*.png")))
        
        for img_path in imgs:
            info = detect_complete_car(img_path)
            if info.get("pass"):
                # 复制原图
                dst = out_car_dir / f"orig_{img_path.name}"
                dst.write_bytes(img_path.read_bytes())
                info["file"] = img_path.name
                info["orig_file"] = f"orig_{img_path.name}"
                
                # 生成水平翻转版
                with Image.open(img_path) as im:
                    flipped = im.transpose(Image.FLIP_LEFT_RIGHT)
                    flipped_path = out_car_dir / f"flip_{img_path.name}"
                    if img_path.suffix.lower() == ".png":
                        flipped.save(flipped_path, "PNG")
                    else:
                        flipped.save(flipped_path, "JPEG", quality=95)
                    info["flip_file"] = f"flip_{img_path.name}"
                
                passed.append(info)
        
        results[name] = {
            "total": len(imgs),
            "passed": len(passed),
            "candidates": passed,
        }
        print(f"{name}: {len(imgs)}张 → 通过{len(passed)}张")
        for p in passed:
            print(f"  ★ {p['file']} {p['w']}x{p['h']} 车占{p['width_ratio']}%x{p['height_ratio']}% 留白L{p['left_margin']}R{p['right_margin']}T{p['top_margin']}B{p['bottom_margin']}")
    
    # 保存日志
    log = OUT_DIR / "_complete_car_log.json"
    log.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    
    # 生成对比预览页：每张图显示原图和翻转版
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>完整车身+车头方向判定</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:10px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-section{background:#16213e;border:2px solid #2ecc71;border-radius:10px;padding:15px;margin-bottom:20px}
.car-title{color:#2ecc71;font-weight:bold;font-size:18px;margin-bottom:10px}
.pair-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:15px;border:1px solid #444;padding:10px;border-radius:6px}
.pair-label{color:#3498db;font-size:12px;margin-bottom:5px}
.cand-card{background:#000;border-radius:6px;overflow:hidden;cursor:pointer;border:1px solid #333}
.cand-card img{width:100%;height:160px;object-fit:contain;display:block;background:#fff}
.cand-label{padding:5px;font-size:10px;color:#aaa;text-align:center}
.dir-btn{padding:5px 15px;border:none;border-radius:4px;cursor:pointer;font-size:12px;margin:5px}
.dir-btn.left{background:#2ecc71;color:#000}
.dir-btn.right{background:#e94560}
</style></head><body>
<h1>完整车身 + 车头方向判定</h1>
<div class="sub">每张图显示原图和水平翻转版，选择"车头向左"的版本</div>
"""
    for car_name, data in results.items():
        car_folder = ""
        for b, m, n in CARS:
            if n == car_name:
                car_folder = f"{b}__{m}"
                break
        
        html += f'<div class="car-section">\n'
        html += f'  <div class="car-title">{car_name} ({data["passed"]}张通过)</div>\n'
        for i, c in enumerate(data["candidates"]):
            orig_url = f"/_complete_car_candidates/{car_folder}/{c['orig_file']}"
            flip_url = f"/_complete_car_candidates/{car_folder}/{c['flip_file']}"
            html += f'  <div class="pair-grid">\n'
            html += f'    <div class="pair-label">候选{i+1}: {c["file"]} (车占{c["width_ratio"]}%x{c["height_ratio"]}%)</div>\n'
            html += f'    <div class="cand-card">\n'
            html += f'      <div class="cand-label">原图 (左图)</div>\n'
            html += f'      <img src="{orig_url}" loading="lazy" onclick="window.open(this.src)">\n'
            html += f'    </div>\n'
            html += f'    <div class="cand-card">\n'
            html += f'      <div class="cand-label">翻转版 (右图)</div>\n'
            html += f'      <img src="{flip_url}" loading="lazy" onclick="window.open(this.src)">\n'
            html += f'    </div>\n'
            html += f'  </div>\n'
        html += f'</div>\n'
    
    html += "</body></html>"
    out = ROOT / "public" / "_preview_complete_car.html"
    out.write_text(html, encoding="utf-8")
    
    total_passed = sum(d["passed"] for d in results.values())
    print(f"\n=== 完成 ===")
    print(f"总计: {total_passed} 张通过完整车身检测")
    print(f"预览页: http://localhost:5173/_preview_complete_car.html")


if __name__ == "__main__":
    main()
