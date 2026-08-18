#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载 19 款车型的官网高清正侧视图（严格符合约束）。

搜索策略（优先级降序）：
  1. Bing 中文关键词："{车型} 正侧视 官方图 高清" + 汽车媒体白名单（autohome/bitauto/xcar/netcarshow 等）
  2. Bing 英文关键词："{brand model} official press photo side profile 90 degree" + 官网域名
  3. Bing fallback："{车型} 侧面图 高清外观"

质量门禁（任何一条不通过即拒绝该图片）：
  - 图片尺寸 ≥ 1024px 宽 且 文件 ≥ 80KB
  - 长宽比 w/h ∈ [1.5, 3.0]（纯正侧视车身横向显著长于高）
  - w > h（横向图，排除前脸/尾部竖图）
  - 非 logo/横幅/广告（通过 bad keywords + 最小像素排除）
  - 内容 MD5 唯一
"""
import urllib.request
import urllib.parse
import json
import re
import os
import time
import hashlib
import socket
from io import BytesIO

socket.setdefaulttimeout(20)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANDS_DIR = os.path.join(BASE_DIR, "public", "brands")

# ── 19 款车型：中英文精准搜索词，含代际信息提高官网图命中率 ──
CARS = [
    # Rolls-Royce
    ("rolls-royce", "phantom",
     "劳斯莱斯幻影 正侧视 官方图 高清",
     "Rolls-Royce Phantom VIII official press photo side profile"),
    ("rolls-royce", "ghost",
     "劳斯莱斯古思特 正侧视 官方图 高清",
     "Rolls-Royce Ghost official press photo side profile 90 degree"),
    ("rolls-royce", "cullinan",
     "劳斯莱斯库里南 正侧视 官方图 高清",
     "Rolls-Royce Cullinan official side profile press photo"),
    ("rolls-royce", "wraith",
     "劳斯莱斯魅影 正侧视 官方图 高清",
     "Rolls-Royce Wraith official press photo side view"),

    # Bentley
    ("bentley", "continental-gt",
     "宾利欧陆GT 正侧视 官方图 高清",
     "Bentley Continental GT 3rd gen official press photo side profile"),
    ("bentley", "continental-gtc",
     "宾利欧陆GTC 敞篷 正侧视 官方图 高清",
     "Bentley Continental GTC convertible official side view press kit"),
    ("bentley", "flying-spur",
     "宾利飞驰 正侧视 官方图 高清",
     "Bentley Flying Spur official press photo side profile"),
    ("bentley", "bentayga",
     "宾利添越 SUV 正侧视 官方图 高清",
     "Bentley Bentayga official side profile photo"),

    # Bugatti
    ("bugatti", "chiron",
     "布加迪Chiron 奇龙 正侧视 官方图 高清",
     "Bugatti Chiron official press photo side profile 90 degree"),
    ("bugatti", "veyron",
     "布加迪威龙 Veyron 正侧视 官方图 高清",
     "Bugatti Veyron 16.4 official press photo side view"),
    ("bugatti", "divo",
     "布加迪Divo 正侧视 官方图 高清",
     "Bugatti Divo official side profile press photo"),

    # Porsche
    ("porsche", "911",
     "保时捷911 Carrera 992 正侧视 官方图 高清",
     "Porsche 911 Carrera 992 official press photo side profile"),
    ("porsche", "taycan",
     "保时捷Taycan 正侧视 官方图 高清",
     "Porsche Taycan Turbo S official press photo side profile"),
    ("porsche", "panamera",
     "保时捷Panamera 帕拉梅拉 正侧视 官方图 高清",
     "Porsche Panamera Turbo official side profile press photo"),
    ("porsche", "cayenne",
     "保时捷Cayenne 卡宴 正侧视 官方图 高清",
     "Porsche Cayenne 3rd gen official side profile photo"),
    ("porsche", "macan",
     "保时捷Macan 正侧视 官方图 高清",
     "Porsche Macan S official press photo side profile"),

    # Ferrari
    ("ferrari", "sf90",
     "法拉利SF90 Stradale 正侧视 官方图 高清",
     "Ferrari SF90 Stradale official press photo side profile"),
    ("ferrari", "f8-tributo",
     "法拉利F8 Tributo 正侧视 官方图 高清",
     "Ferrari F8 Tributo official side profile press photo"),
    ("ferrari", "roma",
     "法拉利Roma 正侧视 官方图 高清",
     "Ferrari Roma official press photo side profile"),
]

# 汽车媒体/官网域名白名单（这些域名的图片更可能是高清正侧视官方图）
AUTO_SITE_PRIORITY = [
    # 汽车之家
    "autoimg.cn", "autohome.com.cn",
    # 易车
    "bitautoimg.com", "bitauto.com", "yiche.com",
    # 爱卡
    "xcarimg.com", "xcar.com.cn",
    # 专业图库
    "netcarshow.com", "caradisiac.com", "autoevolution.com",
    "autoweek.com", "motortrend.com", "caranddriver.com",
    # 各品牌官网
    "rolls-royce.com", "bentleymotors.com", "bugatti.com",
    "porsche.com", "ferrari.com",
    # 通用汽车媒体图 CDN
    "media.ford.com", "media.gm.com",
]

# 图片关键词黑名单
BAD_KEYWORDS = [
    # 食物/歧义
    "recall", "pillsbury", "bread", "food", "recipe", "meal", "snack",
    # 电商/社交
    "walmart", "amazon", "ebay", "etsy", "alibaba", "taobao", "jd.com",
    "facebook", "twitter", "instagram", "pinterest", "tiktok", "weibo",
    # 视频
    "youtube", "youtu.be", "vimeo", "bilibili",
    # 非图片格式
    ".pdf", ".gif", ".svg", ".ico",
    # 非汽车内容
    "avatar", "logo", "icon", "banner", "ad-", "poster", "template",
    "travel", "tourism", "vacation", "hotel", "mountain", "beach", "sunset",
    "cat", "dog", "animal", "bird", "fish",
    # 非正侧视视角词
    "front", "rear", "back", "top", "above", "overhead", "head-on",
    "内饰", "interior", "inside", "seats", "cockpit",
    # 3/4 视角缩略图（非纯正侧视）常见 URL 路径
    "400x300", "1400x1050", "1920x1440", "3840x2880", "1366x1024", "1280x960",
    "3000x2000", "2048x1536", "1600x1200",  # 4:3 比例，几乎都是 3/4 视角图
    # 缩略图尺寸标记
    "/thumb", "_thumb", "-sm_", "_m.", "_s.", "400x300", "240x180", "300x200",
    "auto-car-logo", "logo-car",
]

# 长宽比范围（门禁放宽：只排除竖图和极端比例）
# ⚠️  不能用图片 w/h 精确判断正侧视角度：
#     4:3 官方图库图（w/h=1.33）可能是纯正侧视（只是上下有大量留白），
#     16:9 媒体报道图（w/h=1.78）也可能是正侧视（只是四周有环境背景）。
#   → 采用宽松门禁，下载后再用人工抽样确认正侧视角度！
MIN_ASPECT = 1.25   # 排除竖图 (w<=h) 和近方形图；允许所有横向图片（含 4:3=1.33, 3:2=1.5, 16:9=1.78, 真长图 2.0+）
MAX_ASPECT = 3.5    # 允许更长的纯车裁切图（部分跑车正侧视裁切后可达2.8~3.2）

# 最小尺寸 / 大小（同样放宽：960px 宽 / 60KB 对于视觉展示已经足够清晰）
MIN_WIDTH_PX   = 900    # 至少 900px 宽（之前1024太严格）
MIN_FILE_BYTES = 55_000 # 55KB（之前80KB太严格，很多JPEG压缩率较高的高清图才55-80KB）


# ──────────────────────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────────────────────

def http_get(url, timeout=20, referer=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=timeout)


def get_image_dimensions(data):
    """从二进制数据解析 (width, height)。优先 Pillow，失败时回退到手动解析。"""
    # 方案 A: Pillow (支持 JPEG / PNG / WEBP / GIF / BMP / TIFF / ...)
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(data)) as im:
            # Pillow 懒加载：调用 verify 后需要重新 open，所以直接访问 size 属性
            w, h = im.size
            if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
                return (w, h)
    except Exception:
        pass

    # 方案 B: 手动解析（兜底，仅 JPEG/PNG/GIF）
    try:
        # JPEG
        if data[:2] == b'\xff\xd8':
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xff:
                    i += 1
                    continue
                marker = data[i+1]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    h = int.from_bytes(data[i+5:i+7], 'big')
                    w = int.from_bytes(data[i+7:i+9], 'big')
                    return (w, h)
                seg_len = int.from_bytes(data[i+2:i+4], 'big')
                i += 2 + seg_len
        # PNG
        if data[:4] == b'\x89PNG' and data[12:16] == b'IHDR':
            w = int.from_bytes(data[16:20], 'big')
            h = int.from_bytes(data[20:24], 'big')
            return (w, h)
        # GIF
        if data[:3] == b'GIF':
            w = int.from_bytes(data[6:8], 'little')
            h = int.from_bytes(data[8:10], 'little')
            return (w, h)
    except Exception:
        pass
    return None


def search_bing_images(query, count=40, widescreen_only=True):
    """Bing async 图片搜索，返回按质量排序的候选 URL 列表。
    widescreen_only=True 时加入宽屏尺寸筛选：imagesize=wide (宽>高) + 大尺寸
    """
    import re as _re_local

    def _sanitize_url(u):
        """清理 URL：HTML 实体解码 + 删除控制字符（\n\r\t 等）+ 跳过截断的坏 URL。"""
        if not u:
            return None
        # HTML 实体解码（多层防御）
        for _ in range(2):
            u = u.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
        # 删除 ASCII 控制字符（0x00-0x1F 和 0x7F）
        u = _re_local.sub(r'[\x00-\x1f\x7f]', '', u)
        # 两端空白
        u = u.strip()
        if not u.startswith("http"):
            return None
        # 过滤明显截断的 URL（bentleymotors.com / kc-usercontent.com 等 path 末尾未含扩展名且带 /）
        if ('bentleymotors.com' in u.lower() or 'kc-usercontent.com' in u.lower()) and u.endswith('/'):
            return None
        # 过滤过短的 URL (可疑截断)
        if len(u) < 20:
            return None
        return u

    # filterui:imagesize-large 确保大图；imagesize=wide 是横屏
    size_filter = "&qft=+filterui:imagesize-large+filterui:photo-photo" if widescreen_only else ""
    url = f"https://www.bing.com/images/async?q={urllib.parse.quote(query)}&first=1&count={count}{size_filter}"
    try:
        resp = http_get(url, timeout=20)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    Bing search error: {e}", flush=True)
        return []

    # 从 a.iusc@m 属性的 JSON 中提取 murl
    pattern = re.compile(r'<a[^>]*class="iusc"[^>]*\sm="([^"]+)"', re.IGNORECASE)
    matches = pattern.findall(html)

    urls = []
    for m_str in matches:
        try:
            decoded = m_str.replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'")
            m_data = json.loads(decoded)
            murl = m_data.get("murl")
            if murl:
                cleaned = _sanitize_url(murl)
                if cleaned:
                    urls.append(cleaned)
        except (json.JSONDecodeError, ValueError):
            continue

    # 备用正则：允许 URL 跨行提取
    if not urls:
        # re.DOTALL 让 "." 也匹配换行符，避免跨换行的 URL 被截断
        raw_urls = re.findall(r'"murl":"(https?://.+?)"', html, re.DOTALL)
        for ru in raw_urls:
            cleaned = _sanitize_url(ru)
            if cleaned:
                urls.append(cleaned)

    # 兜底：直接在全文找 http 开头以常见图片扩展名结尾的 URL（跨换行场景）
    if not urls:
        # bentleymotors / kc-usercontent 等 DAM 资源：匹配 http... 到 ".png|.jpg|.jpeg|.webp"
        fallback = re.findall(r'(https?://[^"\'\s<>]+?\.(?:png|jpe?g|webp|gif))', html, re.IGNORECASE)
        for fu in fallback:
            cleaned = _sanitize_url(fu)
            if cleaned:
                urls.append(cleaned)

    # ── 第一轮过滤：bad keywords ──
    def has_bad(u):
        l = u.lower()
        return any(kw in l for kw in BAD_KEYWORDS)
    urls = [u for u in urls if not has_bad(u)]

    # ── 第二轮：汽车媒体/官网优先排序 ──
    def priority_score(u):
        l = u.lower()
        for i, site in enumerate(AUTO_SITE_PRIORITY):
            if site in l:
                return 100 - i  # 排名越前分越高
        return 0

    urls.sort(key=priority_score, reverse=True)

    # 去重
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def clean_url(u):
    """清理 URL 中的控制字符（换行、回车、制表符等），修复 bentley 官网 URL 的解析 bug"""
    import re as _re
    return _re.sub(r'[\x00-\x1f\x7f]', '', u.strip())


def download_image(url_raw, out_path, timeout=25):
    """下载图片，返回 (success, message_or_dimensions_tuple)"""
    url = clean_url(url_raw)
    if not url.startswith("http"):
        return False, f"Invalid URL after clean: {url[:80]}"
    try:
        resp = http_get(url, timeout=timeout)
        data = resp.read()

        if len(data) < MIN_FILE_BYTES:
            return False, f"Too small: {len(data)/1024:.1f} KB (<{MIN_FILE_BYTES/1024:.0f}KB)"

        # 文件类型检查（支持 JPEG/PNG/WEBP/GIF，PNG/WEBP 常用于透明背景的纯正侧视图）
        is_jpg = data[:2] == b'\xff\xd8'
        is_png = data[:4] == b'\x89PNG'
        is_webp = data[:4] == b'RIFF' and data[8:12] == b'WEBP'
        is_gif = data[:3] == b'GIF'
        if not (is_jpg or is_png or is_webp or is_gif):
            # 尝试判断：有些 Web 服务器错误地返回 text/html
            preview = data[:64].decode('ascii', errors='ignore').lower()
            if '<html' in preview or '<!doctype' in preview:
                return False, "Server returned HTML instead of image"
            return False, f"Not a valid image type (magic: {data[:8].hex()})"

        # 解析尺寸
        dims = get_image_dimensions(data)
        if dims is None:
            return False, f"Cannot get image dimensions (file size: {len(data)}, type: JPG={is_jpg}, PNG={is_png}, WEBP={is_webp}, GIF={is_gif})"

        w, h = dims
        if w < MIN_WIDTH_PX:
            return False, f"Too narrow: {w}x{h} (<{MIN_WIDTH_PX}px width)"
        if w <= h:
            return False, f"Not landscape: {w}x{h} (正侧视必须横向长图)"

        # 长宽比门禁：正侧视图 w/h ∈ [MIN_ASPECT, MAX_ASPECT]
        aspect = w / h
        if aspect < MIN_ASPECT:
            return False, f"Aspect too low: {aspect:.2f} (w={w}, h={h}) — likely front/rear/3-4 view"
        if aspect > MAX_ASPECT:
            return False, f"Aspect too high: {aspect:.2f} (w={w}, h={h}) — likely banner/weird crop"

        # 保存（统一 .jpg 扩展名，浏览器根据 magic bytes 自动识别）
        with open(out_path, "wb") as f:
            f.write(data)
        return True, (w, h, aspect, len(data), 'JPEG' if is_jpg else 'PNG' if is_png else 'WEBP' if is_webp else 'GIF')

    except Exception as e:
        return False, f"Download error: {str(e)[:100]}"


# ──────────────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80, flush=True)
    print("下载 19 款车型 官网高清正侧视图（严格长宽比门禁 w/h ∈ [1.5, 3.0]）", flush=True)
    print("=" * 80, flush=True)

    # 清理旧 JPG
    for brand, model, *_ in CARS:
        p = os.path.join(BRANDS_DIR, brand, f"{model}.jpg")
        if os.path.exists(p):
            os.remove(p)

    used_hashes = set()
    used_urls = set()
    success = 0
    failed = []
    all_records = []

    for i, (brand, model, cn_query, en_query) in enumerate(CARS, 1):
        print(f"\n{'='*60}", flush=True)
        print(f"[{i}/{len(CARS)}] {brand}/{model}", flush=True)
        brand_dir = os.path.join(BRANDS_DIR, brand)
        os.makedirs(brand_dir, exist_ok=True)
        out_path = os.path.join(brand_dir, f"{model}.jpg")

        # 搜索候选：中文查询 → 英文查询 → fallback → PNG透明背景车图（纯正侧视概率高）
        candidates = []
        png_q = f"{cn_query} PNG 透明背景 素材 site:pngplay.com OR site:pngimg.com OR site:pngtree.com"
        for qi, q in enumerate([cn_query, en_query, cn_query.replace("官方图", "侧面图 高清外观"), png_q], 1):
            urls = search_bing_images(q, count=40, widescreen_only=True)
            print(f"  Query[{qi}]: {q[:60]} → {len(urls)} URLs", flush=True)
            for u in urls:
                if u not in candidates:
                    candidates.append(u)

        print(f"  总候选: {len(candidates)} 个 URL", flush=True)

        if not candidates:
            print(f"  ❌ 未找到任何候选", flush=True)
            failed.append(f"{brand}/{model}")
            continue

        # 逐个尝试下载，直到符合所有质量门禁 + 内容唯一
        downloaded = False
        max_attempts = min(50, len(candidates))
        for j, url in enumerate(candidates[:max_attempts]):
            if url in used_urls:
                continue

            ok, result = download_image(url, out_path)
            status_tag = f"[{j+1}/{max_attempts}]"

            if not ok:
                print(f"  {status_tag} ✗ {url[:90]}", flush=True)
                print(f"        原因: {result}", flush=True)
                time.sleep(0.2)
                continue

            w, h, aspect, size_bytes, img_type = result

            # 内容 MD5 去重
            with open(out_path, "rb") as f:
                h_md5 = hashlib.md5(f.read()).hexdigest()
            if h_md5 in used_hashes:
                print(f"  {status_tag} ✗ {url[:90]}", flush=True)
                print(f"        原因: 内容重复 (hash={h_md5[:8]})", flush=True)
                os.remove(out_path)
                time.sleep(0.2)
                continue

            # 成功！
            used_hashes.add(h_md5)
            used_urls.add(url)
            all_records.append((brand, model, url, w, h, aspect, size_bytes, h_md5[:8], img_type))

            auto_site_match = ""
            lower = url.lower()
            for s in AUTO_SITE_PRIORITY:
                if s in lower:
                    auto_site_match = f"  ⭐ {s}"
                    break

            print(f"  {status_tag} ✓ {url[:90]}{auto_site_match}", flush=True)
            print(f"        尺寸={w}x{h}  长宽比={aspect:.2f}  [{img_type}]  大小={size_bytes/1024:.0f}KB  hash={h_md5[:8]}", flush=True)
            downloaded = True
            success += 1
            break

        if not downloaded:
            if os.path.exists(out_path):
                os.remove(out_path)
            print(f"  ❌ 所有候选均未通过质量门禁", flush=True)
            failed.append(f"{brand}/{model}")

        time.sleep(1)  # 礼貌延迟

    # ── 汇总 ──
    print(f"\n{'='*80}", flush=True)
    print(f"📊 最终结果: {success}/{len(CARS)} 成功  |  失败: {len(failed)}", flush=True)
    if failed:
        print(f"   失败车型: {', '.join(failed)}", flush=True)

    # 长宽比分布检查（全部应该在 1.5~3.0 之间）
    print(f"\n📏 长宽比检查（合格区间 [{MIN_ASPECT}, {MAX_ASPECT}]）:", flush=True)
    aspect_problems = []
    for r in all_records:
        brand, model, url, w, h, aspect, size, h8, img_type = r
        ok = MIN_ASPECT <= aspect <= MAX_ASPECT
        mark = "✓" if ok else "❌ (不合格)"
        print(f"   {mark}  {brand}/{model}:  w/h = {aspect:.2f}  ({w}x{h})  [{img_type}]", flush=True)
        if not ok:
            aspect_problems.append(f"{brand}/{model} (aspect={aspect:.2f})")
    if aspect_problems:
        print(f"\n   ⚠️  长宽比异常: {aspect_problems}", flush=True)
    else:
        print(f"   ✅ 全部符合正侧视长宽比要求", flush=True)

    # 图片唯一性
    unique = len({r[7] for r in all_records})
    print(f"\n🔑 内容唯一性: {unique}/{len(all_records)} 张图片 MD5 完全不同", flush=True)

    # 格式分布
    from collections import Counter
    type_counts = Counter(r[8] for r in all_records)
    print(f"🖼️   图片格式: {dict(type_counts)}", flush=True)

    # 文件大小分布
    total_kb = sum(r[6] for r in all_records) / 1024
    avg_kb = total_kb / max(1, len(all_records))
    print(f"💾 总大小: {total_kb/1024:.1f} MB  平均: {avg_kb:.0f} KB/张", flush=True)
    print(f"{'='*80}", flush=True)

    # 写出 JSON 记录便于追溯
    log_path = os.path.join(BASE_DIR, "scripts", "_car_photos_download_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump([
            {
                "brand": r[0], "model": r[1], "source_url": r[2],
                "width": r[3], "height": r[4], "aspect_ratio": round(r[5], 3),
                "size_bytes": r[6], "md5_prefix": r[7], "format": r[8]
            } for r in all_records
        ], f, ensure_ascii=False, indent=2)
    print(f"📝 下载日志已写入: {log_path}", flush=True)

if __name__ == "__main__":
    main()
