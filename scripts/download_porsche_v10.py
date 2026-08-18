#!/usr/bin/env python3
"""
v10: 从 Porsche newsroom (newsroom.porsche.com) 下载5款车的正侧视官图
方法论：
1. newsroom.porsche.com/en/model/{model}.html 已确认 404，改用press release页面
2. press release 页面是静态HTML，包含 /dam/{path}/jcr:content/{filename} 形式的图片URL
3. 直接访问 https://newsroom.porsche.com/dam/{path}/jcr:content/{filename} 返回原图
4. 排除改装品牌 (manthey) 和错误变体 (sport-turismo / gt3 / gt2 / turbo-s / gt3-rs)
5. 选择宽高比最接近 1.6-2.0（侧视图）的候选
"""
import os, re, json, time, hashlib, ssl, socket, urllib.request, urllib.parse, io
from pathlib import Path

# === 配置 ===
BASE = Path(r"d:\API\Evolution-Ai.Design\public\brands\porsche")
LOG_PATH = Path(r"d:\API\Evolution-Ai.Design\scripts\_porsche_v10_log.json")
TIMEOUT = 20
MAX_IMG_BYTES = 30 * 1024 * 1024  # 30MB 上限，防止下载超大文件
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# 全局socket超时（防止挂起）
socket.setdefaulttimeout(TIMEOUT)

# 改装品牌黑名单（URL中包含即排除）
TUNER_BLACKLIST = ["manthey", "mansory", "techart", "gemballa", "ruff", "novitec"]

# 错误变体黑名单（按车型）
WRONG_VARIANT = {
    "panamera": ["sport-turismo", "sport_turismo"],
    "911": ["gt3", "gt2", "turbo-s", "turbo_s", "gt3-rs", "gt3_rs", "gt3rs"],
}

# 5款车型配置 - 每个车型多个候选URL（press release 页面）
# 这些URL通过 WebSearch 在 newsroom.porsche.com 上找到
CARS = [
    {
        "model": "911",
        "urls": [
            # 2024 911 world premiere (含标准 Carrera)
            "https://newsroom.porsche.com/es_ES/producto/2024/porsche-nuevo-911-estreno-mundial-36325.html",
            # 911 Carrera GTS T-Hybrid press release（同页含 Carrera）
            "https://newsroom.porsche.com/en/2024/products/porsche-911-carrera-gts-t-hybrid-37359.html",
            # 911 Carrera T (2024)
            "https://newsroom.porsche.com/de/2024/produkte/porsche-der-neue-911-carrera-t-coupe-und-cabriolet-37682.html",
            # 911 Carrera 4S (2025)
            "https://newsroom.porsche.com/fr_CH/2025/products/porsche-911-carrera-targa-4s-transmission-integrale-39928.html",
            # 911 Carrera S (2025)
            "https://newsroom.porsche.com/fr_CH/2025/products/porsche-911-carrera-s-and-cabriolet-38319.html",
        ],
        "keywords": ["911", "carrera"],
    },
    {
        "model": "taycan",
        "urls": [
            # Taycan Turbo GT (2024)
            "https://newsroom.porsche.com/en/2024/products/porsche-the-new-taycan-turbo-gt-35479.html",
            # Taycan 2nd generation (2024)
            "https://newsroom.porsche.com/en/2024/products/porsche-rounds-off-second-taycan-generation-37832.html",
            # Taycan model year update (2026)
            "https://newsroom.porsche.com/en_PAP/2026/products/new-innovations-for-taycan-model-year-update-42861.html",
            # Taycan press kit
            "https://newsroom.porsche.com/en/press-kits/taycan.html",
            "https://newsroom.porsche.com/en/press-kits/taycan/Highlights.html",
        ],
        "keywords": ["taycan"],
    },
    {
        "model": "panamera",
        "urls": [
            # Australian product highlights (含完整车型图集)
            "https://newsroom.porsche.com/en_AU/2024/products/porsche-panamera-product-highlights-36377.html",
            # German Turbo S E-Hybrid / GTS press release (含车型官图)
            "https://newsroom.porsche.com/de/2024/produkte/porsche-panamera-turbo-s-e-hybrid-und-panamera-gts-36863.html",
            # Qatar launch (regional press release)
            "https://newsroom.porsche.com/en_PME/2024/products/porsche-qatar-launches-the-panamera.html",
            # India launch
            "https://newsroom.porsche.com/en_PME/2024/products/porsche-india-launches-the-2024-panamera.html",
            # 3rd generation Panamera (sedan, 2024) - launch press release
            "https://newsroom.porsche.com/en/2024/products/porsche-the-new-panamera-37194.html",
            "https://newsroom.porsche.com/en_PME/2024/products/the-new-porsche-panamera.html",
            # Panamera press kit (English)
            "https://newsroom.porsche.com/en/press-kits/panamera/summary.html",
        ],
        "keywords": ["panamera"],
    },
    {
        "model": "cayenne",
        "urls": [
            # 2023 Cayenne 3rd gen world premiere (Auto Shanghai)
            "https://newsroom.porsche.com/en/2023/products/porsche-cayenne-world-premiere-auto-shanghai-31953.html",
            # 2024 Cayenne GTS (V8)
            "https://newsroom.porsche.com/en_PME/2024/products/porsche-the-new-cayenne-gts-models-35917.html",
            # 2023 Cayenne Turbo E-Hybrid
            "https://newsroom.porsche.com/en/2023/products/porsche-cayenne-turbo-e-hybrid-models-33580.html",
            # 2023 Cayenne S E-Hybrid
            "https://newsroom.porsche.com/en/2023/products/porsche-the-new-cayenne-s-e-hybrid-33885.html",
            # Cayenne press kit
            "https://newsroom.porsche.com/en/press-kits/cayenne.html",
        ],
        "keywords": ["cayenne"],
    },
    {
        "model": "macan",
        "urls": [
            # Macan Electric world premiere (2024) - 主URL
            "https://newsroom.porsche.com/en/2024/products/porsche-the-all-electric-macan-35086.html",
            # Macan 4 Electric
            "https://newsroom.porsche.com/en/2024/products/porsche-macan-4-electric-35086.html",
            # Macan Turbo Electric
            "https://newsroom.porsche.com/en/2024/products/porsche-macan-turbo-electric-35087.html",
            # Macan press kit (electric, 2nd gen)
            "https://newsroom.porsche.com/en/press-kits/the-new-porsche-macan/Kurzfassung.html",
            "https://newsroom.porsche.com/en/press-kits/the-new-porsche-macan/Highlights.html",
        ],
        "keywords": ["macan"],
    },
]


def clean_url(u):
    """清理URL中的控制字符和尾部多余字符"""
    u = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', u)
    u = re.sub(r'[,\s]+$', '', u)
    return u.strip()


def is_blacklisted(url_lower, model):
    """检查URL是否在黑名单中（改装品牌/错误变体）"""
    for t in TUNER_BLACKLIST:
        if t in url_lower:
            return f"tuner:{t}"
    wrong = WRONG_VARIANT.get(model, [])
    for w in wrong:
        if w in url_lower:
            return f"wrong_variant:{w}"
    return None


def fetch_html(url):
    """获取页面HTML"""
    url = clean_url(url)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            data = resp.read()
            enc = resp.headers.get_content_charset() or "utf-8"
            try:
                html = data.decode(enc, errors="replace")
            except Exception:
                html = data.decode("utf-8", errors="replace")
            return html, resp.url, None
    except Exception as e:
        return None, url, str(e)


def extract_image_urls(html, base_url):
    """从HTML中提取所有 porsche.com 域名的图片URL（绝对+相对）"""
    if not html:
        return []

    base = urllib.parse.urlparse(base_url)
    base_host = f"{base.scheme}://{base.netloc}"

    all_urls = set()

    # 1. 绝对URL https://...porsche.com/...jpg
    abs_urls = re.findall(r'https?://[^\s"\'<>\\]+?\.(?:jpg|jpeg|png)', html, re.I)
    for u in abs_urls:
        url = clean_url(u)
        if url.startswith("//"):
            url = "https:" + url
        all_urls.add(url)

    # 2. 相对URL /dam/.../jcr:content/...jpg （原图直链）
    dam_urls = re.findall(r'(/dam/[^\s"\'<>\\]+\.(?:jpg|jpeg|png))', html, re.I)
    for ru in dam_urls:
        url = clean_url(ru)
        all_urls.add(f"{base_host}{url}")

    # 3. imaging URL /.imaging/mte/.../dam/.../jcr:content/...jpg
    #    这些是缩略图URL，但同页面通常有对应的 /dam/ 原图URL
    imaging_urls = re.findall(r'(/\.imaging/[^\s"\'<>\\]+\.(?:jpg|jpeg|png))', html, re.I)
    for iu in imaging_urls:
        # 从 /.imaging/mte/{theme}/{size}/dam/{path}/jcr:content/{filename}
        # 提取 /dam/{path}/jcr:content/{filename} 原图URL
        m = re.search(r'/dam/(/.+?/jcr:content/[^/]+\.(?:jpg|jpeg|png))', iu, re.I)
        if m:
            original_path = m.group(1)
            all_urls.add(f"{base_host}{original_path}")

    # 过滤：只要 porsche.com 域名
    filtered = []
    for u in all_urls:
        url_lower = u.lower()
        # 排除常见非内容图片（图标/按钮/logo等）
        if any(x in url_lower for x in [
            "icon", "logo", "favicon", "sprite", "blank", "pixel", "tracking",
            "1x1", "placeholder", "loader", "spinner", "social", "share",
            "arrow", "menu", "btn", "button", "badge", "flag",
            "autorenbilder", "pressesprecher",  # 作者头像
            "teaser", "/image/teaser_",  # 通用teaser缩略图（容易跨车型重复）
            # 技术细节图（不是整车外观图）
            "engine", "motor", "%20motor", "susp", "suspension",
            "matrix%20led", "matrix_led", "matrixled", "headlight", "taillight",
            "tail-light", "transmission", "getriebe", "battery", "batterie",
            "hv%20system", "hv_system", "hvs", "high%20voltage", "high_voltage",
            "burmester", "bose", "%20air%20susp", "airbag", "wheel%20arch",
            "interior%20detail", "cockpit%20detail", "brake%20caliper",
            "exhaust", "auspuff", "seat%20detail", "door%20panel",
        ]):
            continue
        # 只要 porsche.com 域名的
        if "porsche.com" in url_lower:
            filtered.append(u)

    # 去重保持顺序
    seen = set()
    unique = []
    for u in filtered:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    return unique


def download_image(url):
    """下载图片，返回 (data, error)。分块读取，带超时和大小上限。"""
    url = clean_url(url)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://newsroom.porsche.com/",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            # 先读前4字节判断是否是图片
            head = resp.read(4)
            if len(head) < 4:
                return None, "too_small_head"
            is_jpeg = head[:2] == b'\xff\xd8'
            is_png = head[:4] == b'\x89PNG'
            is_webp = head[:4] == b'RIFF'
            if not (is_jpeg or is_png or is_webp):
                return None, f"not_image:{head.hex()}"
            # 分块读取剩余数据，防止挂起和超大文件
            chunks = [head]
            total = len(head)
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_IMG_BYTES:
                    return None, f"too_large:{total}"
            data = b''.join(chunks)
            if len(data) < 5000:
                return None, "too_small"
            return data, None
    except socket.timeout:
        return None, "socket_timeout"
    except Exception as e:
        return None, str(e)


def get_image_size(data):
    """从图片数据获取宽高"""
    if not data:
        return 0, 0
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        return img.size
    except Exception:
        return 0, 0


def score_candidate(c):
    """打分：宽高比越接近1.8越好（侧视图），尺寸越大越好"""
    asp = c["asp"]
    # 侧视图最佳比例 1.6-2.0，理想 1.8
    if 1.6 <= asp <= 2.0:
        asp_score = 100 - abs(asp - 1.8) * 30
    elif 1.4 <= asp < 1.6:
        asp_score = 50 - (1.6 - asp) * 50  # 接近但仍偏低
    elif 2.0 < asp <= 2.5:
        asp_score = 50 - (asp - 2.0) * 50
    else:
        asp_score = 0
    size_score = min(c["kb"] / 200, 30)  # 越大越好，封顶30分
    return asp_score + size_score


def process_car(car):
    """处理一款车型"""
    model = car["model"]
    print(f"\n{'='*60}")
    print(f"处理: porsche/{model}")
    print(f"{'='*60}")

    BASE.mkdir(parents=True, exist_ok=True)
    save_path = BASE / f"{model}.jpg"

    all_img_urls = []

    # 1. 尝试每个URL
    for url in car["urls"]:
        print(f"\n  访问: {url}")
        html, final_url, err = fetch_html(url)
        if err:
            print(f"    失败: {err}")
            continue
        print(f"    HTML长度: {len(html)} 字符")

        imgs = extract_image_urls(html, final_url)
        print(f"    提取到 {len(imgs)} 个 porsche.com 图片URL")

        for img_url in imgs:
            url_lower = img_url.lower()
            bl = is_blacklisted(url_lower, model)
            if bl:
                print(f"    跳过(黑名单:{bl}): {img_url[:80]}")
                continue
            all_img_urls.append(img_url)

    if not all_img_urls:
        print(f"\n  未找到任何图片URL!")
        return {"model": model, "status": "no_urls", "candidates": [],
                "urls_tried": car["urls"]}

    # 去重
    seen = set()
    unique_urls = []
    for u in all_img_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
    print(f"\n  去重后 {len(unique_urls)} 个候选URL")

    # 2. 下载候选图片
    candidates = []
    for i, img_url in enumerate(unique_urls[:50]):  # 最多试50个
        print(f"\n  [{i+1}/{min(len(unique_urls),50)}] 下载: {img_url[:90]}...")

        data, err = download_image(img_url)
        if data is None:
            print(f"    失败: {err}")
            continue

        w, h = get_image_size(data)
        size_kb = len(data) // 1024
        md5 = hashlib.md5(data).hexdigest()[:12]
        asp = w / h if h > 0 else 0

        print(f"    尺寸: {w}x{h}, 比例: {asp:.2f}, 大小: {size_kb}KB, MD5: {md5}")

        # 质量检查
        if w < 600 or h < 300:
            print(f"    跳过: 尺寸太小 (<600x300)")
            continue
        if size_kb < 20:
            print(f"    跳过: 文件太小 (<20KB)")
            continue

        candidates.append({
            "url": img_url,
            "w": w, "h": h, "asp": round(asp, 2),
            "kb": size_kb, "md5": md5,
        })

    if not candidates:
        print(f"\n  无合格候选!")
        return {"model": model, "status": "no_candidates", "candidates": [],
                "urls_tried": car["urls"]}

    # 3. 选择最佳候选
    candidates.sort(key=score_candidate, reverse=True)

    print(f"\n  最佳候选 Top 5:")
    for c in candidates[:5]:
        print(f"    {c['w']}x{c['h']} asp={c['asp']} {c['kb']}KB "
              f"score={score_candidate(c):.1f} {c['url'][:80]}")

    best = candidates[0]
    # 重新下载最佳候选并保存
    data, err = download_image(best["url"])
    if data:
        with open(save_path, "wb") as f:
            f.write(data)
        print(f"\n  已保存: {save_path}")
        return {
            "model": model, "status": "ok",
            "url": best["url"], "w": best["w"], "h": best["h"],
            "asp": best["asp"], "kb": best["kb"], "md5": best["md5"],
            "save_path": str(save_path),
            "all_candidates": candidates[:10],
            "urls_tried": car["urls"],
        }
    else:
        print(f"\n  保存失败: {err}")
        return {"model": model, "status": "save_failed",
                "candidates": candidates[:10], "urls_tried": car["urls"]}


def main():
    import sys
    # 可选 CLI 参数：--only panamera  只处理指定车型
    only_models = []
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        if idx + 1 < len(sys.argv):
            only_models = [m.strip().lower() for m in sys.argv[idx + 1].split(",")]
    print("=" * 60)
    print("v10 Porsche newsroom 正侧视官图下载器")
    print("方法论：press release页面 + /dam/原图直链 + 黑名单过滤")
    if only_models:
        print(f"过滤: 只处理 {only_models}")
    print("=" * 60)

    # 加载已有日志（如存在），用于增量更新
    existing_results = []
    if LOG_PATH.exists():
        try:
            existing_results = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing_results = []
    existing_by_model = {r["model"]: r for r in existing_results if r.get("status") == "ok"}

    results = []
    for car in CARS:
        if only_models and car["model"].lower() not in only_models:
            # 复用已有结果
            if car["model"] in existing_by_model:
                results.append(existing_by_model[car["model"]])
            continue
        try:
            result = process_car(car)
        except Exception as e:
            print(f"\n  异常: {e}")
            result = {"model": car["model"], "status": f"error:{e}",
                      "candidates": [], "urls_tried": car["urls"]}
        results.append(result)
        # 实时保存日志（每次处理后都保存，防止中断丢失）
        LOG_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        time.sleep(1)

    # 最终保存日志（确保从existing加载的车型也写入日志）
    LOG_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    # 汇总
    print(f"\n\n{'='*60}")
    print(f"日志已保存: {LOG_PATH}")
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n汇总: {ok}/5 成功")
    for r in results:
        icon = "OK" if r["status"] == "ok" else "FAIL"
        if r["status"] == "ok":
            print(f"  [{icon}] porsche/{r['model']}: "
                  f"{r['w']}x{r['h']} {r['kb']}KB asp={r['asp']} "
                  f"{r['url'][:80]}")
        else:
            print(f"  [{icon}] porsche/{r['model']}: {r['status']}")


if __name__ == "__main__":
    main()
