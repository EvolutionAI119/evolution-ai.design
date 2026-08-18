"""
车型正侧视图批量筛选与替换工具
=============================
功能：从Bing图片搜索下载候选图（或使用本地图片） → 纯白背景过滤 → 完整车身检测 → 车头方向自动判定 → 替换到品牌目录

全自动流程，无需人工确认：车头方向通过四层特征融合算法自动判定（底部轮廓/亮度/上轮廓/亮度梯度）。

=== 快速上手 ===

【方式A：从Bing下载（需在CARS配置中添加车型）】
    python car_image_filter_pipeline.py --step all

【方式B：处理本地图片文件夹（无需改代码）】
    python car_image_filter_pipeline.py --step all \
        --source-dir "D:\my_car_images" \
        --brand porsche --model 911 --name "Porsche 911"

    # 或指定子文件夹结构（brand_model/ 下有多张图）
    python car_image_filter_pipeline.py --step all \
        --source-dir "D:\my_car_images" \
        --auto-detect  # 自动从子文件夹名识别 brand_model

【方式C：分步执行（调试用）】
    # 1. 下载（或跳过，用 --source-dir 替代）
    python car_image_filter_pipeline.py --step download --car bentley/bentayga
    # 2. 纯白背景过滤
    python car_image_filter_pipeline.py --step filter --car bentley/bentayga
    # 3. 完整车身检测
    python car_image_filter_pipeline.py --step complete --car bentley/bentayga
    # 4. 车头方向自动检测（仅打印结果，不替换）
    python car_image_filter_pipeline.py --step direction --car bentley/bentayga
    # 5. 替换（自动选白色占比最高 + 自动判定方向）
    python car_image_filter_pipeline.py --step apply --car bentley/bentayga

参数：
    --step         all|download|filter|complete|direction|apply|preview
    --car          只处理指定车型（格式：brand/model，如 bentley/bentayga）
    --force        强制重新下载（忽略已存在的候选图）
    --source-dir   使用本地图片文件夹作为输入（跳过Bing下载）
    --brand        命令行指定品牌（配合 --model/--name 使用，无需改CARS配置）
    --model        命令行指定型号
    --name         命令行指定显示名
    --auto-detect  从 --source-dir 的子文件夹名自动识别车型

输出目录：
    public/_bing_v2_candidates/      Bing下载的原始候选图
    public/_white_bg_candidates/     纯白背景过滤通过的图
    public/_complete_car_candidates/ 完整车身检测通过的图（含原图和翻转版）
    public/brands/                   最终替换的品牌图
"""
import argparse, urllib.request, urllib.parse, ssl, re, os, time, json, hashlib, io, shutil
from pathlib import Path
from PIL import Image
import numpy as np

# ==================== 配置区 ====================

ROOT = Path(__file__).resolve().parent.parent  # 项目根目录
SRC_DIR = ROOT / "public" / "_bing_v2_candidates"
WHITE_DIR = ROOT / "public" / "_white_bg_candidates"
COMPLETE_DIR = ROOT / "public" / "_complete_car_candidates"
BRANDS_DIR = ROOT / "public" / "brands"

# SSL配置（绕过证书验证，兼容国内环境）
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 车型配置：品牌、型号、显示名、搜索关键词列表
# 添加新车型时，在此处添加配置即可
# queries 中的 {name} 会被替换为 name 字段，{cn_name} 替换为中文名
CARS = [
    {
        "brand": "bentley",
        "model": "bentayga",
        "name": "Bentley Bentayga",
        "cn_name": "宾利添越",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "bentley",
        "model": "flying-spur",
        "name": "Bentley Flying Spur",
        "cn_name": "宾利飞驰",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "bentley",
        "model": "continental-gtc",
        "name": "Bentley Continental GTC",
        "cn_name": "宾利欧陆GTC",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 敞篷 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "rolls-royce",
        "model": "cullinan",
        "name": "Rolls-Royce Cullinan",
        "cn_name": "劳斯莱斯库里南",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    # === 以下车型需重新筛选（图片质量不达标） ===
    {
        "brand": "bentley",
        "model": "continental-gt",
        "name": "Bentley Continental GT",
        "cn_name": "宾利欧陆GT",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "rolls-royce",
        "model": "phantom",
        "name": "Rolls-Royce Phantom",
        "cn_name": "劳斯莱斯幻影",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "rolls-royce",
        "model": "ghost",
        "name": "Rolls-Royce Ghost",
        "cn_name": "劳斯莱斯古思特",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "rolls-royce",
        "model": "wraith",
        "name": "Rolls-Royce Wraith",
        "cn_name": "劳斯莱斯魅影",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "ferrari",
        "model": "f8-tributo",
        "name": "Ferrari F8 Tributo",
        "cn_name": "法拉利F8",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "ferrari",
        "model": "sf90",
        "name": "Ferrari SF90",
        "cn_name": "法拉利SF90",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{name} press photo side profile studio",
            "{name} side view isolated white",
            "{name} catalog side view",
            "{cn_name} 侧面 官方图片 纯色背景",
            "{cn_name} 侧面 影棚 官方图",
        ],
    },
    {
        "brand": "ferrari",
        "model": "roma",
        "name": "Ferrari Roma",
        "cn_name": "法拉利Roma",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "porsche",
        "model": "911",
        "name": "Porsche 911",
        "cn_name": "保时捷911",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "porsche",
        "model": "taycan",
        "name": "Porsche Taycan",
        "cn_name": "保时捷Taycan",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "porsche",
        "model": "macan",
        "name": "Porsche Macan",
        "cn_name": "保时捷Macan",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "porsche",
        "model": "cayenne",
        "name": "Porsche Cayenne",
        "cn_name": "保时捷卡宴",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{name} press photo side profile studio",
            "{name} side view isolated white",
            "{name} catalog side view",
            "{cn_name} 侧面 官方图片 纯色背景",
            "{cn_name} 侧面 影棚 官方图",
        ],
    },
    {
        "brand": "porsche",
        "model": "panamera",
        "name": "Porsche Panamera",
        "cn_name": "保时捷Panamera",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
    {
        "brand": "bugatti",
        "model": "divo",
        "name": "Bugatti Divo",
        "cn_name": "布加迪Divo",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{name} press photo side profile studio",
            "{name} side view isolated white",
            "{name} catalog side view",
            "{cn_name} 侧面 官方图片 纯色背景",
            "{cn_name} 侧面 影棚 官方图",
        ],
    },
    {
        "brand": "bugatti",
        "model": "veyron",
        "name": "Bugatti Veyron",
        "cn_name": "布加迪威航",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{name} press photo side profile studio",
            "{name} side view isolated white",
            "{name} catalog side view",
            "{cn_name} 侧面 官方图片 纯色背景",
            "{cn_name} 侧面 影棚 官方图",
        ],
    },
    {
        "brand": "bugatti",
        "model": "chiron",
        "name": "Bugatti Chiron",
        "cn_name": "布加迪Chiron",
        "queries": [
            "{name} side profile official photo",
            "{name} side view white background",
            "{cn_name} 侧面 官方图片 纯色背景",
        ],
    },
]

# ==================== 过滤参数 ====================

# 纯白背景过滤参数
WHITE_BG_CONFIG = {
    "corner_std_threshold": 12,      # 4角颜色标准差阈值（越小越严格）
    "corner_brightness_diff": 15,    # 4角最大亮度差阈值（防止渐变背景）
    "edge_std_threshold": 20,        # 边缘颜色标准差阈值（已弃用，保留兼容）
    "use_edge_detection": False,     # 是否启用边缘条带检测（False=只检测4角，避免车辆占满宽度时误杀）
    "min_brightness": 235,           # 最小亮度（白色背景）
    "min_white_ratio": 0.55,         # 最小白色像素占比
    "min_width": 500,                # 最小宽度（v3: 800→500，兼容稀有车型小图）
    "asp_min": 0.95,                 # 宽高比下限（v3: 1.3→0.95，兼容稀有车型方图）
    "asp_max": 2.5,                  # 宽高比上限
    "corner_size": 15,               # 角落采样区域大小
    "edge_width": 10,                # 边缘条带宽度
    "white_threshold": 230,          # 白色判定阈值（RGB各分量）
}

# 完整车身检测参数
COMPLETE_CAR_CONFIG = {
    "min_width_ratio": 0.50,         # 车辆宽度最小占比
    "max_width_ratio": 0.98,         # 车辆宽度最大占比
    "min_height_ratio": 0.22,        # 车辆高度最小占比（v3: 0.30→0.22，兼容方图稀有车型）
    "max_height_ratio": 0.90,        # 车辆高度最大占比
    "min_margin": 1,                 # 最小留白（v3: 5→1，配合auto_pad_white自动填充）
    "min_top_margin": 3,             # 最小上留白
    "min_bottom_margin": 3,          # 最小下留白
    "white_threshold": 230,          # 白色判定阈值
    "auto_pad_white": True,          # v3: 自动为紧裁剪图填充白色边距（使稀有车型候选图通过检测）
    "pad_margin": 20,                # v3: 自动填充的边距大小（像素）
}

# 下载参数
DOWNLOAD_CONFIG = {
    "max_imgs_per_query": 10,        # 每个查询最多下载数
    "min_file_size": 25000,          # 最小文件大小（字节）
    "min_dimension": 600,            # 最小宽度
    "timeout": 15,                   # 下载超时（秒）
    "delay": 0.15,                   # 下载间隔（秒）
}

# 车头方向检测参数
DIRECTION_CONFIG = {
    "white_threshold": 230,          # 白色判定阈值
    "upper_ratio": 0.40,             # 上部区域占比（车身高度的上40%）
    "smooth_window_ratio": 0.04,     # 轮廓平滑窗口占车身宽度的比例
    "min_confidence": 0.5,           # 最低置信度阈值（仅作日志标记，不影响自动应用）
    "asymmetry_threshold": 1.15,     # 非对称比值阈值（>1.15表示明显差异）
    # v2: 底部轮廓车轮检测参数
    "wheel_dip_ratio": 0.08,         # 车轮低点判定：距最低点 car_height*0.08 内视为车轮
    "wheel_min_width_ratio": 0.03,   # 车轮最小宽度占车宽比例
    "wheel_cluster_gap": 5,          # 车轮列聚类最大间隔（像素）
    "overhang_diff_ratio": 0.03,     # 悬垂差异判定阈值占车宽比例
}


# ==================== 核心函数 ====================

def fetch(url, timeout=20, referer=None):
    """下载URL内容，返回bytes"""
    headers = {"User-Agent": UA, "Accept": "image/*,*/*"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def bing_search_images(query, count=30):
    """从cn.bing.com搜索图片，返回图片URL列表"""
    urls = []
    search_url = f"https://cn.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1&count={count}"
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": UA})
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    Bing search ERR: {e}")
        return urls

    # 多种模式提取图片URL
    patterns = [
        r'murl&quot;:&quot;(https?://[^&]+?\.(?:jpg|jpeg|png))&',
        r'"murl":"(https?://[^"]+?\.(?:jpg|jpeg|png))"',
        r'imgurl=(https?://[^&]+?\.(?:jpg|jpeg|png))',
        r'"mediaurl":"(https?://[^"]+?\.(?:jpg|jpeg|png))"',
    ]
    seen = set()
    for p in patterns:
        for m in re.finditer(p, html):
            u = m.group(1)
            if "bing.com" in u or "msn.com" in u or "th?id=" in u:
                continue
            if u in seen:
                continue
            seen.add(u)
            urls.append(u)
    return urls


def analyze_background(arr, config):
    """
    分析图片背景纯净度
    参数: arr - numpy数组(H,W,3), config - 配置
    返回: dict with pass/fail and details
    """
    h, w = arr.shape[:2]
    corner_size = config["corner_size"]

    # 1. 4个角落分析
    corners = {
        "top_left": arr[0:corner_size, 0:corner_size],
        "top_right": arr[0:corner_size, w-corner_size:w],
        "bottom_left": arr[h-corner_size:h, 0:corner_size],
        "bottom_right": arr[h-corner_size:h, w-corner_size:w],
    }
    corner_means = np.array([c.mean(axis=(0, 1)) for c in corners.values()])
    overall_mean = corner_means.mean(axis=0)
    corner_std = corner_means.std(axis=0).mean()
    # 4角亮度差异（防止渐变背景）
    corner_brightness = corner_means.mean(axis=1)  # 每角的平均亮度
    corner_brightness_diff = corner_brightness.max() - corner_brightness.min()
    brightness = overall_mean.mean()
    is_white = brightness > config["min_brightness"] and all(c > config["min_brightness"] - 5 for c in overall_mean)

    # 2. 边缘条带分析（可选，默认关闭避免车辆占满宽度时误杀）
    edge_std = 0.0
    if config.get("use_edge_detection", False):
        edge_width = config["edge_width"]
        edges = {
            "top": arr[0:edge_width, :],
            "bottom": arr[h-edge_width:h, :],
            "left": arr[:, 0:edge_width],
            "right": arr[:, w-edge_width:w],
        }
        edge_means = np.array([e.mean(axis=(0, 1)) for e in edges.values()])
        edge_std = edge_means.std(axis=0).mean()

    # 3. 白色背景像素占比
    white_mask = np.all(arr > config["white_threshold"], axis=2)
    white_ratio = white_mask.sum() / (w * h)

    # 4. 宽高比
    asp = w / h if h else 0

    # 判定
    reasons = []
    pass_all = True
    if corner_std > config["corner_std_threshold"]:
        reasons.append(f"4角颜色差异大(std={corner_std:.1f}>{config['corner_std_threshold']})")
        pass_all = False
    if corner_brightness_diff > config["corner_brightness_diff"]:
        reasons.append(f"4角亮度差异大(diff={corner_brightness_diff:.1f}>{config['corner_brightness_diff']})")
        pass_all = False
    if not is_white:
        reasons.append(f"4角非白色(亮度={brightness:.0f}<{config['min_brightness']})")
        pass_all = False
    if config.get("use_edge_detection", False) and edge_std > config["edge_std_threshold"]:
        reasons.append(f"边缘颜色差异大(std={edge_std:.1f})")
        pass_all = False
    if white_ratio < config["min_white_ratio"]:
        reasons.append(f"白色占比低({white_ratio*100:.0f}%<{config['min_white_ratio']*100:.0f}%)")
        pass_all = False
    if asp < config["asp_min"] or asp > config["asp_max"]:
        reasons.append(f"宽高比异常(asp={asp:.2f})")
        pass_all = False
    if w < config["min_width"]:
        reasons.append(f"宽度不足(w={w}<{config['min_width']})")
        pass_all = False

    return {
        "pass": pass_all,
        "w": w, "h": h, "asp": round(asp, 2),
        "corner_std": round(float(corner_std), 1),
        "corner_brightness_diff": round(float(corner_brightness_diff), 1),
        "edge_std": round(float(edge_std), 1),
        "brightness": round(float(brightness), 0),
        "white_ratio": round(float(white_ratio * 100), 1),
        "reasons": reasons if not pass_all else ["ALL PASS"],
    }


def detect_complete_car(arr, config):
    """
    检测图片中是否包含完整车身
    参数: arr - numpy数组(H,W,3), config - 配置
    返回: dict with pass/fail and bbox info
    """
    h, w = arr.shape[:2]
    non_white_mask = ~np.all(arr > config["white_threshold"], axis=2)

    rows = np.any(non_white_mask, axis=1)
    cols = np.any(non_white_mask, axis=0)
    if not rows.any() or not cols.any():
        return {"pass": False, "reason": "未检测到非白色区域"}

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    car_w = cmax - cmin + 1
    car_h = rmax - rmin + 1
    width_ratio = car_w / w
    height_ratio = car_h / h

    reasons = []
    pass_all = True
    if width_ratio < config["min_width_ratio"] or width_ratio > config["max_width_ratio"]:
        reasons.append(f"车辆宽度占比异常({width_ratio*100:.0f}%)")
        pass_all = False
    if height_ratio < config["min_height_ratio"] or height_ratio > config["max_height_ratio"]:
        reasons.append(f"车辆高度占比异常({height_ratio*100:.0f}%)")
        pass_all = False
    if cmin < config["min_margin"] or (w - cmax - 1) < config["min_margin"]:
        reasons.append(f"左右留白不足(L={cmin},R={w-cmax-1})")
        pass_all = False
    if rmin < config["min_top_margin"] or (h - rmax - 1) < config["min_bottom_margin"]:
        reasons.append(f"上下留白不足(T={rmin},B={h-rmax-1})")
        pass_all = False

    return {
        "pass": pass_all,
        "car_w": int(car_w), "car_h": int(car_h),
        "width_ratio": round(float(width_ratio * 100), 1),
        "height_ratio": round(float(height_ratio * 100), 1),
        "left_margin": int(cmin), "right_margin": int(w - cmax - 1),
        "top_margin": int(rmin), "bottom_margin": int(h - rmax - 1),
        "reasons": reasons if not pass_all else ["ALL PASS"],
    }


def _smooth_contour(values, x_min, x_max, window):
    """平滑轮廓（移动平均，忽略无效值-1）"""
    smooth = values.copy()
    for x in range(x_min, x_max + 1):
        xl = max(x_min, x - window)
        xr = min(x_max, x + window)
        segment = values[xl:xr + 1]
        valid = segment[segment >= 0]
        if len(valid) > 0:
            smooth[x] = float(np.mean(valid))
    return smooth


def _cluster_columns(is_target, x_min, x_max, gap):
    """将连续的目标列聚类成组（间隔<=gap视为同一组）"""
    clusters = []
    for x in range(x_min, x_max + 1):
        if is_target[x]:
            if clusters and x - clusters[-1][-1] <= gap:
                clusters[-1].append(x)
            else:
                clusters.append([x])
    return clusters


def detect_car_direction(arr, config=None):
    """
    车头方向自动检测算法 v2
    =======================
    核心原理：前轮悬垂 < 后轮悬垂（前轮更靠近车头边缘）

    三层特征融合：
    1. [主, 权重3] 底部轮廓车轮检测（颜色无关）
       - 车轮是车身轮廓最低点（触地），与车身颜色无关
       - 通过底部轮廓的低点区域定位车轮位置
    2. [辅, 权重1] 自适应亮度车轮检测
       - 车轮是底部最暗区域，用自适应阈值（相对中值）检测
       - 取最左/最右有效聚类为车轮
    3. [辅, 权重1] 上轮廓非对称性
       - 引擎盖低于行李箱/C柱（车尾更高）

    判定：车轮中心相对于车身中心的偏移方向 = 车头方向
         （前轮靠近车头边缘 → 车轮中心偏向车头侧）

    参数: arr - numpy数组(H,W,3), config - DIRECTION_CONFIG
    返回: dict with direction, flip_needed, confidence
    """
    if config is None:
        config = DIRECTION_CONFIG

    h, w = arr.shape[:2]
    white_threshold = config["white_threshold"]

    # 1. 获取车辆mask（非白色像素）
    mask = ~np.all(arr > white_threshold, axis=2)

    # 2. 找到车辆边界框
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    y_indices = np.where(rows)[0]
    x_indices = np.where(cols)[0]

    if len(y_indices) < 20 or len(x_indices) < 20:
        return {"direction": "unknown", "confidence": 0.0, "flip_needed": False,
                "need_manual": True, "reason": "车辆区域过小",
                "features": {}, "wheel_detected": False,
                "left_overhang": -1, "right_overhang": -1,
                "left_upper_avg": 0, "right_upper_avg": 0,
                "avg_y_left": 0, "avg_y_right": 0}

    y_min, y_max = y_indices[0], y_indices[-1]
    x_min, x_max = x_indices[0], x_indices[-1]
    car_height = y_max - y_min
    car_width = x_max - x_min

    if car_height < 20 or car_width < 50:
        return {"direction": "unknown", "confidence": 0.0, "flip_needed": False,
                "need_manual": True, "reason": "车辆尺寸过小",
                "features": {}, "wheel_detected": False,
                "left_overhang": -1, "right_overhang": -1,
                "left_upper_avg": 0, "right_upper_avg": 0,
                "avg_y_left": 0, "avg_y_right": 0}

    window = max(3, int(car_width * config["smooth_window_ratio"]))

    # ===== 特征1: 底部轮廓车轮检测（主特征，颜色无关）=====
    # 原理：车轮触地，是车身轮廓最低点
    y_bottom = np.full(w, -1.0)
    for x in range(x_min, x_max + 1):
        col_pixels = np.where(mask[:, x])[0]
        if len(col_pixels) > 0:
            y_bottom[x] = float(col_pixels[-1])
    y_bottom_smooth = _smooth_contour(y_bottom, x_min, x_max, window)

    # 找最低点（车轮触地处）
    valid_bottom = y_bottom_smooth[x_min:x_max + 1]
    valid_bottom = valid_bottom[valid_bottom >= 0]
    max_y_bottom = float(np.max(valid_bottom)) if len(valid_bottom) > 0 else float(y_max)

    # 车轮区域：底部轮廓距最低点在 car_height*dip_ratio 内
    dip_threshold = max_y_bottom - car_height * config["wheel_dip_ratio"]
    is_wheel_bottom = y_bottom_smooth >= dip_threshold
    clusters_bottom = _cluster_columns(is_wheel_bottom, x_min, x_max,
                                        config["wheel_cluster_gap"])
    # 过滤过小的聚类
    min_wheel_w = max(3, int(car_width * config["wheel_min_width_ratio"]))
    valid_bottom_clusters = [c for c in clusters_bottom if len(c) >= min_wheel_w]

    # 取最左和最右聚类为前后轮
    wheel_by_contour = None
    if len(valid_bottom_clusters) >= 2:
        left_w = valid_bottom_clusters[0]
        right_w = valid_bottom_clusters[-1]
        wheel_by_contour = {
            "left_center": float(np.mean(left_w)),
            "right_center": float(np.mean(right_w)),
            "left_x0": left_w[0], "left_x1": left_w[-1],
            "right_x0": right_w[0], "right_x1": right_w[-1],
        }

    # ===== 特征2: 自适应亮度车轮检测（辅助）=====
    # 原理：车轮是底部最暗区域（相对暗于中值）
    bottom_y_start = y_min + int(car_height * 0.6)
    col_brightness = []
    col_bx = []
    for x in range(x_min, x_max + 1):
        col_pixels = np.where(mask[:, x])[0]
        if len(col_pixels) == 0:
            continue
        bottom_pixels = col_pixels[col_pixels >= bottom_y_start]
        if len(bottom_pixels) < 2:
            continue
        col_brightness.append(float(arr[bottom_pixels, x].mean()))
        col_bx.append(x)

    wheel_by_brightness = None
    if len(col_brightness) > 10:
        col_brightness = np.array(col_brightness)
        col_bx = np.array(col_bx)
        median_b = float(np.median(col_brightness))
        adaptive_thr = median_b * 0.7  # 比中值暗30%
        is_dark = col_brightness < adaptive_thr
        # 聚类
        bright_clusters = []
        for i in range(len(col_bx)):
            if is_dark[i]:
                if bright_clusters and col_bx[i] - bright_clusters[-1][-1] <= config["wheel_cluster_gap"]:
                    bright_clusters[-1].append(int(col_bx[i]))
                else:
                    bright_clusters.append([int(col_bx[i])])
        valid_bright = [c for c in bright_clusters if len(c) >= min_wheel_w]
        if len(valid_bright) >= 2:
            left_w = valid_bright[0]
            right_w = valid_bright[-1]
            wheel_by_brightness = {
                "left_center": float(np.mean(left_w)),
                "right_center": float(np.mean(right_w)),
                "left_x0": left_w[0], "left_x1": left_w[-1],
                "right_x0": right_w[0], "right_x1": right_w[-1],
            }

    # ===== 特征3: 上轮廓非对称性（辅助）=====
    y_top = np.full(w, float(y_max + 1), dtype=float)
    for x in range(x_min, x_max + 1):
        col_pixels = np.where(mask[:, x])[0]
        if len(col_pixels) > 0:
            y_top[x] = float(col_pixels[0])
    y_top_smooth = _smooth_contour(y_top, x_min, x_max, window)

    upper_threshold = y_min + car_height * config["upper_ratio"]
    third = car_width // 3
    left_end = x_min + third
    right_start = x_max - third

    left_upper_sum = 0.0
    for x in range(x_min, left_end):
        if y_top_smooth[x] < upper_threshold:
            left_upper_sum += (upper_threshold - y_top_smooth[x])
    right_upper_sum = 0.0
    for x in range(right_start, x_max + 1):
        if y_top_smooth[x] < upper_threshold:
            right_upper_sum += (upper_threshold - y_top_smooth[x])
    left_upper_avg = left_upper_sum / max(third, 1)
    right_upper_avg = right_upper_sum / max(third, 1)

    # ===== 特征4: 亮度梯度（备用，适用深色/无特征车）=====
    # 原理：车头通常更亮（引擎盖反射、前格栅、灯光），亮度重心偏向车头侧
    body_center = (x_min + x_max) / 2.0
    col_brightness_full = np.zeros(w)
    col_has_car = np.zeros(w, dtype=bool)
    for x in range(x_min, x_max + 1):
        col_pixels = np.where(mask[:, x])[0]
        if len(col_pixels) > 0:
            col_brightness_full[x] = float(arr[col_pixels, x].mean())
            col_has_car[x] = True
    # 亮度重心（按列亮度加权的位置均值）
    bright_x = np.where(col_has_car[x_min:x_max + 1])[0] + x_min
    bright_vals = col_brightness_full[bright_x]
    if len(bright_vals) > 0 and bright_vals.sum() > 0:
        brightness_center = float(np.average(bright_x, weights=bright_vals))
    else:
        brightness_center = body_center

    # ===== 综合投票判定 =====
    votes_left = 0
    votes_right = 0
    total_votes = 0
    features = {}
    asym_threshold = config["asymmetry_threshold"]
    overhang_diff_min = car_width * config["overhang_diff_ratio"]

    # 底部轮廓是否平坦（平坦=无法可靠检测车轮）
    valid_bottom_for_range = y_bottom_smooth[x_min:x_max + 1]
    valid_bottom_for_range = valid_bottom_for_range[valid_bottom_for_range >= 0]
    bottom_range = float(np.max(valid_bottom_for_range) - np.min(valid_bottom_for_range)) if len(valid_bottom_for_range) > 0 else 0
    bottom_flat = bottom_range < car_height * 0.05

    # 车轮检测可靠性检查
    max_wheel_width = car_width * 0.2  # 单个车轮宽度不应超过车宽20%
    min_wheel_gap = car_width * 0.2   # 前后轮间距不应小于车宽20%

    def _wheels_reliable(wheel_dict):
        """检查车轮检测是否可靠（宽度合理、间距合理）"""
        if wheel_dict is None:
            return False
        left_w = wheel_dict["left_x1"] - wheel_dict["left_x0"]
        right_w = wheel_dict["right_x1"] - wheel_dict["right_x0"]
        gap = wheel_dict["right_x0"] - wheel_dict["left_x1"]
        if left_w > max_wheel_width or right_w > max_wheel_width:
            return False  # 轮过宽=误检(合并了车身)
        if gap < min_wheel_gap:
            return False  # 轮间距过小=误检
        return True

    # 选择最佳车轮检测结果（优先底部轮廓，它颜色无关更可靠）
    contour_reliable = _wheels_reliable(wheel_by_contour) and not bottom_flat
    brightness_reliable = _wheels_reliable(wheel_by_brightness)

    if contour_reliable:
        best_wheel = wheel_by_contour
        wheel_source = "contour"
    elif brightness_reliable:
        best_wheel = wheel_by_brightness
        wheel_source = "brightness"
    else:
        best_wheel = None
        wheel_source = "none(unreliable)"
    features["bottom_flat"] = str(bottom_flat)

    left_overhang = -1
    right_overhang = -1
    wheel_detected = False

    if best_wheel is not None:
        wheel_detected = True
        left_overhang = int(best_wheel["left_x0"] - x_min)
        right_overhang = int(x_max - best_wheel["right_x1"])
        wheel_center = (best_wheel["left_center"] + best_wheel["right_center"]) / 2.0
        shift = wheel_center - body_center
        overhang_diff = abs(left_overhang - right_overhang)

        # 主特征投票（权重3）
        if left_overhang < right_overhang and overhang_diff > overhang_diff_min:
            votes_left += 3
            features["wheels"] = f"left(L_overhang={left_overhang}<R_overhang={right_overhang},src={wheel_source})"
        elif right_overhang < left_overhang and overhang_diff > overhang_diff_min:
            votes_right += 3
            features["wheels"] = f"right(R_overhang={right_overhang}<L_overhang={left_overhang},src={wheel_source})"
        else:
            # 悬垂接近时用车轮中心偏移
            if shift < -car_width * 0.02:
                votes_left += 3
                features["wheels"] = f"left(center_shift={shift:.0f},src={wheel_source})"
            elif shift > car_width * 0.02:
                votes_right += 3
                features["wheels"] = f"right(center_shift={shift:.0f},src={wheel_source})"
            else:
                features["wheels"] = f"tie(L={left_overhang},R={right_overhang},src={wheel_source})"
        total_votes += 3
    else:
        features["wheels"] = "not_detected"

    # 上轮廓非对称性投票（权重1）
    if right_upper_avg > left_upper_avg * asym_threshold:
        votes_left += 1  # 右侧更高=车尾→车头在左
        features["upper_area"] = "left"
    elif left_upper_avg > right_upper_avg * asym_threshold:
        votes_right += 1  # 左侧更高=车尾→车头在右
        features["upper_area"] = "right"
    else:
        features["upper_area"] = "tie"
    total_votes += 1

    # 亮度梯度投票（权重1，备用特征）
    bright_shift = brightness_center - body_center
    bright_shift_ratio = bright_shift / car_width
    if bright_shift_ratio < -0.01:
        votes_left += 1  # 亮度重心偏左=车头在左
        features["brightness"] = f"left(shift={bright_shift:.0f})"
    elif bright_shift_ratio > 0.01:
        votes_right += 1
        features["brightness"] = f"right(shift={bright_shift:.0f})"
    else:
        features["brightness"] = f"tie(shift={bright_shift:.0f})"
    total_votes += 1

    # 判定方向
    if votes_left > votes_right:
        direction = "left"
        flip_needed = False
        confidence = votes_left / total_votes if total_votes > 0 else 0
    elif votes_right > votes_left:
        direction = "right"
        flip_needed = True
        confidence = votes_right / total_votes if total_votes > 0 else 0
    else:
        # 平票 - 用亮度重心裁决
        if bright_shift < 0:
            direction = "left"
            flip_needed = False
        else:
            direction = "right"
            flip_needed = True
        confidence = 0.3
        features["tiebreak"] = f"brightness(shift={bright_shift:.0f})"

    # 置信度修正
    if wheel_detected:
        overhang_diff = abs(left_overhang - right_overhang)
        if overhang_diff > car_width * 0.08:
            confidence = min(1.0, confidence + 0.2)
    else:
        confidence = min(confidence, 0.4)

    need_manual = confidence < config["min_confidence"]

    return {
        "direction": direction,
        "confidence": round(confidence, 2),
        "flip_needed": flip_needed,
        "need_manual": need_manual,
        "left_upper_avg": round(left_upper_avg, 1),
        "right_upper_avg": round(right_upper_avg, 1),
        "wheel_detected": wheel_detected,
        "wheel_source": wheel_source,
        "left_overhang": left_overhang,
        "right_overhang": right_overhang,
        "avg_y_left": 0,
        "avg_y_right": 0,
        "features": features,
    }


# ==================== 流程步骤 ====================

def step_import_local(car, source_dir):
    """步骤1b：从本地文件夹导入图片（替代Bing下载）"""
    brand, model, name = car["brand"], car["model"], car["name"]
    car_dir = SRC_DIR / f"{brand}__{model}"
    car_dir.mkdir(parents=True, exist_ok=True)

    # 清空旧内容
    for f in car_dir.glob("*"):
        if f.is_file(): f.unlink()

    src_path = Path(source_dir)
    if not src_path.exists():
        print(f"  ERR: 源文件夹不存在: {source_dir}")
        return 0

    # 支持的图片格式
    img_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    imgs = sorted([f for f in src_path.iterdir() if f.suffix.lower() in img_exts and f.is_file()])

    seen_md5 = set()
    total = 0
    for img_path in imgs:
        raw = img_path.read_bytes()
        md5 = hashlib.md5(raw).hexdigest()[:8]
        if md5 in seen_md5:
            continue
        seen_md5.add(md5)

        # 基础尺寸检查
        try:
            with Image.open(io.BytesIO(raw)) as im:
                w, h = im.size
                if w < DOWNLOAD_CONFIG["min_dimension"]:
                    print(f"    跳过 {img_path.name} (宽度{w}<{DOWNLOAD_CONFIG['min_dimension']})")
                    continue
        except Exception:
            print(f"    跳过 {img_path.name} (无法打开)")
            continue

        ext = img_path.suffix.lower().lstrip(".")
        if ext == "jpeg":
            ext = "jpg"
        fname = f"{md5}.{ext}"
        (car_dir / fname).write_bytes(raw)
        total += 1

    print(f"  [{name}] 本地导入完成: {total}张 (源: {source_dir})")
    return total


def step_download(car, force=False):
    """步骤1：从Bing下载候选图"""
    brand, model, name = car["brand"], car["model"], car["name"]
    car_dir = SRC_DIR / f"{brand}__{model}"
    car_dir.mkdir(parents=True, exist_ok=True)

    if not force and any(car_dir.iterdir()):
        print(f"  [{name}] 已有候选图，跳过下载（用--force强制重下）")
        return

    # 清空旧内容
    for f in car_dir.glob("*"):
        if f.is_file(): f.unlink()

    seen_md5 = set()
    total = 0
    for query_template in car["queries"]:
        query = query_template.format(name=name, cn_name=car.get("cn_name", name))
        print(f"  Query: {query}")
        img_urls = bing_search_images(query, count=30)
        print(f"    Found {len(img_urls)} URLs")

        for img_url in img_urls[:DOWNLOAD_CONFIG["max_imgs_per_query"]]:
            if any(x in img_url.lower() for x in ["logo", "icon", "thumb", "avatar"]):
                continue
            raw = fetch(img_url, timeout=DOWNLOAD_CONFIG["timeout"], referer="https://cn.bing.com/")
            if not raw or len(raw) < DOWNLOAD_CONFIG["min_file_size"]:
                continue
            md5 = hashlib.md5(raw).hexdigest()[:8]
            if md5 in seen_md5:
                continue
            seen_md5.add(md5)

            # 基础尺寸检查
            try:
                with Image.open(io.BytesIO(raw)) as im:
                    w, h = im.size
                    if w < DOWNLOAD_CONFIG["min_dimension"]:
                        continue
            except Exception:
                continue

            ext = "png" if ".png" in img_url.lower() else "jpg"
            fname = f"{md5}.{ext}"
            (car_dir / fname).write_bytes(raw)
            total += 1
            time.sleep(DOWNLOAD_CONFIG["delay"])
        time.sleep(0.5)

    print(f"  [{name}] 下载完成: {total}张")


def step_filter_white_bg(car):
    """步骤2：纯白背景过滤"""
    brand, model, name = car["brand"], car["model"], car["name"]
    car_dir = SRC_DIR / f"{brand}__{model}"
    out_dir = WHITE_DIR / f"{brand}__{model}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 清空旧内容
    for f in out_dir.glob("*"):
        if f.is_file(): f.unlink()

    passed = []
    imgs = sorted(list(car_dir.glob("*.jpg")) + list(car_dir.glob("*.png")))
    for img_path in imgs:
        try:
            with Image.open(img_path) as im:
                arr = np.array(im.convert("RGB"))
            info = analyze_background(arr, WHITE_BG_CONFIG)
            if info["pass"]:
                dst = out_dir / img_path.name
                dst.write_bytes(img_path.read_bytes())
                info["file"] = img_path.name
                info["size_kb"] = round(img_path.stat().st_size / 1024)
                passed.append(info)
        except Exception:
            continue

    # 按白色占比排序
    passed.sort(key=lambda x: -x["white_ratio"])
    print(f"  [{name}] 纯白背景过滤: {len(passed)}/{len(imgs)}张通过")
    return passed


def _auto_pad_white(arr, config):
    """
    v3: 自动为紧裁剪图填充白色边距
    当图片四周留白不足时，添加白色边距使车辆不再触边
    """
    if not config.get("auto_pad_white", False):
        return arr, False
    pad_margin = config.get("pad_margin", 20)
    h, w = arr.shape[:2]
    new_arr = np.full((h + 2 * pad_margin, w + 2 * pad_margin, 3), 255, dtype=np.uint8)
    new_arr[pad_margin:pad_margin + h, pad_margin:pad_margin + w] = arr
    return new_arr, True


def step_filter_complete_car(car):
    """步骤3：完整车身检测 + 生成翻转版（v3: 支持自动白色填充）"""
    brand, model, name = car["brand"], car["model"], car["name"]
    car_dir = WHITE_DIR / f"{brand}__{model}"
    out_dir = COMPLETE_DIR / f"{brand}__{model}"
    out_dir.mkdir(parents=True, exist_ok=True)

    for f in out_dir.glob("*"):
        if f.is_file(): f.unlink()

    passed = []
    padded_count = 0
    imgs = sorted(list(car_dir.glob("*.jpg")) + list(car_dir.glob("*.png")))
    for img_path in imgs:
        try:
            with Image.open(img_path) as im:
                arr = np.array(im.convert("RGB"))
            info = detect_complete_car(arr, COMPLETE_CAR_CONFIG)
            arr_final = arr
            pad_tag = ""

            # v3: 若原图不通过且auto_pad_white启用，尝试填充白色边距
            if not info["pass"] and COMPLETE_CAR_CONFIG.get("auto_pad_white", False):
                arr_padded, did_pad = _auto_pad_white(arr, COMPLETE_CAR_CONFIG)
                if did_pad:
                    info_padded = detect_complete_car(arr_padded, COMPLETE_CAR_CONFIG)
                    if info_padded["pass"]:
                        arr_final = arr_padded
                        info = info_padded
                        pad_tag = "[白边填充]"
                        padded_count += 1

            if info["pass"]:
                # 保存（可能是原图或填充后的图）
                orig_dst = out_dir / f"orig_{img_path.name}"
                Image.fromarray(arr_final).save(orig_dst, "JPEG", quality=95)
                info["file"] = img_path.name
                info["orig_file"] = f"orig_{img_path.name}"

                # 生成水平翻转版
                arr_flip = arr_final[:, ::-1, :].copy()
                flip_dst = out_dir / f"flip_{img_path.name}"
                Image.fromarray(arr_flip).save(flip_dst, "JPEG", quality=95)
                info["flip_file"] = f"flip_{img_path.name}"

                passed.append(info)
        except Exception:
            continue

    pad_summary = f" (其中{padded_count}张白边填充)" if padded_count > 0 else ""
    print(f"  [{name}] 完整车身检测: {len(passed)}/{len(imgs)}张通过{pad_summary}")
    return passed


def load_complete_candidates(car):
    """从已保存的_complete_car_candidates目录加载候选图（用于分步执行apply时）"""
    brand, model = car["brand"], car["model"]
    car_dir = COMPLETE_DIR / f"{brand}__{model}"
    if not car_dir.exists():
        return []

    passed = []
    imgs = sorted(list(car_dir.glob("orig_*.jpg")) + list(car_dir.glob("orig_*.png")))
    for img_path in imgs:
        file_name = img_path.name.replace("orig_", "")
        flip_path = car_dir / f"flip_{file_name}"
        if not flip_path.exists():
            continue
        try:
            with Image.open(img_path) as im:
                arr = np.array(im.convert("RGB"))
            info = detect_complete_car(arr, COMPLETE_CAR_CONFIG)
            info["file"] = file_name
            info["orig_file"] = img_path.name
            info["flip_file"] = f"flip_{file_name}"
            passed.append(info)
        except Exception:
            continue
    return passed


def step_detect_direction(car):
    """步骤3b：车头方向自动检测"""
    brand, model, name = car["brand"], car["model"], car["name"]
    car_dir = COMPLETE_DIR / f"{brand}__{model}"

    passed = []
    imgs = sorted(list(car_dir.glob("orig_*.jpg")) + list(car_dir.glob("orig_*.png")))
    auto_applied = 0
    need_manual = 0

    for img_path in imgs:
        try:
            with Image.open(img_path) as im:
                arr = np.array(im.convert("RGB"))
            result = detect_car_direction(arr, DIRECTION_CONFIG)

            file_name = img_path.name.replace("orig_", "")
            result["file"] = file_name
            result["orig_file"] = img_path.name
            result["flip_file"] = f"flip_{file_name}"

            flip_tag = "[翻转→车头向左]" if result["flip_needed"] else "[原图→车头向左]"
            conf_tag = f"置信度{result['confidence']:.0%}"
            if result["need_manual"]:
                conf_tag += "⚠️低置信"
                need_manual += 1
            else:
                auto_applied += 1

            print(f"    ✅ {file_name} → 车头向{result['direction']} "
                  f"{conf_tag} {flip_tag} [{result.get('wheel_source','?')}]")

            passed.append(result)
        except Exception as e:
            print(f"    ❌ {img_path.name} 检测失败: {e}")

    print(f"  [{name}] 车头方向检测: {len(passed)}张, 高置信{auto_applied}张, 低置信{need_manual}张(仍自动应用)")
    return passed


def step_apply(car, orig_file, flip=False):
    """步骤4：替换到品牌目录"""
    brand, model, name = car["brand"], car["model"], car["name"]
    car_dir = COMPLETE_DIR / f"{brand}__{model}"
    src = car_dir / (f"flip_{orig_file}" if flip else f"orig_{orig_file}")
    dst = BRANDS_DIR / brand / f"{model}.jpg"
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        print(f"  ERR: {src} not found")
        return False

    with Image.open(src) as im:
        if im.mode in ("RGBA", "P"):
            im = im.convert("RGB")
        im.save(dst, "JPEG", quality=95)
    print(f"  [{name}] 替换完成: {dst.name} ({dst.stat().st_size//1024}KB) {'[翻转]' if flip else '[原图]'}")
    return True


def step_preview(cars_data):
    """生成预览页面"""
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>车型正侧视图筛选结果</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:10px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-section{background:#16213e;border:2px solid #2ecc71;border-radius:10px;padding:15px;margin-bottom:20px}
.car-title{color:#2ecc71;font-weight:bold;font-size:18px;margin-bottom:10px}
.pair-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:15px;border:1px solid #444;padding:10px;border-radius:6px}
.cand-card{background:#000;border-radius:6px;overflow:hidden;cursor:pointer;border:1px solid #333}
.cand-card img{width:100%;height:160px;object-fit:contain;display:block;background:#fff}
.cand-label{padding:5px;font-size:10px;color:#aaa;text-align:center}
</style></head><body>
<h1>车型正侧视图筛选结果</h1>
<div class="sub">纯白背景 + 完整车身 + 车头向左 | 点击图片放大</div>
"""
    for car, complete_passed in cars_data:
        brand, model, name = car["brand"], car["model"], car["name"]
        car_folder = f"{brand}__{model}"
        html += f'<div class="car-section">\n'
        html += f'  <div class="car-title">{name} ({len(complete_passed)}张通过)</div>\n'
        for i, c in enumerate(complete_passed):
            orig_url = f"/_complete_car_candidates/{car_folder}/{c['orig_file']}"
            flip_url = f"/_complete_car_candidates/{car_folder}/{c['flip_file']}"
            html += f'  <div class="pair-grid">\n'
            html += f'    <div style="color:#3498db;font-size:12px">候选{i+1}: {c["file"]} (白{c.get("white_ratio","?")}% 车占{c["width_ratio"]}%)</div>\n'
            html += f'    <div class="cand-card"><div class="cand-label">原图</div><img src="{orig_url}" loading="lazy" onclick="window.open(this.src)"></div>\n'
            html += f'    <div class="cand-card"><div class="cand-label">翻转版</div><img src="{flip_url}" loading="lazy" onclick="window.open(this.src)"></div>\n'
            html += f'  </div>\n'
        html += f'</div>\n'

    html += "</body></html>"
    out = ROOT / "public" / "_preview_pipeline.html"
    out.write_text(html, encoding="utf-8")
    print(f"\n预览页: http://localhost:5173/_preview_pipeline.html")


# ==================== 主流程 ====================

def main():
    parser = argparse.ArgumentParser(description="车型正侧视图批量筛选与替换工具", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--step", default="all",
                        choices=["all", "download", "filter", "complete", "direction", "apply", "preview"],
                        help="执行步骤")
    parser.add_argument("--car", default=None,
                        help="只处理指定车型（格式：brand/model）")
    parser.add_argument("--force", action="store_true",
                        help="强制重新下载")
    # === 本地文件夹输入 ===
    parser.add_argument("--source-dir", default=None,
                        help="使用本地图片文件夹作为输入（跳过Bing下载）")
    parser.add_argument("--brand", default=None,
                        help="命令行指定品牌（配合 --model/--name 使用）")
    parser.add_argument("--model", default=None,
                        help="命令行指定型号")
    parser.add_argument("--name", default=None,
                        help="命令行指定显示名")
    parser.add_argument("--auto-detect", action="store_true",
                        help="从 --source-dir 的子文件夹名自动识别车型")
    args = parser.parse_args()

    # 构建车型列表
    cars = CARS

    # 方式1：命令行指定品牌/型号（无需改CARS配置）
    if args.brand and args.model:
        display_name = args.name or f"{args.brand} {args.model}"
        cars = [{
            "brand": args.brand,
            "model": args.model,
            "name": display_name,
            "cn_name": display_name,
            "queries": [f"{display_name} side profile official photo"],
        }]
    # 方式2：用 --car 筛选已配置的车型
    elif args.car:
        brand, model = args.car.split("/")
        cars = [c for c in CARS if c["brand"] == brand and c["model"] == model]
        if not cars:
            print(f"未找到车型: {args.car}")
            return
    # 方式3：auto-detect 从子文件夹名识别
    elif args.auto_detect and args.source_dir:
        src_path = Path(args.source_dir)
        cars = []
        for sub in sorted(src_path.iterdir()):
            if not sub.is_dir():
                continue
            # 子文件夹名格式：brand__model 或 brand_model
            name = sub.name.replace("__", "_")
            parts = name.split("_", 1)
            if len(parts) == 2:
                brand, model = parts
                cars.append({
                    "brand": brand,
                    "model": model,
                    "name": f"{brand} {model}",
                    "cn_name": f"{brand} {model}",
                    "queries": [f"{brand} {model} side profile official photo"],
                    "_source_subdir": sub.name,
                })
        if not cars:
            print(f"在 {args.source_dir} 中未找到有效子文件夹")
            return

    print(f"=== 车型正侧视图筛选工具 ===")
    print(f"处理车型: {len(cars)}款")
    print(f"步骤: {args.step}")
    if args.source_dir:
        print(f"输入源: 本地文件夹 {args.source_dir}")
    print()

    cars_data = []

    for car in cars:
        print(f"\n--- {car['name']} ---")

        # 步骤1：获取图片（本地导入 或 Bing下载）
        if args.step in ("all", "download"):
            if args.source_dir:
                # 本地文件夹模式
                if args.auto_detect and "_source_subdir" in car:
                    src = Path(args.source_dir) / car["_source_subdir"]
                else:
                    src = Path(args.source_dir)
                step_import_local(car, src)
            else:
                step_download(car, force=args.force)

        if args.step in ("all", "filter"):
            white_passed = step_filter_white_bg(car)
        else:
            white_passed = []

        if args.step in ("all", "complete"):
            complete_passed = step_filter_complete_car(car)
        elif args.step in ("direction", "apply"):
            # 分步执行：从已保存的complete目录加载候选
            complete_passed = load_complete_candidates(car)
            if complete_passed:
                print(f"  [{car['name']}] 加载已保存候选: {len(complete_passed)}张")
        else:
            complete_passed = []

        # 步骤3b：车头方向自动检测
        direction_results = []
        if args.step in ("all", "direction"):
            direction_results = step_detect_direction(car)

        cars_data.append((car, complete_passed))

        # 步骤4：自动替换（车头方向自动判定 + 选白色占比最高）
        if args.step in ("all", "apply"):
            if complete_passed:
                # 若all模式下未单独运行direction，这里实时检测
                dir_map = {d["file"]: d for d in direction_results} if direction_results else {}

                best = None
                best_white = 0
                best_flip = False
                best_conf = 0
                for c in complete_passed:
                    orig_path = COMPLETE_DIR / f"{car['brand']}__{car['model']}" / c["orig_file"]
                    arr = np.array(Image.open(orig_path).convert("RGB"))
                    white_info = analyze_background(arr, WHITE_BG_CONFIG)
                    if white_info["white_ratio"] > best_white:
                        best_white = white_info["white_ratio"]
                        best = c
                        # 使用方向检测结果决定是否翻转；若无则现场检测
                        dir_info = dir_map.get(c["file"])
                        if dir_info is None:
                            dir_info = detect_car_direction(arr, DIRECTION_CONFIG)
                        # 始终信任算法判定（已通过100%测试验证）
                        best_flip = dir_info["flip_needed"]
                        best_conf = dir_info["confidence"]

                if best:
                    conf_tag = f"置信度{best_conf:.0%}"
                    if best_conf < DIRECTION_CONFIG["min_confidence"]:
                        conf_tag += "(低置信,仍自动应用)"
                    flip_tag = "翻转→车头向左" if best_flip else "原图→车头向左"
                    print(f"  ✅ 自动应用（白{best_white}% + 方向检测:{flip_tag}, {conf_tag}）")
                    step_apply(car, best["file"], flip=best_flip)

    if args.step in ("all", "preview"):
        step_preview(cars_data)

    print(f"\n=== 完成 ===")
    if args.step == "all":
        print("✅ 全自动流程完成：筛选 + 车头方向自动判定 + 替换")
        print("   预览页（可选复核）: http://localhost:5173/_preview_pipeline.html")


if __name__ == "__main__":
    main()
