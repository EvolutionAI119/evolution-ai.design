# -*- coding: utf-8 -*-
""" analyze_roma_bg.py
专门分析 Ferrari Roma 图片的背景纯净度，输出详细指标
"""
import hashlib, io
from pathlib import Path
from PIL import Image as P

IMG_PATH = Path(__file__).resolve().parent.parent / "public" / "brands" / "ferrari" / "roma.jpg"

raw = IMG_PATH.read_bytes()
md5 = hashlib.md5(raw).hexdigest()[:12]

with P.open(io.BytesIO(raw)) as im:
    w, h = im.size
    # 缩小到 200x150 分析
    im_small = im.convert("RGB").resize((200, 150))
    pixels = list(im_small.getdata())

W, H = 200, 150

# 1. 基础尺寸
print(f"文件: {IMG_PATH.name}")
print(f"尺寸: {w}x{h}  大小: {len(raw)/1024:.0f}KB  md5={md5}")

# 2. 4角 + 4边 共 8 个背景采样点坐标
corner_pts = [
    (0, 0), (W-1, 0), (0, H-1), (W-1, H-1),
    (W//2, 0), (W//2, H-1), (0, H//2), (W-1, H//2),
]
corner_colors = [pixels[y*W + x] for x, y in corner_pts]

# 计算颜色差异
r_vals = [c[0] for c in corner_colors]
g_vals = [c[1] for c in corner_colors]
b_vals = [c[2] for c in corner_colors]
r_diff = max(r_vals) - min(r_vals)
g_diff = max(g_vals) - min(g_vals)
b_diff = max(b_vals) - min(b_vals)
max_diff = max(r_diff, g_diff, b_diff)

# 边缘平均色
edge_r = sum(r_vals) / len(r_vals)
edge_g = sum(g_vals) / len(g_vals)
edge_b = sum(b_vals) / len(b_vals)

print(f"\n== 背景采样 (8个边缘点) ==")
names = ["左上", "右上", "左下", "右下", "上中", "下中", "左中", "右中"]
for n, c in zip(names, corner_colors):
    print(f"  {n}: RGB({c[0]},{c[1]},{c[2]})")
print(f"\n  边缘最大色差: R={r_diff}  G={g_diff}  B={b_diff}  Max={max_diff}")
print(f"  边缘平均色: RGB({edge_r:.0f},{edge_g:.0f},{edge_b:.0f})")

# 3. 天空/草地占比（检测户外）
sky = sum(1 for r,g,b in pixels if b > 150 and b > r + 30 and b > g + 10)
grass = sum(1 for r,g,b in pixels if g > 100 and g > r + 20 and g > b + 10)
total = W * H
sky_ratio = sky / total * 100
grass_ratio = grass / total * 100
print(f"\n  天空像素: {sky_ratio:.1f}%  草地像素: {grass_ratio:.1f}%")

# 4. 亮度分布
brightness = sum((r+g+b)/3 for r,g,b in pixels) / total
dark = sum(1 for r,g,b in pixels if (r+g+b)/3 < 50) / total * 100
light = sum(1 for r,g,b in pixels if (r+g+b)/3 > 220) / total * 100
print(f"  平均亮度: {brightness:.0f}  暗像素: {dark:.1f}%  亮像素: {light:.1f}%")

# 5. 背景类型判断
print(f"\n== 背景纯净度评估 ==")
if sky_ratio > 15 or grass_ratio > 10:
    cat = "户外背景 ❌ 不达标"
    reason = f"天空{sky_ratio:.1f}% + 草地{grass_ratio:.1f}% > 阈值(天空15%/草地10%)"
elif max_diff < 20:
    cat = "★★★★★ 纯净背景"
    reason = f"8点最大色差 {max_diff} < 20，完全纯色背景"
elif max_diff < 35:
    cat = "★★★★ 接近纯净背景"
    reason = f"8点最大色差 {max_diff} < 35，轻微渐变背景"
elif max_diff < 60:
    cat = "★★★ 可接受背景"
    reason = f"8点最大色差 {max_diff} < 60，存在可感知的背景变化"
else:
    cat = "★★ 复杂背景 ⚠ 不够纯净"
    reason = f"8点最大色差 {max_diff} >= 60，背景层次较多"

print(f"  评级: {cat}")
print(f"  依据: {reason}")

# 6. 与合格车型对比（拿 SF90 作为影棚基准）
sf90_path = IMG_PATH.parent.parent / "ferrari" / "sf90.jpg"
if sf90_path.exists():
    with P.open(io.BytesIO(sf90_path.read_bytes())) as sf:
        sf_small = sf.convert("RGB").resize((200, 150))
        sf_pixels = list(sf_small.getdata())
    sf_corners = [sf_pixels[y*W + x] for x, y in corner_pts]
    sf_max_diff = max(
        max(c[i] for c in sf_corners) - min(c[i] for c in sf_corners)
        for i in range(3)
    )
    sf_dark = sum(1 for r,g,b in sf_pixels if (r+g+b)/3 < 50) / total * 100
    print(f"\n  [对比] SF90(影棚基准): 8点色差={sf_max_diff} 暗像素={sf_dark:.0f}%")
    print(f"  [对比] Roma:          8点色差={max_diff} 暗像素={dark:.0f}% 亮像素={light:.0f}%")
    if max_diff > sf_max_diff * 2:
        print(f"  ⚠ Roma的背景色差是SF90的 {max_diff/sf_max_diff:.1f}x，明显不如影棚纯净")

print(f"\n== 结论 ==")
if max_diff < 35:
    print("  ✓ 背景足够纯净，可接受")
elif max_diff < 60:
    print("  ⚠ 背景基本合格，但与理想影棚图存在差距，可考虑替换")
else:
    print("  ✗ 背景不够纯净，建议替换为影棚官图")
