#!/usr/bin/env python3
"""
v9: 从各品牌官网媒体库下载19款车型的正侧视官图
方法论纠正：
1. 唯一来源 = 各品牌官网/新闻中心（非壁纸站）
2. 排除改装品牌（Mansory/Novitec/Techart/SPOFEC/Manthey）
3. 排除错误变体（Sport Turismo/SF90 XX/Chiron Profilee等）
4. 下载后必须人工视觉验证
"""
import os, re, json, time, hashlib, ssl, urllib.request, urllib.parse
from pathlib import Path

# === 配置 ===
BASE = Path(r"d:\API\Evolution-Ai.Design\public\brands")
LOG_PATH = Path(r"d:\API\Evolution-Ai.Design\scripts\_official_download_log.json")
TIMEOUT = 20
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# 改装品牌黑名单
TUNER_BLACKLIST = ["mansory", "novitec", "techart", "spofec", "manthey", "brabus",
                   "carlsson", "lorinser", "abt", "mtm", "gemballa", "ruff", "edo",
                   "mulliner", "bacalar", "profilee", "sport-turismo", "xx-stradale",
                   "xx stradale", "turismo"]

# 错误变体黑名单（按车型）
WRONG_VARIANT = {
    "continental-gtc": ["bacalar", "bentayga", "flying-spur", "continental-gt"],
    "divo": ["chiron-profilee", "chiron profilee", "chiron-sport", "chiron-pur",
             "chiron-super", "centodieci", "la-voiture", "mistral", "bolide",
             "tourbillon", "brouillard"],
    "panamera": ["sport-turismo", "techart"],
    "sf90": ["xx-stradale", "xx stradale", "assetto"],
    "911": ["gt3", "gt2", "turbo-s", "gt3-rs", "rwd", "carrera-gts"],
}

# 19款车型配置
# 每个车型配置：品牌目录、文件名、官方页面URL列表、品牌域名过滤
CARS = [
    # === Rolls-Royce (4) ===
    {
        "brand": "rolls-royce", "model": "phantom",
        "urls": [
            "https://www.rolls-roycemotorcars.com/en_GB/phantom.html",
            "https://www.rolls-roycemotorcars.com/en_GB/showroom/phantom.html",
        ],
        "brand_domains": ["rolls-roycemotorcars.com"],
        "keywords": ["phantom"],
    },
    {
        "brand": "rolls-royce", "model": "ghost",
        "urls": [
            "https://www.rolls-roycemotorcars.com/en_GB/ghost.html",
            "https://www.rolls-roycemotorcars.com/en_GB/showroom/ghost.html",
        ],
        "brand_domains": ["rolls-roycemotorcars.com"],
        "keywords": ["ghost"],
    },
    {
        "brand": "rolls-royce", "model": "cullinan",
        "urls": [
            "https://www.rolls-roycemotorcars.com/en_GB/cullinan.html",
            "https://www.rolls-roycemotorcars.com/en_GB/showroom/cullinan.html",
        ],
        "brand_domains": ["rolls-roycemotorcars.com"],
        "keywords": ["cullinan"],
    },
    {
        "brand": "rolls-royce", "model": "wraith",
        "urls": [
            "https://www.rolls-roycemotorcars.com/en_GB/wraith.html",
            "https://www.rolls-roycemotorcars.com/en_GB/showroom/wraith.html",
        ],
        "brand_domains": ["rolls-roycemotorcars.com"],
        "keywords": ["wraith"],
    },
    # === Bentley (4) ===
    {
        "brand": "bentley", "model": "continental-gt",
        "urls": [
            "https://www.bentleymotors.com/en/models/continental-gt/continental-gt.html",
        ],
        "brand_domains": ["bentleymotors.com", "cdn.bentleymotors.com"],
        "keywords": ["continental-gt", "continental_gt", "continentalgt"],
    },
    {
        "brand": "bentley", "model": "continental-gtc",
        "urls": [
            "https://www.bentleymotors.com/en/models/continental-gtc/continental-gtc.html",
            "https://www.bentleymotors.com/en/models/continental-gt/continental-gtc.html",
        ],
        "brand_domains": ["bentleymotors.com", "cdn.bentleymotors.com"],
        "keywords": ["continental-gtc", "continental_gtc", "gtc", "convertible"],
    },
    {
        "brand": "bentley", "model": "flying-spur",
        "urls": [
            "https://www.bentleymotors.com/en/models/flying-spur/flying-spur.html",
        ],
        "brand_domains": ["bentleymotors.com", "cdn.bentleymotors.com"],
        "keywords": ["flying-spur", "flying_spur", "flyingspur"],
    },
    {
        "brand": "bentley", "model": "bentayga",
        "urls": [
            "https://www.bentleymotors.com/en/models/bentayga/bentayga.html",
        ],
        "brand_domains": ["bentleymotors.com", "cdn.bentleymotors.com"],
        "keywords": ["bentayga"],
    },
    # === Bugatti (3) ===
    {
        "brand": "bugatti", "model": "chiron",
        "urls": [
            "https://newsroom.bugatti.com/models/chiron",
            "https://www.bugatti.com/models/chiron/",
        ],
        "brand_domains": ["bugatti.com", "newsroom.bugatti.com", "bugatti-newsroom.imgix.net"],
        "keywords": ["chiron"],
    },
    {
        "brand": "bugatti", "model": "veyron",
        "urls": [
            "https://newsroom.bugatti.com/models/veyron",
            "https://www.bugatti.com/models/veyron/",
        ],
        "brand_domains": ["bugatti.com", "newsroom.bugatti.com", "bugatti-newsroom.imgix.net"],
        "keywords": ["veyron"],
    },
    {
        "brand": "bugatti", "model": "divo",
        "urls": [
            "https://newsroom.bugatti.com/models/divo",
            "https://www.bugatti.com/models/divo/",
        ],
        "brand_domains": ["bugatti.com", "newsroom.bugatti.com", "bugatti-newsroom.imgix.net"],
        "keywords": ["divo"],
    },
    # === Porsche (5) ===
    {
        "brand": "porsche", "model": "911",
        "urls": [
            "https://newsroom.porsche.com/en/model/911.html",
            "https://www.porsche.com/international/models/911/",
        ],
        "brand_domains": ["porsche.com", "newsroom.porsche.com"],
        "keywords": ["911", "carrera"],
    },
    {
        "brand": "porsche", "model": "taycan",
        "urls": [
            "https://newsroom.porsche.com/en/model/taycan.html",
            "https://www.porsche.com/international/models/taycan/",
        ],
        "brand_domains": ["porsche.com", "newsroom.porsche.com"],
        "keywords": ["taycan"],
    },
    {
        "brand": "porsche", "model": "panamera",
        "urls": [
            "https://newsroom.porsche.com/en/model/panamera.html",
            "https://www.porsche.com/international/models/panamera/",
        ],
        "brand_domains": ["porsche.com", "newsroom.porsche.com"],
        "keywords": ["panamera"],
    },
    {
        "brand": "porsche", "model": "cayenne",
        "urls": [
            "https://newsroom.porsche.com/en/model/cayenne.html",
            "https://www.porsche.com/international/models/cayenne/",
        ],
        "brand_domains": ["porsche.com", "newsroom.porsche.com"],
        "keywords": ["cayenne"],
    },
    {
        "brand": "porsche", "model": "macan",
        "urls": [
            "https://newsroom.porsche.com/en/model/macan.html",
            "https://www.porsche.com/international/models/macan/",
        ],
        "brand_domains": ["porsche.com", "newsroom.porsche.com"],
        "keywords": ["macan"],
    },
    # === Ferrari (3) ===
    {
        "brand": "ferrari", "model": "sf90",
        "urls": [
            "https://www.ferrari.com/en-EN/auto/sf90-stradale",
            "https://www.ferrari.com/en-EN/models/sf90-stradale",
        ],
        "brand_domains": ["ferrari.com"],
        "keywords": ["sf90", "stradale"],
    },
    {
        "brand": "ferrari", "model": "f8-tributo",
        "urls": [
            "https://www.ferrari.com/en-EN/auto/f8-tributo",
            "https://www.ferrari.com/en-EN/models/f8-tributo",
        ],
        "brand_domains": ["ferrari.com"],
        "keywords": ["f8", "tributo"],
    },
    {
        "brand": "ferrari", "model": "roma",
        "urls": [
            "https://www.ferrari.com/en-EN/auto/roma",
            "https://www.ferrari.com/en-EN/models/roma",
        ],
        "brand_domains": ["ferrari.com"],
        "keywords": ["roma"],
    },
]

def clean_url(u):
    """清理URL中的控制字符"""
    u = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', u)
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
            # 尝试检测编码
            enc = resp.headers.get_content_charset() or "utf-8"
            try:
                html = data.decode(enc, errors="replace")
            except:
                html = data.decode("utf-8", errors="replace")
            final_url = resp.url
            return html, final_url, None
    except Exception as e:
        return None, url, str(e)

def extract_image_urls(html, base_url, brand_domains):
    """从HTML中提取所有图片URL，过滤品牌域名"""
    if not html:
        return []

    # 统一提取所有 https?:// 开头以图片扩展名结尾的URL
    # 这样可以同时处理 src, srcset, data-src, JSON, CSS 等各种场景
    raw_urls = re.findall(r'https?://[^\s"\'<>\\]+?\.(?:jpg|jpeg|png)', html, re.I)

    # 也提取相对路径的图片URL
    rel_urls = re.findall(r'src\s*=\s*["\'](/[^"\']+\.(?:jpg|jpeg|png))', html, re.I)
    base = urllib.parse.urlparse(base_url)
    for ru in rel_urls:
        full = f"{base.scheme}://{base.netloc}{ru}"
        raw_urls.append(full)

    all_urls = set()
    for u in raw_urls:
        url = clean_url(u)
        # 去掉URL末尾可能的多余字符
        url = re.sub(r'[,\s]+$', '', url)
        if url.startswith("//"):
            url = "https:" + url
        all_urls.add(url)

    # 过滤：只要品牌域名的图片
    filtered = []
    for u in all_urls:
        url_lower = u.lower()
        # 排除常见非内容图片
        if any(x in url_lower for x in ["icon", "logo", "favicon", "sprite",
                                         "blank", "pixel", "tracking", "doubaocdn",
                                         "1x1", "placeholder", "loader", "spinner",
                                         "social", "share", "arrow", "menu", "btn",
                                         "button", "badge", "flag"]):
            continue
        # 只要品牌域名的
        for domain in brand_domains:
            if domain in url_lower:
                filtered.append(u)
                break

    # 去重
    seen = set()
    unique = []
    for u in filtered:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    return unique

def download_image(url, save_path):
    """下载图片到本地"""
    url = clean_url(url)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": url,
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            data = resp.read()
            if len(data) < 5000:  # <5KB 太小，可能不是真图
                return None, "too_small"
            # 验证是JPEG
            if data[:2] == b'\xff\xd8' or data[:4] == b'\x89PNG' or data[:4] == b'RIFF':
                with open(save_path, "wb") as f:
                    f.write(data)
                md5 = hashlib.md5(data).hexdigest()[:12]
                return data, md5
            else:
                return None, f"not_image:{data[:4].hex()}"
    except Exception as e:
        return None, str(e)

def get_image_size(data):
    """从JPEG数据获取宽高"""
    if not data:
        return 0, 0
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        return img.size
    except:
        return 0, 0

def process_car(car):
    """处理一款车型"""
    brand = car["brand"]
    model = car["model"]
    print(f"\n{'='*60}")
    print(f"处理: {brand}/{model}")
    print(f"{'='*60}")
    
    save_dir = BASE / brand
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{model}.jpg"
    
    all_img_urls = []
    
    # 1. 尝试每个官方URL
    for url in car["urls"]:
        print(f"\n  访问: {url}")
        html, final_url, err = fetch_html(url)
        if err:
            print(f"    失败: {err}")
            continue
        print(f"    HTML长度: {len(html)} 字符")
        
        # 提取图片URL
        imgs = extract_image_urls(html, final_url, car["brand_domains"])
        print(f"    提取到 {len(imgs)} 个品牌域名图片URL")
        
        for img_url in imgs:
            url_lower = img_url.lower()
            # 检查黑名单
            bl = is_blacklisted(url_lower, model)
            if bl:
                print(f"    跳过(黑名单:{bl}): {img_url[:80]}")
                continue
            all_img_urls.append(img_url)
    
    if not all_img_urls:
        print(f"\n  未找到任何图片URL!")
        return {"brand": brand, "model": model, "status": "no_urls", "candidates": []}
    
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
    for i, img_url in enumerate(unique_urls[:30]):  # 最多试30个
        print(f"\n  [{i+1}/{min(len(unique_urls),30)}] 下载: {img_url[:80]}...")
        
        # 临时保存
        tmp_path = save_dir / f"_tmp_{model}_{i}.jpg"
        data, result = download_image(img_url, tmp_path)
        
        if data is None:
            print(f"    失败: {result}")
            if tmp_path.exists():
                tmp_path.unlink()
            continue
        
        w, h = get_image_size(data)
        size_kb = len(data) // 1024
        md5 = result  # download_image返回md5
        asp = w / h if h > 0 else 0
        
        print(f"    尺寸: {w}x{h}, 比例: {asp:.2f}, 大小: {size_kb}KB, MD5: {md5}")
        
        # 基本质量检查
        if w < 800 or h < 400:
            print(f"    跳过: 尺寸太小")
            if tmp_path.exists():
                tmp_path.unlink()
            continue
        if size_kb < 30:
            print(f"    跳过: 文件太小")
            if tmp_path.exists():
                tmp_path.unlink()
            continue
        
        candidates.append({
            "url": img_url,
            "w": w, "h": h, "asp": round(asp, 2),
            "kb": size_kb, "md5": md5,
            "file": str(tmp_path),
        })
        
        # 清理临时文件
        if tmp_path.exists():
            tmp_path.unlink()
    
    if not candidates:
        print(f"\n  无合格候选!")
        return {"brand": brand, "model": model, "status": "no_candidates", "candidates": []}
    
    # 3. 选择最佳候选（优先宽高比1.6-2.2的，即侧视图比例）
    def score(c):
        asp = c["asp"]
        # 侧视图最佳比例 1.6-2.2
        asp_score = 100 - abs(asp - 1.8) * 50 if 1.4 < asp < 2.5 else 0
        size_score = min(c["kb"] / 100, 50)  # 越大越好
        return asp_score + size_score
    
    candidates.sort(key=score, reverse=True)
    
    print(f"\n  最佳候选:")
    for c in candidates[:5]:
        print(f"    {c['w']}x{c['h']} asp={c['asp']} {c['kb']}KB score={score(c):.1f} {c['url'][:60]}")
    
    # 下载最佳候选为最终图片
    best = candidates[0]
    data, result = download_image(best["url"], save_path)
    
    if data:
        print(f"\n  已保存: {save_path}")
        return {
            "brand": brand, "model": model, "status": "ok",
            "url": best["url"], "w": best["w"], "h": best["h"],
            "asp": best["asp"], "kb": best["kb"], "md5": best["md5"],
            "save_path": str(save_path),
            "all_candidates": candidates[:5],
        }
    else:
        print(f"\n  保存失败: {result}")
        return {"brand": brand, "model": model, "status": "save_failed", "candidates": candidates[:5]}

def main():
    import sys
    # 直接重定向stdout到文件
    log_file = open(r"d:\API\Evolution-Ai.Design\scripts\_official_v9_output.txt", "w", encoding="utf-8")
    class Tee:
        def __init__(self, *files): self.files = files
        def write(self, s):
            for f in self.files: f.write(s); f.flush()
        def flush(self):
            for f in self.files: f.flush()
    sys.stdout = Tee(log_file, sys.__stdout__)

    print("=" * 60)
    print("v9 官网正侧视官图下载器")
    print("方法论：官网媒体库为唯一来源 + 排除改装/错误变体")
    print("=" * 60)

    results = []
    for car in CARS:
        try:
            result = process_car(car)
        except Exception as e:
            print(f"\n  异常: {e}")
            result = {"brand": car["brand"], "model": car["model"], "status": f"error:{e}", "candidates": []}
        results.append(result)
        # 实时保存日志
        LOG_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        time.sleep(2)  # 礼貌延迟
    
    # 保存日志
    LOG_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n\n{'='*60}")
    print(f"日志已保存: {LOG_PATH}")
    
    # 汇总
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n汇总: {ok}/19 成功")
    for r in results:
        status_icon = "OK" if r["status"] == "ok" else "FAIL"
        if r["status"] == "ok":
            print(f"  [{status_icon}] {r['brand']}/{r['model']}: {r['w']}x{r['h']} {r['kb']}KB {r['url'][:60]}")
        else:
            print(f"  [{status_icon}] {r['brand']}/{r['model']}: {r['status']}")

if __name__ == "__main__":
    main()
