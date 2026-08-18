# -*- coding: utf-8 -*-
""" analyze_image_content.py
客观分析每张图片的像素内容，判断是否为正侧视外观图。
- 检测是否为内饰图（颜色分布、亮度特征）
- 检测背景是否纯净（4角像素相似度）
- 检测是否为户外图（天空蓝/绿色占比）
"""
import io, hashlib
from pathlib import Path
from PIL import Image as P

BRANDS_D = Path(__file__).resolve().parent.parent / "public" / "brands"
CAR_LIST = [
    ("rolls-royce","phantom"),("rolls-royce","ghost"),("rolls-royce","cullinan"),("rolls-royce","wraith"),
    ("bentley","continental-gt"),("bentley","continental-gtc"),("bentley","flying-spur"),("bentley","bentayga"),
    ("bugatti","chiron"),("bugatti","veyron"),("bugatti","divo"),
    ("porsche","911"),("porsche","taycan"),("porsche","panamera"),("porsche","cayenne"),("porsche","macan"),
    ("ferrari","sf90"),("ferrari","f8-tributo"),("ferrari","roma"),
]

def analyze(brand, model):
    p = BRANDS_D / brand / (model + ".jpg")
    if not p.exists():
        return f"  MISSING {brand}/{model}"
    raw = p.read_bytes()
    md5 = hashlib.md5(raw).hexdigest()[:12]
    try:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
            im_small = im.convert("RGB").resize((100, 100))
            pixels = list(im_small.getdata())
    except Exception as e:
        return f"  CORRUPT {brand}/{model}: {e}"

    # 分析像素
    # 1. 平均亮度
    brightness = sum((r+g+b)/3 for r,g,b in pixels) / len(pixels)
    # 2. 4个角的像素（检测背景纯净度）
    corners = [pixels[0], pixels[99], pixels[9900], pixels[9999]]
    corner_colors = [(r,g,b) for r,g,b in corners]
    # 4角颜色差异（标准差）
    corner_std = max(
        max(abs(c1[i]-c2[i]) for i in range(3))
        for c1 in corner_colors for c2 in corner_colors
    )
    # 3. 蓝色像素占比（检测天空）
    sky_pixels = sum(1 for r,g,b in pixels if b > 150 and b > r + 30 and b > g + 10)
    sky_ratio = sky_pixels / len(pixels)
    # 4. 绿色像素占比（检测户外草地）
    grass_pixels = sum(1 for r,g,b in pixels if g > 100 and g > r + 20 and g > b + 10)
    grass_ratio = grass_pixels / len(pixels)
    # 5. 暗色像素占比（检测影棚/暗背景）
    dark_pixels = sum(1 for r,g,b in pixels if (r+g+b)/3 < 50)
    dark_ratio = dark_pixels / len(pixels)
    # 6. 浅色像素占比（检测白色背景）
    light_pixels = sum(1 for r,g,b in pixels if (r+g+b)/3 > 220)
    light_ratio = light_pixels / len(pixels)
    # 7. 棕色/暖色像素占比（检测内饰皮革）
    brown_pixels = sum(1 for r,g,b in pixels if r > 80 and r < 200 and g > 50 and g < r and b < g and r - b > 30)
    brown_ratio = brown_pixels / len(pixels)

    # 判断图片类型
    bg_type = "未知"
    is_interior = False
    is_outdoor = False
    is_studio = False

    if brown_ratio > 0.25 and brightness < 130:
        is_interior = True
        bg_type = "疑似内饰(棕色皮革)"
    elif sky_ratio > 0.15 or grass_ratio > 0.10:
        is_outdoor = True
        bg_type = f"户外(天空{sky_ratio*100:.0f}% 草地{grass_ratio*100:.0f}%)"
    elif dark_ratio > 0.30:
        is_studio = True
        bg_type = f"暗色影棚(暗{dark_ratio*100:.0f}%)"
    elif light_ratio > 0.30:
        is_studio = True
        bg_type = f"白色影棚(白{light_ratio*100:.0f}%)"
    elif corner_std < 30:
        is_studio = True
        bg_type = f"纯净背景(4角差异{corner_std})"
    else:
        bg_type = f"复杂背景(4角差异{corner_std} 亮{brightness:.0f})"

    return f"{brand+'/'+model:<32} {w}x{h} {len(raw)/1024:>4.0f}KB md5={md5} | 亮{brightness:>3.0f} | {bg_type}"


print("=" * 130)
print(f"{'车型':<32} {'尺寸':<12} {'大小':<8} {'md5':<14} | 亮度 | 背景类型")
print("=" * 130)
for brand, model in CAR_LIST:
    print(analyze(brand, model))
